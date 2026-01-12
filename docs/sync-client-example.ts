/**
 * RESO MLS Sync Client - Best Practice Implementation (TypeScript)
 * 
 * Features:
 * - OAuth 2.0 token management with auto-refresh
 * - Efficient bulk pagination ($top=1000)
 * - Parallel requests for maximum throughput
 * - Retry logic with exponential backoff
 * - Progress tracking with UI integration examples
 * - TypeScript types
 * - Multi-tenant support (Qobrix + Dash data sources)
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
// TYPES
// =============================================================================

export interface Property {
  ListingKey: string;
  ListingId?: string;
  ListPrice: number;
  ListPriceCurrencyCode?: string;
  StandardStatus: 'Active' | 'Pending' | 'Closed' | 'Withdrawn';
  PropertyType: string;
  PropertyClass: 'RESI' | 'RLSE' | 'COMS' | 'COML' | 'LAND';
  DevelopmentStatus?: 'Proposed' | 'Under Construction' | 'Complete' | null;
  City: string;
  StateOrProvince?: string;
  PostalCode?: string;
  Country?: string;
  BedroomsTotal?: number;
  BathroomsTotalInteger?: number;
  BathroomsHalf?: number;
  LivingArea?: number;
  LotSizeSquareFeet?: number;
  Latitude?: number;
  Longitude?: number;
  ModificationTimestamp?: string;
  PublicRemarks?: string;
  
  // RESO DD 2.0 Feature Fields (populated from Dash data)
  YearBuilt?: number;
  View?: string;
  Flooring?: string;
  Heating?: string;
  Cooling?: string;
  PoolFeatures?: string;
  FireplaceYN?: boolean;
  FireplaceFeatures?: string;
  ParkingFeatures?: string;
  Fencing?: string;
  
  // Agent/Office Fields
  ListAgentKey?: string;
  ListAgentFirstName?: string;
  ListAgentLastName?: string;
  ListAgentEmail?: string;
  ListOfficeName?: string;
  ListOfficeKey?: string;
  
  // Multi-tenant Fields
  /** Office key: 'CSIR' (Qobrix) or 'HSIR' (Dash) */
  OriginatingSystemOfficeKey: 'CSIR' | 'HSIR';
  /** Data source: 'qobrix' or 'dash_sothebys' */
  X_DataSource: 'qobrix' | 'dash_sothebys';
  
  // Extension Fields (X_ prefix)
  X_ListingUrl?: string;
  X_CurrencyCode?: string;
  X_ListPriceUSD?: number;
  X_QobrixId?: string;
  X_QobrixRef?: string;
  
  /** Main photo URL - populated via getMainPhotos() from Media where Order=0 */
  mainPhoto?: string;
  /** All media - populated via syncAllWithMedia() or getPropertyMedia() */
  media?: Media[];
  [key: string]: unknown;
}

export interface Media {
  MediaKey: string;
  ResourceRecordKey: string;
  MediaURL: string;
  MediaCategory: 'Photo' | 'Floorplan' | 'Document' | 'Video' | string;
  Order: number;
  ShortDescription?: string;
  LongDescription?: string;
  MediaModificationTimestamp?: string;
  /** Image width in pixels (available for Dash photos) */
  ImageWidth?: number;
  /** Image height in pixels (available for Dash photos) */
  ImageHeight?: number;
  /** Office key: 'CSIR' (Qobrix) or 'HSIR' (Dash) */
  OriginatingSystemOfficeKey: 'CSIR' | 'HSIR';
  /** Data source: 'qobrix' or 'dash_sothebys' */
  X_DataSource: 'qobrix' | 'dash_sothebys';
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

/**
 * Progress callback data - use this to update your UI progress bar
 * 
 * @example
 * // React state update
 * onProgress: (p) => setProgress(p)
 * 
 * // DOM update
 * onProgress: (p) => {
 *   progressBar.style.width = `${p.percent}%`;
 *   progressText.textContent = `${p.fetched}/${p.total}`;
 * }
 */
export interface SyncProgress {
  /** Total number of items to sync */
  total: number;
  /** Number of items fetched so far */
  fetched: number;
  /** Completion percentage (0-100) */
  percent: number;
  /** Time elapsed in milliseconds */
  elapsedMs: number;
  /** Estimated remaining time in milliseconds */
  estimatedRemainingMs: number;
  /** Current sync speed (items per second) */
  propertiesPerSecond: number;
}

export interface SyncOptions {
  /** OData $filter expression (e.g., "StandardStatus eq 'Active'") */
  filter?: string;
  /** Fields to return (reduces payload size) */
  select?: string[];
  /** Items per page (default: 1000, max: 1000) */
  pageSize?: number;
  /** Parallel requests (default: 3) */
  maxConcurrent?: number;
  /** Progress callback - called after each page fetch */
  onProgress?: (progress: SyncProgress) => void;
  /** Batch callback - called with each page of results */
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

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------------------
  // Count & Page Methods
  // ---------------------------------------------------------------------------

