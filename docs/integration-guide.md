# Integration Guide

Connect your real estate website to the RESO Web API.

## API Base URL

```
https://your-server.com/reso
```

## Authentication

OAuth 2.0 Client Credentials flow (RESO Web API Core compliant).

### Step 1: Get Access Token

```bash
curl -X POST https://your-server.com/reso/oauth/token \
  -u "client_id:client_secret" \
  -d "grant_type=client_credentials"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Step 2: Use Bearer Token

```javascript
const response = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
```

### JavaScript Helper

```javascript
const API_URL = 'https://your-server.com/reso';
const CLIENT_ID = 'your-client-id';
const CLIENT_SECRET = 'your-client-secret';

async function getAccessToken() {
  const credentials = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
  const response = await fetch(`${API_URL}/oauth/token`, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: 'grant_type=client_credentials'
  });
  const data = await response.json();
  return data.access_token;
}

// Usage
const token = await getAccessToken();
const properties = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 401 | Unauthorized | No token provided |
| 401 | InvalidToken | Token expired or invalid |

## Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /oauth/token` | Get OAuth access token |
| `GET /odata/Property` | Property listings |
| `GET /odata/Property('{key}')` | Single property |
| `GET /odata/Media` | Property photos |
| `GET /odata/Member` | Agents |
| `GET /odata/Office` | Offices/agencies |
| `GET /odata/Contacts` | Contacts |
| `GET /odata/ShowingAppointment` | Showing appointments |
| `GET /docs` | Swagger UI |

## Quick Start

```javascript
const API_URL = 'https://your-server.com/reso';

// Get token first
const token = await getAccessToken();

// Fetch active properties
const response = await fetch(
  `${API_URL}/odata/Property?$filter=StandardStatus eq 'Active'&$top=20`,
  { headers: { 'Authorization': `Bearer ${token}` } }
);
const data = await response.json();

console.log(data.value); // Array of properties
```

### Response Format

```json
{
  "@odata.context": "https://your-server.com/reso/$metadata#Property",
  "@odata.count": 14034,
  "value": [
    {
      "ListingKey": "QOBRIX_abc123",
      "ListPrice": 750000,
      "ListPriceCurrencyCode": "EUR",
      "City": "Miami",
      "StandardStatus": "Active",
      "BedroomsTotal": 3,
      "BathroomsTotalInteger": 2,
      "LivingArea": 1500,
      "Latitude": 25.7617,
      "Longitude": -80.1918
    }
  ],
  "@odata.nextLink": "https://your-server.com/reso/odata/Property?$skip=20&$top=20"
}
```

## OData Query Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `$filter` | `StandardStatus eq 'Active'` | Filter results |
| `$select` | `ListingKey,ListPrice,City` | Select fields |
| `$orderby` | `ListPrice desc` | Sort results |
| `$top` | `20` | Limit results |
| `$skip` | `40` | Pagination offset |
| `$count` | `true` | Include total count |

### Pagination Limits

| Setting | Value | Description |
|---------|-------|-------------|
| Default | 100 | If `$top` not specified |
| Maximum | 1000 | Hard limit per request |

```bash
# Default (100 properties)
/odata/Property

# Custom page size
/odata/Property?$top=500

# Max enforced (>1000 capped to 1000)
/odata/Property?$top=5000  # returns 1000

# Pagination example
/odata/Property?$top=100&$skip=0    # Page 1
/odata/Property?$top=100&$skip=100  # Page 2
/odata/Property?$top=100&$skip=200  # Page 3
```

The response includes `@odata.nextLink` for automatic pagination.


## Common Queries

```bash
# Active properties
$filter=StandardStatus eq 'Active'

# Price range
$filter=ListPrice ge 500000 and ListPrice lt 1000000

# Bedrooms
$filter=BedroomsTotal ge 3

# City search
$filter=contains(City,'Miami')

# Combined filters
$filter=StandardStatus eq 'Active' and ListPrice lt 500000 and BedroomsTotal ge 2

# Sort by price
$orderby=ListPrice desc

# Pagination (page 3, 20 per page)
$top=20&$skip=40
```


## PropertyClass (Sale vs Lease)

RESO standard field to distinguish sale from lease/rental properties:

| PropertyClass | Description | Count |
|---------------|-------------|-------|
| `RESI` | Residential Sale | ~13,776 |
| `RLSE` | Residential Lease (Rental) | ~36 |
| `COMS` | Commercial Sale | ~182 |
| `COML` | Commercial Lease | ~3 |
| `LAND` | Land | ~69 |

