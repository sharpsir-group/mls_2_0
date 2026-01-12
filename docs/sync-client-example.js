/**
 * RESO MLS Sync Client - Vanilla JavaScript Implementation
 * 
 * Features:
 * - OAuth 2.0 token management with auto-refresh
 * - Efficient bulk pagination ($top=1000)
 * - Parallel requests for maximum throughput
 * - Retry logic with exponential backoff
 * - Progress tracking with UI integration examples
 * - Multi-tenant support (Qobrix + Dash data sources)
 * 
 * No dependencies - works in browser and Node.js (18+)
 * 
 * Data Sources:
 *   This API aggregates data from multiple sources:
 *   - Qobrix (OriginatingSystemOfficeKey = 'CSIR', X_DataSource = 'qobrix')
 *   - Dash/Sotheby's (OriginatingSystemOfficeKey = 'HSIR', X_DataSource = 'dash_sothebys')
 * 
 *   Your OAuth client is configured for specific office keys. Filter by:
 *   $filter=OriginatingSystemOfficeKey eq 'CSIR'  // Qobrix only
 *   $filter=OriginatingSystemOfficeKey eq 'HSIR'  // Dash only
 *   (no filter) // All data your client has access to
 * 
 * PropertyClass Values:
 *   RESI = Residential Sale
 *   RLSE = Residential Lease (Rental)
 *   COMS = Commercial Sale
 *   COML = Commercial Lease
 *   LAND = Land
 * 
 * DevelopmentStatus Values:
 *   Proposed = Off-plan, not yet started
 *   Under Construction = Currently being built
 *   Complete = Finished construction
 *   null = Unknown/not specified
 * 
 * Property Fields (RESO DD 2.0):
 *   Core: ListingKey, ListingId, ListPrice, StandardStatus, PropertyType, PropertyClass
 *   Location: City, StateOrProvince, PostalCode, Country, Latitude, Longitude
 *   Details: BedroomsTotal, BathroomsTotalInteger, BathroomsHalf, LivingArea, LotSizeSquareFeet
 *   Features: YearBuilt, View, Flooring, Heating, Cooling, PoolFeatures, FireplaceYN, ParkingFeatures
 *   Agent: ListAgentKey, ListAgentFirstName, ListAgentLastName, ListAgentEmail, ListOfficeName
 *   Extensions: X_DataSource, X_ListingUrl, X_CurrencyCode, X_ListPriceUSD
 * 
 * Media Fields:
 *   MediaKey, ResourceRecordKey, MediaURL, MediaCategory, Order
 *   ImageWidth, ImageHeight (available for Dash photos)
 */

// =============================================================================
// MLS SYNC CLIENT
// =============================================================================

class MLSSyncClient {
  /**
   * @param {Object} config
   * @param {string} config.baseUrl - API base URL
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

  async getToken() {
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
          this.accessToken = null;
          if (attempt < retries) continue;
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        if (attempt === retries) throw error;
        await this.sleep(backoffMs * Math.pow(2, attempt - 1));
      }
    }

    throw new Error('Max retries exceeded');
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------------------
  // Property Methods
  // ---------------------------------------------------------------------------

  async getPropertyCount(filter) {
    let url = `${this.baseUrl}/odata/Property?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;
    const response = await this.fetchWithRetry(url);
    return response['@odata.count'] || 0;
  }

  async fetchPage(options = {}) {
    const params = new URLSearchParams();
    if (options.top) params.set('$top', String(options.top));
    if (options.skip) params.set('$skip', String(options.skip));
    if (options.filter) params.set('$filter', options.filter);
    if (options.select?.length) params.set('$select', options.select.join(','));
    return this.fetchWithRetry(`${this.baseUrl}/odata/Property?${params}`);
  }

  async getProperty(listingKey) {
    return this.fetchWithRetry(`${this.baseUrl}/odata/Property('${listingKey}')`);
  }

  // ---------------------------------------------------------------------------
  // Full Sync - Sequential
  // ---------------------------------------------------------------------------

  /**
   * Sync all properties sequentially
   * @param {Object} options
   * @param {string} [options.filter] - OData filter
   * @param {string[]} [options.select] - Fields to return
   * @param {number} [options.pageSize=1000]
   * @param {Function} [options.onProgress] - Progress callback for UI updates
   * @param {Function} [options.onBatch] - Called with each batch
   * @returns {Promise<Object[]>}
   */
  async syncAllSequential(options = {}) {
    const { filter, select, pageSize = 1000, onProgress, onBatch } = options;

    const startTime = Date.now();
    const allProperties = [];
    const total = await this.getPropertyCount(filter);
    let fetched = 0;
    let skip = 0;

    while (true) {
      const response = await this.fetchPage({ skip, top: pageSize, filter, select });
      const batch = response.value;
      allProperties.push(...batch);
      fetched += batch.length;

      if (onBatch) await onBatch(batch);

      // Call progress callback for UI update
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

      if (!response['@odata.nextLink'] || batch.length < pageSize) break;
      skip += pageSize;
    }

    return allProperties;
  }