  async getPropertyCount(filter?: string): Promise<number> {
    let url = `${this.baseUrl}/odata/Property?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;

    const response = await this.fetchWithRetry<ODataResponse<Property>>(url);
    return response['@odata.count'] ?? 0;
  }

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
  // Full Sync - Sequential
  // ---------------------------------------------------------------------------

  async syncAllSequential(options: SyncOptions = {}): Promise<Property[]> {
    const { filter, select, pageSize = 1000, onProgress, onBatch } = options;

    const startTime = Date.now();
    const allProperties: Property[] = [];
    const total = await this.getPropertyCount(filter);
    let fetched = 0;
    let skip = 0;

    while (true) {
      const response = await this.fetchPage({ skip, top: pageSize, filter, select });
      const batch = response.value;
      allProperties.push(...batch);
      fetched += batch.length;

      if (onBatch) await onBatch(batch);

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

  async syncAllParallel(options: SyncOptions = {}): Promise<Property[]> {
    const { filter, select, pageSize = 1000, maxConcurrent = 3, onProgress, onBatch } = options;

    const startTime = Date.now();
    const total = await this.getPropertyCount(filter);
    const totalPages = Math.ceil(total / pageSize);
    
    const allProperties: Property[] = new Array(total);
    let completedPages = 0;
    let fetchedCount = 0;

    const fetchPageTask = async (pageIndex: number): Promise<void> => {
      const skip = pageIndex * pageSize;
      const response = await this.fetchPage({ skip, top: pageSize, filter, select });
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

    for (let i = 0; i < totalPages; i += maxConcurrent) {
      const batch: Promise<void>[] = [];
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

  async syncModifiedSince(
    since: Date,
    options: Omit<SyncOptions, 'filter'> = {}
  ): Promise<Property[]> {
    const filter = `ModificationTimestamp gt ${since.toISOString()}`;
    return this.syncAllParallel({ ...options, filter });
  }

  // ---------------------------------------------------------------------------
  // Media Methods
  // ---------------------------------------------------------------------------

  async getMediaCount(filter?: string): Promise<number> {
    let url = `${this.baseUrl}/odata/Media?$top=0&$count=true`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;
    const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
    return response['@odata.count'] ?? 0;
  }

  /**
   * Get main photo URLs for multiple properties (batch request)
   * Returns Map of ListingKey -> MediaURL for first photo (Order=0)
   * 
   * @example
   * const photos = await client.getMainPhotos(properties.map(p => p.ListingKey));
   * properties.forEach(p => p.mainPhoto = photos.get(p.ListingKey));
   */
  /**
   * Get main photo URLs for multiple properties (batch request)
   * Returns Map of ListingKey -> MediaURL for first photo (Order=0)
   * 
   * @example
   * const photos = await client.getMainPhotos(properties.map(p => p.ListingKey));
   * properties.forEach(p => p.mainPhoto = photos.get(p.ListingKey));
   */
  async getMainPhotos(listingKeys: string[]): Promise<Map<string, string>> {
    const photoMap = new Map<string, string>();
    const batchSize = 200; // ~200 keys per request (URL length safe)
    const maxConcurrent = 3; // Parallel batch requests
    
    // Create batch requests
    const batches: string[][] = [];
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
          return this.fetchWithRetry<ODataResponse<Media>>(url);
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

  async getPropertyMedia(listingKey: string): Promise<Media[]> {
    const url = `${this.baseUrl}/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`;
    const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
    return response.value;
  }

  async getMediaForProperties(listingKeys: string[]): Promise<Map<string, Media[]>> {
    const mediaMap = new Map<string, Media[]>();
    const batchSize = 50;
    
    for (let i = 0; i < listingKeys.length; i += batchSize) {
      const batch = listingKeys.slice(i, i + batchSize);
      const keyList = batch.map(k => `'${k}'`).join(',');
      const url = `${this.baseUrl}/odata/Media?$filter=${encodeURIComponent(`ResourceRecordKey in (${keyList})`)}&$orderby=ResourceRecordKey,Order&$top=1000`;
      const response = await this.fetchWithRetry<ODataResponse<Media>>(url);
      
      for (const m of response.value) {
        if (!mediaMap.has(m.ResourceRecordKey)) mediaMap.set(m.ResourceRecordKey, []);
        mediaMap.get(m.ResourceRecordKey)!.push(m);
      }
    }
    
    return mediaMap;
  }

  async syncAllMedia(options: { pageSize?: number; onProgress?: (progress: SyncProgress) => void } = {}): Promise<Media[]> {
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

      if (!response['@odata.nextLink'] || response.value.length < pageSize) break;
      skip += pageSize;
    }

    return allMedia;
  }

  async syncAllWithMedia(options: SyncOptions = {}): Promise<Property[]> {
    const { onProgress } = options;
    
    const properties = await this.syncAllParallel({
      ...options,
      onProgress: onProgress ? (p) => onProgress({ ...p, percent: Math.round(p.percent * 0.6) }) : undefined,
    });

    const allMedia = await this.syncAllMedia({
      onProgress: onProgress ? (p) => onProgress({ ...p, percent: 60 + Math.round(p.percent * 0.4) }) : undefined,
    });

    const mediaMap = new Map<string, Media[]>();
    for (const m of allMedia) {
      if (!mediaMap.has(m.ResourceRecordKey)) mediaMap.set(m.ResourceRecordKey, []);
      mediaMap.get(m.ResourceRecordKey)!.push(m);
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
      return await client.syncAllParallel({
        ...options,
        onProgress: (p) => {
          if (!abortRef.current) setProgress(p);
          options?.onProgress?.(p);
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [client]);

  const abort = useCallback(() => { abortRef.current = true; }, []);

  return { syncAll, loading, progress, error, abort };
}

// =============================================================================
// USAGE EXAMPLES
// =============================================================================

/*
// ---------------------------------------------------------------------------
// 1. BASIC USAGE
// ---------------------------------------------------------------------------

const mlsClient = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// Sync all active properties (from all data sources your client has access to)
const properties = await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
});


// ---------------------------------------------------------------------------
// 1a. FILTER BY DATA SOURCE
// ---------------------------------------------------------------------------

// Sync only Qobrix data
const qobrixProperties = await mlsClient.syncAllParallel({
  filter: "OriginatingSystemOfficeKey eq 'CSIR'",
});

// Sync only Dash/Sotheby's data
const dashProperties = await mlsClient.syncAllParallel({
  filter: "OriginatingSystemOfficeKey eq 'HSIR'",
});

// Combine filters
const activeDashProperties = await mlsClient.syncAllParallel({
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
const properties = await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal', 'BathroomsTotalInteger'],
});

// Step 2: Batch fetch main photos (single request per 100 properties)
const photoMap = await mlsClient.getMainPhotos(properties.map(p => p.ListingKey));

// Step 3: Attach to properties
properties.forEach(p => {
  p.mainPhoto = photoMap.get(p.ListingKey) || null;
});

// Now use in your UI:
// properties.forEach(p => console.log(p.ListPrice, p.mainPhoto));


// ---------------------------------------------------------------------------
// 1c. PROPERTY DETAIL PAGE - Fetch All Photos on Click
// ---------------------------------------------------------------------------

// When user clicks a property card, fetch all photos for the detail page:

// Vanilla JS
async function showPropertyDetail(listingKey: string) {
  // Fetch all photos for this property
  const photos = await mlsClient.getPropertyMedia(listingKey);
  
  // photos is sorted by Order (first photo = main photo)
  console.log(`Found ${photos.length} photos`);
  photos.forEach((photo, i) => {
    console.log(`  [${photo.Order}] ${photo.MediaCategory}: ${photo.MediaURL}`);
  });
  
  return photos;
}

// React Component - Property Detail with Gallery
function PropertyDetail({ listingKey }: { listingKey: string }) {
  const [photos, setPhotos] = useState<Media[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    mlsClient.getPropertyMedia(listingKey)
      .then(setPhotos)
      .finally(() => setLoading(false));
  }, [listingKey]);

  if (loading) return <div>Loading photos...</div>;
  if (photos.length === 0) return <div>No photos available</div>;

  return (
    <div className="property-gallery">
      {// Main Image }
      <img 
        src={photos[activeIndex].MediaURL} 
        alt={photos[activeIndex].ShortDescription || `Photo ${activeIndex + 1}`}
        className="w-full h-96 object-cover rounded-lg"
      />
      
      {// Thumbnail Strip }
      <div className="flex gap-2 mt-4 overflow-x-auto">
        {photos.map((photo, i) => (
          <img
            key={photo.MediaKey}
            src={photo.MediaURL}
            alt={`Thumbnail ${i + 1}`}
            onClick={() => setActiveIndex(i)}
            className={`w-20 h-20 object-cover rounded cursor-pointer ${
              i === activeIndex ? 'ring-2 ring-blue-500' : 'opacity-70 hover:opacity-100'
            }`}
          />
        ))}
      </div>
      
      {// Photo Counter }
      <p className="text-sm text-gray-500 mt-2">
        {activeIndex + 1} / {photos.length} photos
      </p>
    </div>
  );
}

// React Hook for Property Detail
function usePropertyDetail(listingKey: string | null) {
  const [property, setProperty] = useState<Property | null>(null);
  const [photos, setPhotos] = useState<Media[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!listingKey) return;
    
    setLoading(true);
    
    // Fetch property and photos in parallel
    Promise.all([
      mlsClient.fetchPage({ 
        filter: `ListingKey eq '${listingKey}'`,
        top: 1 
      }),
      mlsClient.getPropertyMedia(listingKey)
    ])
    .then(([propResponse, mediaResponse]) => {
      setProperty(propResponse.value[0] || null);
      setPhotos(mediaResponse);
    })
    .finally(() => setLoading(false));
  }, [listingKey]);

  return { property, photos, loading };
}

// Usage:
// const { property, photos, loading } = usePropertyDetail('QOBRIX_abc123');


// ---------------------------------------------------------------------------
// 2. PROGRESS BAR - VANILLA JAVASCRIPT
// ---------------------------------------------------------------------------

// HTML:
// <div class="progress-container">
//   <div class="progress-bar" id="progressBar"></div>
// </div>
// <p id="progressText">Ready</p>
// <p id="speedText"></p>

// CSS:
// .progress-container { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
// .progress-bar { height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); transition: width 0.3s ease; }

const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const speedText = document.getElementById('speedText');

await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  onProgress: (p) => {
    // Update progress bar width
    progressBar.style.width = `${p.percent}%`;

    // Update text
    progressText.textContent = `${p.percent}% (${p.fetched.toLocaleString()} / ${p.total.toLocaleString()})`;

    // Show speed and ETA
    const etaSeconds = Math.round(p.estimatedRemainingMs / 1000);
    speedText.textContent = `${p.propertiesPerSecond} items/sec • ETA: ${etaSeconds}s`;
  },
});

progressText.textContent = 'Sync complete!';


// ---------------------------------------------------------------------------
// 3. PROGRESS BAR - REACT COMPONENT
// ---------------------------------------------------------------------------

import { useState } from 'react';

function SyncProgressBar() {
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    setProgress(null);
    
    try {
      const properties = await mlsClient.syncAllParallel({
        filter: "StandardStatus eq 'Active'",
        onProgress: setProgress,  // Direct state update!
      });
      console.log(`Synced ${properties.length} properties`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="p-4">
      <button 
        onClick={handleSync} 
        disabled={syncing}
        className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
      >
        {syncing ? 'Syncing...' : 'Start Sync'}
      </button>

      {progress && (
        <div className="mt-4">
          {// Progress bar }
          <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
          
          {// Stats }
          <div className="mt-2 text-sm text-gray-600 flex justify-between">
            <span>{progress.percent}% ({progress.fetched.toLocaleString()} / {progress.total.toLocaleString()})</span>
            <span>{progress.propertiesPerSecond} items/sec</span>
          </div>
          
          {// ETA }
          <p className="text-xs text-gray-400">
            ETA: {Math.round(progress.estimatedRemainingMs / 1000)}s
          </p>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// 4. PROGRESS BAR - USING THE REACT HOOK
// ---------------------------------------------------------------------------

function SyncWithHook() {
  const { syncAll, loading, progress, error } = useMLSSync(mlsClient);

  const handleSync = async () => {
    const properties = await syncAll({
      filter: "StandardStatus eq 'Active'",
    });
    console.log(`Got ${properties.length} properties`);
  };

  return (
    <div>
      <button onClick={handleSync} disabled={loading}>
        {loading ? 'Syncing...' : 'Sync'}
      </button>
      
      {progress && (
        <div>
          <progress value={progress.percent} max={100} />
          <span>{progress.percent}%</span>
          <span>{progress.propertiesPerSecond} items/sec</span>
        </div>
      )}
      
      {error && <p className="text-red-500">{error.message}</p>}
    </div>
  );
}


// ---------------------------------------------------------------------------
// 5. TWO-PHASE PROGRESS (Properties + Media)
// ---------------------------------------------------------------------------

// When syncing both properties and media, show which phase is active:

function TwoPhaseSync() {
  const [phase, setPhase] = useState<'idle' | 'properties' | 'media'>('idle');
  const [progress, setProgress] = useState<SyncProgress | null>(null);

  const handleSync = async () => {
    // Phase 1: Properties (0-60%)
    setPhase('properties');
    const properties = await mlsClient.syncAllParallel({
      onProgress: (p) => setProgress({ ...p, percent: Math.round(p.percent * 0.6) }),
    });

    // Phase 2: Media (60-100%)
    setPhase('media');
    const media = await mlsClient.syncAllMedia({
      onProgress: (p) => setProgress({ ...p, percent: 60 + Math.round(p.percent * 0.4) }),
    });

    setPhase('idle');
  };

  return (
    <div>
      <button onClick={handleSync}>Sync All</button>
      {progress && (
        <div>
          <p>Phase: {phase}</p>
          <progress value={progress.percent} max={100} />
          <span>{progress.percent}%</span>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// 6. ANIMATED PROGRESS BAR (CSS-only animation)
// ---------------------------------------------------------------------------

// CSS:
// .progress-bar-animated {
//   background: linear-gradient(
//     90deg,
//     #4CAF50 0%,
//     #8BC34A 50%,
//     #4CAF50 100%
//   );
//   background-size: 200% 100%;
//   animation: shimmer 1.5s ease-in-out infinite;
// }
// @keyframes shimmer {
//   0% { background-position: 200% 0; }
//   100% { background-position: -200% 0; }
// }

// React JSX:
// <div 
//   className={`h-full ${syncing ? 'progress-bar-animated' : 'bg-green-500'}`}
//   style={{ width: `${progress.percent}%` }}
// />

*/

export default MLSSyncClient;