### Filter Examples

```bash
# All rentals (residential)
$filter=PropertyClass eq 'RLSE'

# All for-sale properties
$filter=PropertyClass eq 'RESI' or PropertyClass eq 'COMS' or PropertyClass eq 'LAND'

# Commercial properties (sale + lease)
$filter=PropertyClass eq 'COMS' or PropertyClass eq 'COML'

# Residential rentals under €5000/month
$filter=PropertyClass eq 'RLSE' and LeasePrice lt 5000
```

### JavaScript Example

```javascript
// Get all rental properties
const rentals = await fetch(
  `${API_URL}/odata/Property?$filter=PropertyClass eq 'RLSE'`,
  { headers: { 'Authorization': `Bearer ${token}` } }
).then(r => r.json());

// Check property type
rentals.value.forEach(p => {
  console.log(`${p.ListingKey}: ${p.PropertyClass} - €${p.LeasePrice}/month`);
});
```

## Property Fields

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `ListingKey` | string | Unique ID |
| `ListPrice` | number | Listing price |
| `ListPriceCurrencyCode` | string | Currency (e.g., EUR, USD) |
| `StandardStatus` | string | Active, Pending, Closed, Withdrawn |
| `PropertyType` | string | Apartment, House, Land, etc. |
| `PropertyClass` | string | RESI, RLSE, COMS, COML, LAND |
| `City` | string | City name |
| `BedroomsTotal` | integer | Number of bedrooms |
| `BathroomsTotalInteger` | integer | Number of bathrooms |
| `LivingArea` | number | Interior area (sqm) |
| `Latitude` | number | GPS latitude |
| `Longitude` | number | GPS longitude |

### Extension Fields (X_)

| Field | Description |
|-------|-------------|
| `X_MainPhoto` | Main photo URL |
| `X_SeaView` | Has sea view |
| `X_PrivateSwimmingPool` | Has private pool |
| `X_ShortDescription` | Marketing description |

## Get Property Photos

```javascript
const listingKey = 'QOBRIX_abc123';
const response = await fetch(
  `https://your-server.com/reso/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`,
  { headers: { 'Authorization': `Bearer ${token}` } }
);
const data = await response.json();

data.value.forEach(media => {
  console.log(media.MediaURL);  // Photo URL
  console.log(media.Order);     // Display order
});
```

## TypeScript Types

```typescript
interface Property {
  ListingKey: string;
  ListPrice: number;
  ListPriceCurrencyCode: string;
  StandardStatus: 'Active' | 'Pending' | 'Closed' | 'Withdrawn';
  PropertyType: string;
  PropertyClass: 'RESI' | 'RLSE' | 'COMS' | 'COML' | 'LAND';  // Sale vs Lease
  City: string;
  BedroomsTotal: number;
  BathroomsTotalInteger: number;
  LivingArea: number;
  Latitude: number;
  Longitude: number;
  X_MainPhoto?: string;
}

interface Media {
  MediaKey: string;
  ResourceRecordKey: string;
  MediaURL: string;
  MediaCategory: string;
  Order: number;
}

interface ODataResponse<T> {
  '@odata.context': string;
  '@odata.count'?: number;
  '@odata.nextLink'?: string;
  value: T[];
}

interface TokenResponse {
  access_token: string;
  token_type: 'Bearer';
  expires_in: number;
}
```

## React Example

```tsx
import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_RESO_API_URL;
const CLIENT_ID = import.meta.env.VITE_RESO_CLIENT_ID;
const CLIENT_SECRET = import.meta.env.VITE_RESO_CLIENT_SECRET;

function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  
  const getToken = useCallback(async () => {
    const credentials = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
    const response = await fetch(`${API_URL}/oauth/token`, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: 'grant_type=client_credentials'
    });
    const data = await response.json();
    setToken(data.access_token);
    return data.access_token;
  }, []);

  return { token, getToken };
}

