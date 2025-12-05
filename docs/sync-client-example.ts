/**
 * RESO MLS Sync Client - Best Practice Implementation
 * 
 * Features:
 * - OAuth 2.0 token management with auto-refresh
 * - Efficient bulk pagination ($top=1000)
 * - Parallel requests for maximum throughput
 * - Retry logic with exponential backoff
 * - Progress tracking
 * - TypeScript types
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
 */

// =============================================================================
// TYPES
// =============================================================================

export interface Property {
  ListingKey: string;
  ListingId?: string;
  ListPrice: number;
  ListPriceCurrencyCode: string;
  StandardStatus: 'Active' | 'Pending' | 'Closed' | 'Withdrawn';
  PropertyType: string;
  PropertyClass: 'RESI' | 'RLSE' | 'COMS' | 'COML' | 'LAND';  // Sale vs Lease classification
  DevelopmentStatus?: 'Proposed' | 'Under Construction' | 'Complete' | null;  // Construction stage
  City: string;
  StateOrProvince?: string;
  PostalCode?: string;
  BedroomsTotal?: number;
  BathroomsTotalInteger?: number;
  LivingArea?: number;
  Latitude?: number;
  Longitude?: number;
  ModificationTimestamp?: string;
  X_MainPhoto?: string;
  media?: Media[]; // Attached media/photos
  [key: string]: unknown; // Allow extension fields
}

export interface Media {
  MediaKey: string;
  ResourceRecordKey: string; // = Property.ListingKey
  MediaURL: string;
  MediaCategory: 'Photo' | 'Floorplan' | 'Document' | 'Video' | string;
  Order: number;
  ShortDescription?: string;
  MediaModificationTimestamp?: string;
  [key: string]: unknown;
}

export interface ODataResponse<T> {
  '@odata.context': string;
  '@odata.count'?: number;
  '@odata.nextLink'?: string;
  value: T[];
}

export interface TokenResponse {
  access_token: string;
  token_type: 'Bearer';
  expires_in: number;
}

export interface SyncProgress {
  total: number;
  fetched: number;
  percent: number;
  elapsedMs: number;
  estimatedRemainingMs: number;
  propertiesPerSecond: number;
}

export interface SyncOptions {
  filter?: string;
  select?: string[];
  pageSize?: number;
  maxConcurrent?: number;
  onProgress?: (progress: SyncProgress) => void;
  onBatch?: (properties: Property[]) => void | Promise<void>;
}

// =============================================================================
// MLS SYNC CLIENT
// =============================================================================

export class MLSSyncClient {
  private baseUrl: string;
  private clientId: string;
  private clientSecret: string;
  private accessToken: string | null = null;
  private tokenExpiry: number = 0;

