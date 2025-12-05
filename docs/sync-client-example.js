/**
 * RESO MLS Sync Client - Vanilla JavaScript Implementation
 * 
 * Features:
 * - OAuth 2.0 token management with auto-refresh
 * - Efficient bulk pagination ($top=1000)
 * - Parallel requests for maximum throughput
 * - Retry logic with exponential backoff
 * - Progress tracking
 * - PropertyClass filtering (RESI, RLSE, COMS, COML, LAND)
 * 
 * No dependencies - works in browser and Node.js (18+)
 * 
 * PropertyClass Values:
 *   RESI = Residential Sale
 *   RLSE = Residential Lease (Rental)
 *   COMS = Commercial Sale
 *   COML = Commercial Lease
 *   LAND = Land
 */

// =============================================================================
// MLS SYNC CLIENT
// =============================================================================

class MLSSyncClient {
  /**
   * @param {Object} config
   * @param {string} config.baseUrl - API base URL (e.g., 'https://your-server.com/reso')
   * @param {string} config.clientId - OAuth client ID
   * @param {string} config.clientSecret - OAuth client secret
   */
  constructor(config) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.clientId = config.clientId;
    this.clientSecret = config.clientSecret;
    this.accessToken = null;
    this.tokenExpiry = 0;
  }

  // ---------------------------------------------------------------------------
  // OAuth Token Management
  // ---------------------------------------------------------------------------

  /**
   * Get valid access token (auto-refresh if expired)
   * @returns {Promise<string>}
   */
  async getToken() {
    // Return cached token if still valid (with 60s buffer)
    if (this.accessToken && Date.now() < this.tokenExpiry - 60000) {
      return this.accessToken;
    }

    const credentials = btoa(`${this.clientId}:${this.clientSecret}`);
    
    const response = await fetch(`${this.baseUrl}/oauth/token`, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'grant_type=client_credentials',
    });

    if (!response.ok) {
      throw new Error(`OAuth failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    this.accessToken = data.access_token;
    this.tokenExpiry = Date.now() + data.expires_in * 1000;

    return this.accessToken;
  }

  // ---------------------------------------------------------------------------
  // HTTP Request with Retry
  // ---------------------------------------------------------------------------

  /**
   * Fetch with automatic retry and exponential backoff
   * @param {string} url
   * @param {number} retries
   * @param {number} backoffMs
   * @returns {Promise<Object>}
   */
  async fetchWithRetry(url, retries = 3, backoffMs = 1000) {
    const token = await this.getToken();

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        });

        if (response.status === 401) {
          // Token expired - clear and retry
          this.accessToken = null;
          if (attempt < retries) continue;
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        if (attempt === retries) throw error;
        
        // Exponential backoff
        await this.sleep(backoffMs * Math.pow(2, attempt - 1));
      }
    }

    throw new Error('Max retries exceeded');
  }

  /**
   * @param {number} ms
   * @returns {Promise<void>}
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------------------
  // Property Methods
  // ---------------------------------------------------------------------------

  /**
   * Get total property count
   * @param {string} [filter] - OData filter expression
   * @returns {Promise<number>}
   */
  async getPropertyCount(filter) {
    let url = `${this.baseUrl}/odata/Property?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;

    const response = await this.fetchWithRetry(url);
    return response['@odata.count'] || 0;
  }

  /**
   * Fetch a single page of properties
   * @param {Object} options
   * @param {number} [options.skip]
   * @param {number} [options.top]
   * @param {string} [options.filter]
   * @param {string[]} [options.select]
   * @returns {Promise<Object>}
   */
  async fetchPage(options = {}) {
    const params = new URLSearchParams();
    
    if (options.top) params.set('$top', String(options.top));
    if (options.skip) params.set('$skip', String(options.skip));
    if (options.filter) params.set('$filter', options.filter);
    if (options.select && options.select.length) {
      params.set('$select', options.select.join(','));
    }

    const url = `${this.baseUrl}/odata/Property?${params}`;
    return this.fetchWithRetry(url);
  }

  /**
   * Get a single property by key
   * @param {string} listingKey
   * @returns {Promise<Object>}
   */
  async getProperty(listingKey) {
    const url = `${this.baseUrl}/odata/Property('${listingKey}')`;
    return this.fetchWithRetry(url);
  }

  // ---------------------------------------------------------------------------
  // Full Sync - Sequential (Simple)
  // ---------------------------------------------------------------------------

  /**
   * Sync all properties sequentially
   * @param {Object} [options]
   * @param {string} [options.filter]
   * @param {string[]} [options.select]
   * @param {number} [options.pageSize=1000]
   * @param {Function} [options.onProgress]
   * @param {Function} [options.onBatch]
   * @returns {Promise<Object[]>}
   */
  async syncAllSequential(options = {}) {
    const {
      filter,
      select,
      pageSize = 1000,
      onProgress,
      onBatch,
    } = options;

    const startTime = Date.now();
    const allProperties = [];
    
    // Get total count first
    const total = await this.getPropertyCount(filter);
    let fetched = 0;
    let skip = 0;

    while (true) {
      const response = await this.fetchPage({
        skip,
        top: pageSize,
        filter,
        select,
      });

      const batch = response.value;
      allProperties.push(...batch);
      fetched += batch.length;

      // Callback for batch processing
      if (onBatch) await onBatch(batch);

      // Progress update
      if (onProgress) {
        const elapsed = Date.now() - startTime;
        const rate = fetched / (elapsed / 1000);
        onProgress({
          total,
          fetched,
          percent: Math.round((fetched / total) * 100),
          elapsedMs: elapsed,
          estimatedRemainingMs: rate > 0 ? ((total - fetched) / rate) * 1000 : 0,
          propertiesPerSecond: Math.round(rate),
        });
      }

      // Check if done
      if (!response['@odata.nextLink'] || batch.length < pageSize) {
        break;
      }

      skip += pageSize;
    }

    return allProperties;
  }

  // ---------------------------------------------------------------------------
  // Full Sync - Parallel (Fast)
  // ---------------------------------------------------------------------------

  /**
   * Sync all properties with parallel requests
   * @param {Object} [options]
   * @param {string} [options.filter]
   * @param {string[]} [options.select]
   * @param {number} [options.pageSize=1000]
   * @param {number} [options.maxConcurrent=3]
   * @param {Function} [options.onProgress]
   * @param {Function} [options.onBatch]
   * @returns {Promise<Object[]>}
   */
  async syncAllParallel(options = {}) {
    const {
      filter,
      select,
      pageSize = 1000,
      maxConcurrent = 3,
      onProgress,
      onBatch,
    } = options;

    const startTime = Date.now();
    const total = await this.getPropertyCount(filter);
    const totalPages = Math.ceil(total / pageSize);
    
    const allProperties = new Array(total);
    let completedPages = 0;
    let fetchedCount = 0;

    // Create page fetch task
    const fetchPageTask = async (pageIndex) => {
      const skip = pageIndex * pageSize;
      const response = await this.fetchPage({
        skip,
        top: pageSize,
        filter,
        select,
      });

      // Store in correct position
      const batch = response.value;
      for (let i = 0; i < batch.length; i++) {
        allProperties[skip + i] = batch[i];
      }

      fetchedCount += batch.length;
      completedPages++;

      if (onBatch) await onBatch(batch);

      if (onProgress) {
        const elapsed = Date.now() - startTime;
        const rate = fetchedCount / (elapsed / 1000);
        onProgress({
          total,
          fetched: fetchedCount,
          percent: Math.round((completedPages / totalPages) * 100),
          elapsedMs: elapsed,
          estimatedRemainingMs: rate > 0 ? ((total - fetchedCount) / rate) * 1000 : 0,
          propertiesPerSecond: Math.round(rate),
        });
      }
    };

    // Process pages in parallel batches
    for (let i = 0; i < totalPages; i += maxConcurrent) {
      const batch = [];
      for (let j = 0; j < maxConcurrent && i + j < totalPages; j++) {
        batch.push(fetchPageTask(i + j));
      }
      await Promise.all(batch);
    }

    // Filter out empty slots (in case of partial last page)
    return allProperties.filter(Boolean);
  }

  // ---------------------------------------------------------------------------
  // Incremental Sync (Delta)
  // ---------------------------------------------------------------------------

  /**
   * Sync properties modified since a given date
   * @param {Date} since
   * @param {Object} [options]
   * @returns {Promise<Object[]>}
   */
  async syncModifiedSince(since, options = {}) {
    const isoDate = since.toISOString();
    const filter = `ModificationTimestamp gt ${isoDate}`;
    
    return this.syncAllParallel({
      ...options,
      filter,
    });
  }

  // ---------------------------------------------------------------------------
  // Media Methods
  // ---------------------------------------------------------------------------

  /**
   * Get total media count
   * @param {string} [filter]
   * @returns {Promise<number>}
   */
  async getMediaCount(filter) {
    let url = `${this.baseUrl}/odata/Media?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;

    const response = await this.fetchWithRetry(url);
    return response['@odata.count'] || 0;
  }

  /**
   * Fetch media for a single property
   * @param {string} listingKey
   * @returns {Promise<Object[]>}
   */
  async getPropertyMedia(listingKey) {
    const url = `${this.baseUrl}/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`;
    const response = await this.fetchWithRetry(url);
    return response.value;
  }

  /**
   * Fetch media for multiple properties (bulk)
   * @param {string[]} listingKeys
   * @returns {Promise<Map<string, Object[]>>}
   */
  async getMediaForProperties(listingKeys) {
    const mediaMap = new Map();
    
    // Process in batches of 50 to avoid URL length limits
    const batchSize = 50;
    for (let i = 0; i < listingKeys.length; i += batchSize) {
      const batch = listingKeys.slice(i, i + batchSize);
      const keyList = batch.map(k => `'${k}'`).join(',');
      const filter = `ResourceRecordKey in (${keyList})`;
      
      const url = `${this.baseUrl}/odata/Media?$filter=${encodeURIComponent(filter)}&$orderby=ResourceRecordKey,Order&$top=1000`;
      const response = await this.fetchWithRetry(url);
      
      // Group by property
      for (const m of response.value) {
        const key = m.ResourceRecordKey;
        if (!mediaMap.has(key)) mediaMap.set(key, []);
        mediaMap.get(key).push(m);
      }
    }
    
    return mediaMap;
  }

  /**
   * Sync all media
   * @param {Object} [options]
   * @param {number} [options.pageSize=1000]
   * @param {Function} [options.onProgress]
   * @returns {Promise<Object[]>}
   */
  async syncAllMedia(options = {}) {
    const { pageSize = 1000, onProgress } = options;
    const startTime = Date.now();
    const allMedia = [];
    
    const total = await this.getMediaCount();
    let fetched = 0;
    let skip = 0;

    while (true) {
      const url = `${this.baseUrl}/odata/Media?$top=${pageSize}&$skip=${skip}&$orderby=ResourceRecordKey,Order`;
      const response = await this.fetchWithRetry(url);
      
      allMedia.push(...response.value);
      fetched += response.value.length;

      if (onProgress) {
        const elapsed = Date.now() - startTime;
        const rate = fetched / (elapsed / 1000);
        onProgress({
          total,
          fetched,
          percent: Math.round((fetched / total) * 100),
          elapsedMs: elapsed,
          estimatedRemainingMs: rate > 0 ? ((total - fetched) / rate) * 1000 : 0,
          propertiesPerSecond: Math.round(rate),
        });
      }

      if (!response['@odata.nextLink'] || response.value.length < pageSize) {
        break;
      }
      skip += pageSize;
    }

    return allMedia;
  }

  /**
   * Full sync with media attached to properties
   * @param {Object} [options]
   * @returns {Promise<Object[]>}
   */
  async syncAllWithMedia(options = {}) {
    const { onProgress } = options;
    
    // Phase 1: Sync properties
    console.log('Phase 1/2: Syncing properties...');
    const properties = await this.syncAllParallel({
      ...options,
      onProgress: onProgress ? (p) => {
        onProgress({ ...p, percent: Math.round(p.percent * 0.6) }); // 0-60%
      } : undefined,
    });

    // Phase 2: Sync media
    console.log('Phase 2/2: Syncing media...');
    const allMedia = await this.syncAllMedia({
      onProgress: onProgress ? (p) => {
        onProgress({ ...p, percent: 60 + Math.round(p.percent * 0.4) }); // 60-100%
      } : undefined,
    });

    // Attach media to properties
    const mediaMap = new Map();
    for (const m of allMedia) {
      const key = m.ResourceRecordKey;
      if (!mediaMap.has(key)) mediaMap.set(key, []);
      mediaMap.get(key).push(m);
    }

    for (const p of properties) {
      p.media = mediaMap.get(p.ListingKey) || [];
    }

    return properties;
  }

  /**
   * Get single property with all media (for detail page)
   * @param {string} listingKey
   * @returns {Promise<Object>}
   */
  async getPropertyWithMedia(listingKey) {
    // Fetch both in parallel
    const [property, media] = await Promise.all([
      this.getProperty(listingKey),
      this.getPropertyMedia(listingKey),
    ]);
    
    property.media = media;
    return property;
  }
}

// =============================================================================
// USAGE EXAMPLES
// =============================================================================

/*
// ---------------------------------------------------------------------------
// BROWSER USAGE
// ---------------------------------------------------------------------------

// Initialize client
const mlsClient = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// Full sync with progress
mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal', 'X_MainPhoto'],
  maxConcurrent: 3,
  onProgress: (p) => {
    document.getElementById('progress').textContent = 
      `${p.percent}% (${p.fetched}/${p.total}) - ${p.propertiesPerSecond} props/sec`;
  },
}).then(properties => {
  console.log(`Synced ${properties.length} properties`);
  renderProperties(properties);
});

// Get single property with all photos (for detail page)
mlsClient.getPropertyWithMedia('QOBRIX_123').then(property => {
  console.log(`${property.ListingKey}: ${property.media.length} photos`);
  renderPropertyDetail(property);
});

// Incremental sync (changes since last sync)
const lastSync = new Date(localStorage.getItem('lastSync') || 0);
mlsClient.syncModifiedSince(lastSync).then(updates => {
  console.log(`${updates.length} properties updated`);
  localStorage.setItem('lastSync', new Date().toISOString());
});

// ---------------------------------------------------------------------------
// NODE.JS USAGE (18+)
// ---------------------------------------------------------------------------

// const mlsClient = new MLSSyncClient({
//   baseUrl: 'https://your-server.com/reso',
//   clientId: process.env.RESO_CLIENT_ID,
//   clientSecret: process.env.RESO_CLIENT_SECRET,
// });
// 
// const properties = await mlsClient.syncAllParallel();
// console.log(`Synced ${properties.length} properties`);

// ---------------------------------------------------------------------------
// HTML EXAMPLE
// ---------------------------------------------------------------------------

/*
<!DOCTYPE html>
<html>
<head>
  <title>MLS Property Sync</title>
  <style>
    .property-card {
      border: 1px solid #ddd;
      padding: 16px;
      margin: 8px;
      border-radius: 8px;
    }
    .property-card img {
      width: 100%;
      height: 200px;
      object-fit: cover;
      border-radius: 4px;
    }
    .progress-bar {
      width: 100%;
      height: 20px;
      background: #eee;
      border-radius: 10px;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      background: #4CAF50;
      transition: width 0.3s;
    }
  </style>
</head>
<body>
  <h1>MLS Properties</h1>
  
  <button id="syncBtn">Sync Properties</button>
  
  <div id="progress" style="margin: 16px 0;">
    <div class="progress-bar">
      <div class="progress-bar-fill" id="progressFill" style="width: 0%"></div>
    </div>
    <p id="progressText">Ready to sync</p>
  </div>
  
  <div id="properties" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;"></div>

  <script src="sync-client-example.js"></script>
  <script>
    const client = new MLSSyncClient({
      baseUrl: 'https://your-server.com/reso',
      clientId: 'your-client-id',
      clientSecret: 'your-client-secret',
    });

    document.getElementById('syncBtn').addEventListener('click', async () => {
      const btn = document.getElementById('syncBtn');
      btn.disabled = true;
      btn.textContent = 'Syncing...';

      try {
        const properties = await client.syncAllParallel({
          filter: "StandardStatus eq 'Active'",
          select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal', 'X_MainPhoto'],
          onProgress: (p) => {
            document.getElementById('progressFill').style.width = p.percent + '%';
            document.getElementById('progressText').textContent = 
              `${p.percent}% (${p.fetched}/${p.total}) - ${p.propertiesPerSecond} props/sec`;
          },
        });

        // Render properties
        const container = document.getElementById('properties');
        container.innerHTML = properties.slice(0, 50).map(p => `
          <div class="property-card">
            <img src="${p.X_MainPhoto || 'placeholder.jpg'}" alt="${p.City}">
            <h3>$${p.ListPrice?.toLocaleString() || 'N/A'}</h3>
            <p>${p.City} | ${p.BedroomsTotal || '?'} bed</p>
          </div>
        `).join('');

        document.getElementById('progressText').textContent = 
          `Done! Synced ${properties.length} properties`;
      } catch (err) {
        document.getElementById('progressText').textContent = 'Error: ' + err.message;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Sync Properties';
      }
    });
  </script>
</body>
</html>
*/

// Export for Node.js / ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MLSSyncClient;
}