function PropertyList() {
  const { token, getToken } = useAuth();
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      const accessToken = token || await getToken();
      const response = await fetch(
        `${API_URL}/odata/Property?$filter=StandardStatus eq 'Active'&$top=20`,
        { headers: { 'Authorization': `Bearer ${accessToken}` } }
      );
      const data = await response.json();
      setProperties(data.value);
      setLoading(false);
    }
    fetchData();
  }, [token, getToken]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      {properties.map(property => (
        <div key={property.ListingKey} className="border rounded p-4">
          <img src={property.X_MainPhoto} alt="" className="w-full h-48 object-cover" />
          <h3>${property.ListPrice?.toLocaleString()} {property.ListPriceCurrencyCode}</h3>
          <p>{property.City}</p>
          <p>{property.BedroomsTotal} bed | {property.BathroomsTotalInteger} bath</p>
        </div>
      ))}
    </div>
  );
}
```

## Environment Variables

```env
VITE_RESO_API_URL=https://your-server.com/reso
VITE_RESO_CLIENT_ID=your-client-id
VITE_RESO_CLIENT_SECRET=your-client-secret
```

## Error Handling

```javascript
async function fetchWithAuth(url, token, getToken) {
  try {
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 401) {
      // Token expired - refresh and retry
      const newToken = await getToken();
      return fetchWithAuth(url, newToken, getToken);
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'API Error');
    }
    
    return response.json();
  } catch (e) {
    console.error('Request failed:', e);
    throw e;
  }
}
```

## RESO Compliance

This API implements:
- **OAuth 2.0 Client Credentials** flow per RESO Web API Core specification
- **OData 4.0** query syntax
- **RESO Data Dictionary 2.0** field names and types
- Standard error response format

## Bulk Sync Client (TypeScript)

For optimal bulk synchronization, see the full implementation: [`sync-client-example.ts`](sync-client-example.ts)

### Key Features

```typescript
const mlsClient = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});
```

### 1. Full Sync (Parallel - Fastest)

```typescript
const properties = await mlsClient.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
  select: ['ListingKey', 'ListPrice', 'City', 'BedroomsTotal'],
  maxConcurrent: 3,  // 3 parallel requests
  onProgress: (p) => {
    console.log(`${p.percent}% - ${p.propertiesPerSecond} props/sec`);
  },
});
```

### 2. Incremental Sync (Delta)

```typescript
// Only fetch properties modified since last sync
const lastSync = new Date('2024-12-01T00:00:00Z');
const updates = await mlsClient.syncModifiedSince(lastSync);
```

### 3. React Hook

```tsx
function SyncButton() {
  const { syncAll, loading, progress } = useMLSSync(mlsClient);

  return (
    <button onClick={() => syncAll()} disabled={loading}>
      {loading ? `${progress?.percent}%` : 'Sync'}
    </button>
  );
}
```

### Performance Tips

| Tip | Impact |
|-----|--------|
| Use `$top=1000` | Max batch size |
| Use `$select` | Reduce payload |
| Parallel requests (3) | 3x throughput |
| Incremental sync | Minimize data |

### Expected Throughput

| Mode | Properties/Second |
|------|-------------------|
| Sequential | ~1,300 |
| Parallel (3) | ~3,500 |

### Syncing Media (Photos)

```typescript
// Option 1: Full sync with media attached
const propertiesWithMedia = await client.syncAllWithMedia({
  filter: "StandardStatus eq 'Active'",
});

// Each property has .media array
propertiesWithMedia.forEach(p => {
  console.log(`${p.ListingKey}: ${p.media?.length} photos`);
});

// Option 2: On-demand for single property
const photos = await client.getPropertyMedia('QOBRIX_123');

// Option 3: Bulk fetch for multiple properties
const mediaMap = await client.getMediaForProperties(['KEY1', 'KEY2']);
```

### Best Practice: Use X_MainPhoto for Listings

```typescript
// For listing pages, X_MainPhoto is already included - no extra request!
const props = await client.syncAllParallel({
  select: ['ListingKey', 'ListPrice', 'City', 'X_MainPhoto'],
});

// Use X_MainPhoto directly
props.forEach(p => {
  console.log(p.X_MainPhoto); // Main image URL
});
```

## Vanilla JavaScript Client

For projects without TypeScript, use [`sync-client-example.js`](sync-client-example.js):

```html
<script src="sync-client-example.js"></script>
<script>
  const client = new MLSSyncClient({
    baseUrl: 'https://your-server.com/reso',
    clientId: 'your-client-id',
    clientSecret: 'your-client-secret',
  });

  // Sync all properties
  client.syncAllParallel({
    filter: "StandardStatus eq 'Active'",
    onProgress: (p) => console.log(p.percent + '%'),
  }).then(properties => {
    console.log('Synced', properties.length, 'properties');
  });

  // Get single property with all photos
  client.getPropertyWithMedia('QOBRIX_123').then(property => {
    console.log(property.ListPrice, property.media.length, 'photos');
  });
</script>
```
