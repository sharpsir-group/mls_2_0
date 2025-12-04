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
  [key: string]: unknown; // Allow extension fields
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
// USAGE EXAMPLE
// =============================================================================

/*
// Initialize client
const mlsClient = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// Option 1: Full sync with progress
const properties = await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal'],
  maxConcurrent: 3,
  onProgress: (p) => {
    console.log(`${p.percent}% - ${p.propertiesPerSecond} props/sec`);
  },
});

// Option 2: Incremental sync (changes since last sync)
const lastSync = new Date('2024-12-01T00:00:00Z');
const updates = await mlsClient.syncModifiedSince(lastSync);

// Option 3: React component
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