  constructor(config: {
    baseUrl: string;
    clientId: string;
    clientSecret: string;
  }) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.clientId = config.clientId;
    this.clientSecret = config.clientSecret;
  }

  // ---------------------------------------------------------------------------
  // OAuth Token Management
  // ---------------------------------------------------------------------------

  private async getToken(): Promise<string> {
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

    const data: TokenResponse = await response.json();
    this.accessToken = data.access_token;
    this.tokenExpiry = Date.now() + data.expires_in * 1000;

    return this.accessToken;
  }

  // ---------------------------------------------------------------------------
  // HTTP Request with Retry
  // ---------------------------------------------------------------------------

  private async fetchWithRetry<T>(
    url: string,
    retries = 3,
    backoffMs = 1000
  ): Promise<T> {
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

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------------------
  // Get Total Count
  // ---------------------------------------------------------------------------

  async getPropertyCount(filter?: string): Promise<number> {
    let url = `${this.baseUrl}/odata/Property?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;

    const response = await this.fetchWithRetry<ODataResponse<Property>>(url);
    return response['@odata.count'] ?? 0;
  }

  // ---------------------------------------------------------------------------
  // Fetch Single Page
  // ---------------------------------------------------------------------------

  async fetchPage(options: {
    skip?: number;
    top?: number;
    filter?: string;
    select?: string[];
  }): Promise<ODataResponse<Property>> {
    const params = new URLSearchParams();
    
    if (options.top) params.set('$top', String(options.top));
    if (options.skip) params.set('$skip', String(options.skip));
    if (options.filter) params.set('$filter', options.filter);
    if (options.select?.length) params.set('$select', options.select.join(','));

    const url = `${this.baseUrl}/odata/Property?${params}`;
    return this.fetchWithRetry<ODataResponse<Property>>(url);
  }

  // ---------------------------------------------------------------------------
  // Full Sync - Sequential (Simple)
  // ---------------------------------------------------------------------------

  async syncAllSequential(options: SyncOptions = {}): Promise<Property[]> {
    const {
      filter,
      select,
      pageSize = 1000,
      onProgress,
      onBatch,
    } = options;

    const startTime = Date.now();
    const allProperties: Property[] = [];
    
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

  async syncAllParallel(options: SyncOptions = {}): Promise<Property[]> {
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
    
    const allProperties: Property[] = new Array(total);
    let completedPages = 0;
    let fetchedCount = 0;

    // Create page fetch tasks
    const fetchPageTask = async (pageIndex: number): Promise<void> => {
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
      const batch: Promise<void>[] = [];
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

  async syncModifiedSince(
    since: Date,
    options: Omit<SyncOptions, 'filter'> = {}
  ): Promise<Property[]> {
    const isoDate = since.toISOString();
    const filter = `ModificationTimestamp gt ${isoDate}`;
    
    return this.syncAllParallel({
      ...options,
      filter,
    });
  }

  // ---------------------------------------------------------------------------
  // Media Sync
  // ---------------------------------------------------------------------------

  /**
   * Get total media count
   */
  async getMediaCount(filter?: string): Promise<number> {
    let url = `${this.baseUrl}/odata/Media?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;

    const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
    return response['@odata.count'] ?? 0;
  }

  /**
   * Fetch media for a single property
   */
  async getPropertyMedia(listingKey: string): Promise<Media[]> {
    const url = `${this.baseUrl}/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`;
    const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
    return response.value;
  }

  /**
   * Fetch media for multiple properties (bulk)
   */
  async getMediaForProperties(listingKeys: string[]): Promise<Map<string, Media[]>> {
    const mediaMap = new Map<string, Media[]>();
    
    // Process in batches of 50 to avoid URL length limits
    const batchSize = 50;
    for (let i = 0; i < listingKeys.length; i += batchSize) {
      const batch = listingKeys.slice(i, i + batchSize);
      const keyList = batch.map(k => `'${k}'`).join(',');
      const filter = `ResourceRecordKey in (${keyList})`;
      
      const url = `${this.baseUrl}/odata/Media?$filter=${encodeURIComponent(filter)}&$orderby=ResourceRecordKey,Order&$top=1000`;
      const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
      
      // Group by property
      for (const m of response.value) {
        const key = m.ResourceRecordKey;
        if (!mediaMap.has(key)) mediaMap.set(key, []);
        mediaMap.get(key)!.push(m);
      }
    }
    
    return mediaMap;
  }

  /**
   * Sync all media (for full database sync)
   */
  async syncAllMedia(options: {
    pageSize?: number;
    onProgress?: (progress: SyncProgress) => void;
  } = {}): Promise<Media[]> {
    const { pageSize = 1000, onProgress } = options;
    const startTime = Date.now();
    const allMedia: Media[] = [];
    
    const total = await this.getMediaCount();
    let fetched = 0;
    let skip = 0;

    while (true) {
      const url = `${this.baseUrl}/odata/Media?$top=${pageSize}&$skip=${skip}&$orderby=ResourceRecordKey,Order`;
      const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
      
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
   */
  async syncAllWithMedia(options: SyncOptions = {}): Promise<Property[]> {
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
    const mediaMap = new Map<string, Media[]>();
    for (const m of allMedia) {
      const key = m.ResourceRecordKey;
      if (!mediaMap.has(key)) mediaMap.set(key, []);
      mediaMap.get(key)!.push(m);
    }

    for (const p of properties) {
      p.media = mediaMap.get(p.ListingKey) || [];
    }

    return properties;
  }
}

// =============================================================================
// REACT HOOK
// =============================================================================

import { useState, useCallback, useRef } from 'react';

export function useMLSSync(client: MLSSyncClient) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef(false);

  const syncAll = useCallback(async (options?: SyncOptions) => {
    setLoading(true);
    setError(null);
    setProgress(null);
    abortRef.current = false;

    try {
      const properties = await client.syncAllParallel({
        ...options,
        onProgress: (p) => {
          if (!abortRef.current) setProgress(p);
          options?.onProgress?.(p);
        },
      });
      return properties;
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const abort = useCallback(() => {
    abortRef.current = true;
  }, []);

  return { syncAll, loading, progress, error, abort };
}

// =============================================================================
// USAGE EXAMPLES
// =============================================================================

/*
// Initialize client
const mlsClient = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// ---------------------------------------------------------------------------
// PROPERTIES ONLY
// ---------------------------------------------------------------------------

// Option 1: Full sync with progress
const properties = await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal', 'X_MainPhoto'],
  maxConcurrent: 3,
  onProgress: (p) => {
    console.log(`${p.percent}% - ${p.propertiesPerSecond} props/sec`);
  },
});

// Option 2: Incremental sync (changes since last sync)
const lastSync = new Date('2024-12-01T00:00:00Z');
const updates = await mlsClient.syncModifiedSince(lastSync);

// ---------------------------------------------------------------------------
// PROPERTIES WITH MEDIA (PHOTOS)
// ---------------------------------------------------------------------------

// Option 3: Full sync with all media attached
const propertiesWithMedia = await mlsClient.syncAllWithMedia({
  filter: "StandardStatus eq 'Active'",
  onProgress: (p) => console.log(`${p.percent}%`),
});

// Each property now has .media array
propertiesWithMedia.forEach(p => {
  console.log(`${p.ListingKey}: ${p.media?.length || 0} photos`);
  p.media?.forEach(m => console.log(`  - ${m.MediaURL}`));
});

// Option 4: Get media for specific properties
const listingKeys = ['QOBRIX_123', 'QOBRIX_456', 'QOBRIX_789'];
const mediaMap = await mlsClient.getMediaForProperties(listingKeys);

listingKeys.forEach(key => {
  const photos = mediaMap.get(key) || [];
  console.log(`${key}: ${photos.length} photos`);
});

// Option 5: Get media for single property (on-demand)
const singlePropertyMedia = await mlsClient.getPropertyMedia('QOBRIX_123');
console.log(`Found ${singlePropertyMedia.length} photos`);

// ---------------------------------------------------------------------------
// REACT COMPONENT
// ---------------------------------------------------------------------------

function PropertyGallery({ listingKey }: { listingKey: string }) {
  const [media, setMedia] = useState<Media[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    mlsClient.getPropertyMedia(listingKey)
      .then(setMedia)
      .finally(() => setLoading(false));
  }, [listingKey]);

  if (loading) return <div>Loading photos...</div>;

  return (
    <div className="grid grid-cols-3 gap-2">
      {media.map(m => (
        <img 
          key={m.MediaKey} 
          src={m.MediaURL} 
          alt={m.ShortDescription || `Photo ${m.Order}`}
          className="w-full h-32 object-cover rounded"
        />
      ))}
    </div>
  );
}

function SyncButton() {
  const { syncAll, loading, progress, error } = useMLSSync(mlsClient);

  const handleSync = async () => {
    const props = await syncAll({
      filter: "StandardStatus eq 'Active'",
    });
    console.log(`Synced ${props.length} properties`);
  };

  return (
    <div>
      <button onClick={handleSync} disabled={loading}>
        {loading ? 'Syncing...' : 'Sync Properties'}
      </button>
      {progress && (
        <div>
          {progress.percent}% ({progress.fetched}/{progress.total})
          <br />
          {progress.propertiesPerSecond} props/sec
        </div>
      )}
      {error && <div style={{ color: 'red' }}>{error.message}</div>}
    </div>
  );
}
*/

export default MLSSyncClient;