  // ---------------------------------------------------------------------------
  // Full Sync - Parallel (Recommended)
  // ---------------------------------------------------------------------------

  /**
   * Sync all properties with parallel requests (faster)
   * @param {Object} options
   * @param {string} [options.filter] - OData filter
   * @param {string[]} [options.select] - Fields to return
   * @param {number} [options.pageSize=1000]
   * @param {number} [options.maxConcurrent=3] - Parallel requests
   * @param {Function} [options.onProgress] - Progress callback for UI updates
   * @param {Function} [options.onBatch] - Called with each batch
   * @returns {Promise<Object[]>}
   */
  async syncAllParallel(options = {}) {
    const { filter, select, pageSize = 1000, maxConcurrent = 3, onProgress, onBatch } = options;

    const startTime = Date.now();
    const total = await this.getPropertyCount(filter);
    const totalPages = Math.ceil(total / pageSize);
    
    const allProperties = new Array(total);
    let completedPages = 0;
    let fetchedCount = 0;

    const fetchPageTask = async (pageIndex) => {
      const skip = pageIndex * pageSize;
      const response = await this.fetchPage({ skip, top: pageSize, filter, select });
      const batch = response.value;
      
      for (let i = 0; i < batch.length; i++) {
        allProperties[skip + i] = batch[i];
      }

      fetchedCount += batch.length;
      completedPages++;

      if (onBatch) await onBatch(batch);

      // Call progress callback for UI update
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

    for (let i = 0; i < totalPages; i += maxConcurrent) {
      const batch = [];
      for (let j = 0; j < maxConcurrent && i + j < totalPages; j++) {
        batch.push(fetchPageTask(i + j));
      }
      await Promise.all(batch);
    }

    return allProperties.filter(Boolean);
  }

  // ---------------------------------------------------------------------------
  // Incremental Sync
  // ---------------------------------------------------------------------------

  async syncModifiedSince(since, options = {}) {
    const filter = `ModificationTimestamp gt ${since.toISOString()}`;
    return this.syncAllParallel({ ...options, filter });
  }

  // ---------------------------------------------------------------------------
  // Media Methods
  // ---------------------------------------------------------------------------

  async getMediaCount(filter) {
    let url = `${this.baseUrl}/odata/Media?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;
    const response = await this.fetchWithRetry(url);
    return response['@odata.count'] || 0;
  }

  /**
   * Get main photo URLs for multiple properties (batch request)
   * Returns Map of ListingKey -> MediaURL for first photo (Order=0)
   * @param {string[]} listingKeys - Array of property ListingKeys
   * @returns {Promise<Map<string, string>>}
   * 
   * @example
   * const photos = await client.getMainPhotos(properties.map(p => p.ListingKey));
   * properties.forEach(p => p.mainPhoto = photos.get(p.ListingKey));
   */
  /**
   * Get main photo URLs for multiple properties (batch request with parallelism)
   * @param {string[]} listingKeys - Array of property ListingKeys
   * @returns {Promise<Map<string, string>>} Map of ListingKey -> MediaURL
   */
  async getMainPhotos(listingKeys) {
    const photoMap = new Map();
    const batchSize = 200; // ~200 keys per request (URL length safe)
    const maxConcurrent = 3; // Parallel batch requests
    
    // Create batch requests
    const batches = [];
    for (let i = 0; i < listingKeys.length; i += batchSize) {
      batches.push(listingKeys.slice(i, i + batchSize));
    }
    
    // Process batches with concurrency limit
    for (let i = 0; i < batches.length; i += maxConcurrent) {
      const batchGroup = batches.slice(i, i + maxConcurrent);
      const results = await Promise.all(
        batchGroup.map(async (batch) => {
          const keyList = batch.map(k => `'${k}'`).join(',');
          const filter = `ResourceRecordKey in (${keyList}) and Order eq 0`;
          // IMPORTANT: Must include $top=1000 to avoid default 100 limit!
          const url = `${this.baseUrl}/odata/Media?$filter=${encodeURIComponent(filter)}&$select=ResourceRecordKey,MediaURL&$top=1000`;
          return this.fetchWithRetry(url);
        })
      );
      
      for (const response of results) {
        for (const m of response.value) {
          photoMap.set(m.ResourceRecordKey, m.MediaURL);
        }
      }
    }
    
    return photoMap;
  }

  async getPropertyMedia(listingKey) {
    const url = `${this.baseUrl}/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`;
    const response = await this.fetchWithRetry(url);
    return response.value;
  }

  async getMediaForProperties(listingKeys) {
    const mediaMap = new Map();
    const batchSize = 50;
    
    for (let i = 0; i < listingKeys.length; i += batchSize) {
      const batch = listingKeys.slice(i, i + batchSize);
      const keyList = batch.map(k => `'${k}'`).join(',');
      const url = `${this.baseUrl}/odata/Media?$filter=${encodeURIComponent(`ResourceRecordKey in (${keyList})`)}&$orderby=ResourceRecordKey,Order&$top=1000`;
      const response = await this.fetchWithRetry(url);
      
      for (const m of response.value) {
        if (!mediaMap.has(m.ResourceRecordKey)) mediaMap.set(m.ResourceRecordKey, []);
        mediaMap.get(m.ResourceRecordKey).push(m);
      }
    }
    
    return mediaMap;
  }

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

      if (!response['@odata.nextLink'] || response.value.length < pageSize) break;
      skip += pageSize;
    }

    return allMedia;
  }

  async syncAllWithMedia(options = {}) {
    const { onProgress } = options;
    
    const properties = await this.syncAllParallel({
      ...options,
      onProgress: onProgress ? (p) => onProgress({ ...p, percent: Math.round(p.percent * 0.6) }) : undefined,
    });

    const allMedia = await this.syncAllMedia({
      onProgress: onProgress ? (p) => onProgress({ ...p, percent: 60 + Math.round(p.percent * 0.4) }) : undefined,
    });

    const mediaMap = new Map();
    for (const m of allMedia) {
      if (!mediaMap.has(m.ResourceRecordKey)) mediaMap.set(m.ResourceRecordKey, []);
      mediaMap.get(m.ResourceRecordKey).push(m);
    }

    for (const p of properties) {
      p.media = mediaMap.get(p.ListingKey) || [];
    }

    return properties;
  }

  async getPropertyWithMedia(listingKey) {
    const [property, media] = await Promise.all([
      this.getProperty(listingKey),
      this.getPropertyMedia(listingKey),
    ]);
    property.media = media;
    return property;
  }
}

// =============================================================================
// USAGE EXAMPLES WITH PROGRESS BAR
// =============================================================================

/*
// ---------------------------------------------------------------------------
// 1. BASIC SYNC WITH CONSOLE PROGRESS
// ---------------------------------------------------------------------------

const client = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// Sync all active properties (from all data sources your client has access to)
const properties = await client.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  onProgress: (p) => {
    console.log(`${p.percent}% (${p.fetched}/${p.total}) - ${p.propertiesPerSecond} items/sec`);
  },
});


// ---------------------------------------------------------------------------
// 1a. FILTER BY DATA SOURCE
// ---------------------------------------------------------------------------

// Sync only Qobrix data
const qobrixProperties = await client.syncAllParallel({
  filter: "OriginatingSystemOfficeKey eq 'CSIR'",
});

// Sync only Dash/Sotheby's data
const dashProperties = await client.syncAllParallel({
  filter: "OriginatingSystemOfficeKey eq 'HSIR'",
});

// Combine filters
const activeDashProperties = await client.syncAllParallel({
  filter: "StandardStatus eq 'Active' and OriginatingSystemOfficeKey eq 'HSIR'",
});

// Check data source in results
properties.forEach(p => {
  console.log(`${p.ListingKey}: ${p.X_DataSource} (${p.OriginatingSystemOfficeKey})`);
  // Output: QOBRIX_abc123: qobrix (CSIR)
  // Output: DASH_xyz789: dash_sothebys (HSIR)
});


// ---------------------------------------------------------------------------
// 1b. SYNC WITH MAIN PHOTOS (Recommended for listing pages)
// ---------------------------------------------------------------------------

// Step 1: Sync properties
const properties = await client.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal', 'BathroomsTotalInteger'],
});

// Step 2: Batch fetch main photos (single request per 100 properties)
const photoMap = await client.getMainPhotos(properties.map(p => p.ListingKey));

// Step 3: Attach to properties
properties.forEach(p => {
  p.mainPhoto = photoMap.get(p.ListingKey) || null;
});

// Now render in UI:
// properties.forEach(p => {
//   console.log(`${p.ListPrice} - ${p.City} - ${p.mainPhoto}`);
// });


// ---------------------------------------------------------------------------
// 1c. PROPERTY DETAIL PAGE - Fetch All Photos on Click
// ---------------------------------------------------------------------------

// When user clicks a property card, load all photos for the detail/gallery view:

async function showPropertyDetail(listingKey) {
  // Show loading state
  document.getElementById('gallery').innerHTML = '<p>Loading photos...</p>';
  
  // Fetch all photos for this property (sorted by Order)
  const photos = await client.getPropertyMedia(listingKey);
  
  if (photos.length === 0) {
    document.getElementById('gallery').innerHTML = '<p>No photos available</p>';
    return;
  }
  
  // Render gallery
  let currentIndex = 0;
  const gallery = document.getElementById('gallery');
  
  function renderGallery() {
    gallery.innerHTML = `
      <div class="main-image">
        <img src="${photos[currentIndex].MediaURL}" alt="Property photo ${currentIndex + 1}">
        <div class="photo-counter">${currentIndex + 1} / ${photos.length}</div>
      </div>
      <div class="thumbnails">
        ${photos.map((p, i) => `
          <img 
            src="${p.MediaURL}" 
            class="thumb ${i === currentIndex ? 'active' : ''}"
            onclick="setPhoto(${i})"
          >
        `).join('')}
      </div>
      <div class="nav-buttons">
        <button onclick="prevPhoto()" ${currentIndex === 0 ? 'disabled' : ''}>← Prev</button>
        <button onclick="nextPhoto()" ${currentIndex === photos.length - 1 ? 'disabled' : ''}>Next →</button>
      </div>
    `;
  }
  
  // Navigation functions (attach to window for onclick)
  window.setPhoto = (i) => { currentIndex = i; renderGallery(); };
  window.prevPhoto = () => { if (currentIndex > 0) { currentIndex--; renderGallery(); } };
  window.nextPhoto = () => { if (currentIndex < photos.length - 1) { currentIndex++; renderGallery(); } };
  
  renderGallery();
}

// CSS for the gallery:
// .main-image { position: relative; }
// .main-image img { width: 100%; max-height: 500px; object-fit: cover; border-radius: 8px; }
// .photo-counter { position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; }
// .thumbnails { display: flex; gap: 8px; margin-top: 12px; overflow-x: auto; }
// .thumb { width: 80px; height: 60px; object-fit: cover; border-radius: 4px; cursor: pointer; opacity: 0.6; transition: opacity 0.2s; }
// .thumb:hover, .thumb.active { opacity: 1; }
// .thumb.active { outline: 2px solid #3b82f6; }

// Example: Property card click handler
document.querySelectorAll('.property-card').forEach(card => {
  card.addEventListener('click', () => {
    const listingKey = card.dataset.listingKey;
    showPropertyDetail(listingKey);
  });
});


// ---------------------------------------------------------------------------
// 1d. REACT: Property Card → Detail Page Pattern
// ---------------------------------------------------------------------------

// PropertyCard.jsx - Shows main photo, links to detail
function PropertyCard({ property }) {
  return (
    <Link to={`/property/${property.ListingKey}`} className="property-card">
      <img src={property.mainPhoto} alt={property.City} />
      <h3>${property.ListPrice?.toLocaleString()}</h3>
      <p>{property.BedroomsTotal} bed • {property.City}</p>
    </Link>
  );
}

// PropertyDetailPage.jsx - Shows all photos in gallery
function PropertyDetailPage() {
  const { listingKey } = useParams();
  const [photos, setPhotos] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.getPropertyMedia(listingKey)
      .then(setPhotos)
      .finally(() => setLoading(false));
  }, [listingKey]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="property-detail">
      {/* Main Image */}
      {photos.length > 0 && (
        <div className="gallery">
          <img 
            src={photos[activeIndex].MediaURL} 
            className="main-photo"
          />
          <div className="thumbnails">
            {photos.map((photo, i) => (
              <img
                key={photo.MediaKey}
                src={photo.MediaURL}
                onClick={() => setActiveIndex(i)}
                className={i === activeIndex ? 'active' : ''}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// 2. PROGRESS BAR - VANILLA JAVASCRIPT (Full Example)
// ---------------------------------------------------------------------------

<!DOCTYPE html>
<html>
<head>
  <title>MLS Property Sync</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }
    
    /* Progress Bar Styles */
    .progress-container {
      width: 100%;
      max-width: 500px;
      height: 24px;
      background: #e5e7eb;
      border-radius: 12px;
      overflow: hidden;
      margin: 16px 0;
    }
    
    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, #10b981, #34d399);
      border-radius: 12px;
      transition: width 0.3s ease;
      position: relative;
    }
    
    /* Animated shimmer effect while syncing */
    .progress-bar.syncing {
      background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #10b981 100%);
      background-size: 200% 100%;
      animation: shimmer 1.5s ease-in-out infinite;
    }
    
    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    
    .progress-text {
      font-size: 14px;
      color: #374151;
      margin-bottom: 4px;
    }
    
    .progress-stats {
      font-size: 12px;
      color: #6b7280;
    }
    
    .sync-btn {
      background: #3b82f6;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
      transition: background 0.2s;
    }
    
    .sync-btn:hover { background: #2563eb; }
    .sync-btn:disabled { background: #9ca3af; cursor: not-allowed; }
  </style>
</head>
<body>
  <h1>MLS Property Sync</h1>
  
  <button class="sync-btn" id="syncBtn">Start Sync</button>
  
  <div style="margin-top: 20px;">
    <p class="progress-text" id="progressText">Ready to sync</p>
    <div class="progress-container">
      <div class="progress-bar" id="progressBar" style="width: 0%"></div>
    </div>
    <p class="progress-stats" id="progressStats"></p>
  </div>
  
  <div id="results" style="margin-top: 20px;"></div>

  <script src="sync-client-example.js"></script>
  <script>
    const client = new MLSSyncClient({
      baseUrl: 'https://your-server.com/reso',
      clientId: 'your-client-id',
      clientSecret: 'your-client-secret',
    });

    const btn = document.getElementById('syncBtn');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressStats = document.getElementById('progressStats');
    const results = document.getElementById('results');

    btn.addEventListener('click', async () => {
      // Disable button during sync
      btn.disabled = true;
      btn.textContent = 'Syncing...';
      progressBar.classList.add('syncing');

      try {
        // Step 1: Sync properties
        const properties = await client.syncAllParallel({
          filter: "StandardStatus eq 'Active'",
          select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal'],
          
          // PROGRESS CALLBACK - Update UI here!
          onProgress: (p) => {
            // Update progress bar width (0-80% for properties)
            progressBar.style.width = `${Math.round(p.percent * 0.8)}%`;
            
            // Update text
            progressText.textContent = `${p.percent}% properties (${p.fetched.toLocaleString()} / ${p.total.toLocaleString()})`;
            
            // Show speed and ETA
            const etaSeconds = Math.round(p.estimatedRemainingMs / 1000);
            const etaText = etaSeconds > 60 
              ? `${Math.floor(etaSeconds / 60)}m ${etaSeconds % 60}s` 
              : `${etaSeconds}s`;
            progressStats.textContent = `Speed: ${p.propertiesPerSecond} items/sec • ETA: ${etaText}`;
          },
        });

        // Step 2: Fetch main photos (80-100%)
        progressText.textContent = 'Fetching main photos...';
        const photoMap = await client.getMainPhotos(properties.map(p => p.ListingKey));
        
        // Step 3: Attach photos to properties
        properties.forEach(p => {
          p.mainPhoto = photoMap.get(p.ListingKey) || null;
        });
        progressBar.style.width = '100%';

        // Done!
        progressBar.classList.remove('syncing');
        progressText.textContent = `✓ Synced ${properties.length.toLocaleString()} properties with photos`;
        progressStats.textContent = '';
        
        results.innerHTML = `<p>First 5 properties:</p><pre>${JSON.stringify(properties.slice(0, 5), null, 2)}</pre>`;
        
      } catch (error) {
        progressBar.classList.remove('syncing');
        progressText.textContent = `✗ Error: ${error.message}`;
        progressBar.style.background = '#ef4444';
      } finally {
        btn.disabled = false;
        btn.textContent = 'Start Sync';
      }
    });
  </script>
</body>
</html>


// ---------------------------------------------------------------------------
// 3. PROGRESS BAR - REACT COMPONENT
// ---------------------------------------------------------------------------

import { useState } from 'react';

function SyncProgressBar() {
  const [progress, setProgress] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [properties, setProperties] = useState([]);

  const handleSync = async () => {
    setSyncing(true);
    setProgress(null);
    
    try {
      const result = await client.syncAllParallel({
        filter: "StandardStatus eq 'Active'",
        onProgress: setProgress,  // React state update as progress callback!
      });
      setProperties(result);
    } finally {
      setSyncing(false);
    }
  };

  const formatEta = (ms) => {
    const seconds = Math.round(ms / 1000);
    return seconds > 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${seconds}s`;
  };

  return (
    <div className="p-6 max-w-md">
      <button 
        onClick={handleSync} 
        disabled={syncing}
        className="w-full py-3 px-4 bg-blue-500 text-white rounded-lg font-medium
                   disabled:bg-gray-400 disabled:cursor-not-allowed
                   hover:bg-blue-600 transition-colors"
      >
        {syncing ? 'Syncing...' : 'Start Sync'}
      </button>

      {/* Progress Section */}
      {(progress || syncing) && (
        <div className="mt-4">
          {/* Text */}
          <p className="text-sm text-gray-700 mb-2">
            {progress 
              ? `${progress.percent}% (${progress.fetched.toLocaleString()} / ${progress.total.toLocaleString()})`
              : 'Initializing...'}
          </p>
          
          {/* Progress Bar */}
          <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-300 ${
                syncing 
                  ? 'bg-gradient-to-r from-green-500 via-green-400 to-green-500 bg-[length:200%_100%] animate-pulse' 
                  : 'bg-green-500'
              }`}
              style={{ width: `${progress?.percent || 0}%` }}
            />
          </div>
          
          {/* Stats */}
          {progress && (
            <p className="text-xs text-gray-500 mt-2">
              {progress.propertiesPerSecond} items/sec • ETA: {formatEta(progress.estimatedRemainingMs)}
            </p>
          )}
        </div>
      )}

      {/* Results */}
      {!syncing && properties.length > 0 && (
        <p className="mt-4 text-green-600 font-medium">
          ✓ Synced {properties.length.toLocaleString()} properties
        </p>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// 4. TWO-PHASE PROGRESS (Properties + Media)
// ---------------------------------------------------------------------------

// When syncing properties AND media, show which phase is active:

async function syncWithTwoPhaseProgress() {
  const phaseText = document.getElementById('phaseText');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  // Phase 1: Properties (0-60%)
  phaseText.textContent = 'Phase 1/2: Syncing properties...';
  const properties = await client.syncAllParallel({
    onProgress: (p) => {
      const adjustedPercent = Math.round(p.percent * 0.6); // 0-60%
      progressBar.style.width = `${adjustedPercent}%`;
      progressText.textContent = `${adjustedPercent}% - Properties: ${p.fetched}/${p.total}`;
    },
  });

  // Phase 2: Media (60-100%)
  phaseText.textContent = 'Phase 2/2: Syncing media...';
  const media = await client.syncAllMedia({
    onProgress: (p) => {
      const adjustedPercent = 60 + Math.round(p.percent * 0.4); // 60-100%
      progressBar.style.width = `${adjustedPercent}%`;
      progressText.textContent = `${adjustedPercent}% - Media: ${p.fetched}/${p.total}`;
    },
  });

  phaseText.textContent = 'Complete!';
  progressBar.style.width = '100%';
}


// ---------------------------------------------------------------------------
// 5. CIRCULAR PROGRESS (Alternative UI)
// ---------------------------------------------------------------------------

// CSS for circular progress:
// .circular-progress {
//   width: 120px;
//   height: 120px;
//   border-radius: 50%;
//   background: conic-gradient(#10b981 var(--progress), #e5e7eb var(--progress));
//   display: flex;
//   align-items: center;
//   justify-content: center;
// }
// .circular-progress::before {
//   content: '';
//   width: 100px;
//   height: 100px;
//   border-radius: 50%;
//   background: white;
// }

// Usage:
// onProgress: (p) => {
//   circularProgress.style.setProperty('--progress', `${p.percent * 3.6}deg`);
//   percentText.textContent = `${p.percent}%`;
// }


// ---------------------------------------------------------------------------
// 6. NODE.JS TERMINAL PROGRESS
// ---------------------------------------------------------------------------

// For Node.js CLI applications:

const properties = await client.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  onProgress: (p) => {
    // Clear line and print progress
    process.stdout.clearLine(0);
    process.stdout.cursorTo(0);
    
    const barWidth = 30;
    const filled = Math.round((p.percent / 100) * barWidth);
    const empty = barWidth - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    
    process.stdout.write(
      `[${bar}] ${p.percent}% | ${p.fetched}/${p.total} | ${p.propertiesPerSecond}/s`
    );
  },
});

console.log(`\nSynced ${properties.length} properties`);

*/

// Export for Node.js / ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MLSSyncClient;
}
