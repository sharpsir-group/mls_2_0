# Integration Guide

Connect your real estate website to the RESO Web API.

## API Base URL

```
https://your-server.com/reso
```

## Authentication

OAuth 2.0 Client Credentials flow (RESO Web API Core compliant).

### Get Access Token

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

### Use Bearer Token

```javascript
const response = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
```

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

## OData Query Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `$filter` | `StandardStatus eq 'Active'` | Filter results |
| `$select` | `ListingKey,ListPrice,City` | Select fields |
| `$orderby` | `ListPrice desc` | Sort results |
| `$top` | `20` (max: 1000) | Limit results |
| `$skip` | `40` | Pagination offset |
| `$count` | `true` | Include total count |

## Common Filters

```bash
# Active properties
$filter=StandardStatus eq 'Active'

# Price range
$filter=ListPrice ge 500000 and ListPrice lt 1000000

# Bedrooms
$filter=BedroomsTotal ge 3

# City search
$filter=contains(City,'Miami')

# Combined
$filter=StandardStatus eq 'Active' and ListPrice lt 500000 and BedroomsTotal ge 2
```

## PropertyClass (Sale vs Lease)

| PropertyClass | Description |
|---------------|-------------|
| `RESI` | Residential Sale |
| `RLSE` | Residential Lease (Rental) |
| `COMS` | Commercial Sale |
| `COML` | Commercial Lease |
| `LAND` | Land |

```bash
# Rentals only
$filter=PropertyClass eq 'RLSE'

# For-sale only
$filter=PropertyClass eq 'RESI' or PropertyClass eq 'COMS' or PropertyClass eq 'LAND'
```

## Property Fields

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `ListingKey` | string | Unique ID |
| `ListPrice` | number | Listing price |
| `ListPriceCurrencyCode` | string | Currency (EUR, USD) |
| `StandardStatus` | string | Active, Pending, Closed, Withdrawn |
| `PropertyType` | string | Apartment, House, Land |
| `PropertyClass` | string | RESI, RLSE, COMS, COML, LAND |
| `City` | string | City name |
| `BedroomsTotal` | integer | Bedrooms |
| `BathroomsTotalInteger` | integer | Bathrooms |
| `LivingArea` | number | Interior area (sqm) |
| `Latitude` / `Longitude` | number | GPS coordinates |
| `X_MainPhoto` | string | Main photo URL |

### Extension Fields

Fields prefixed with `X_` are Qobrix extensions (e.g., `X_SeaView`, `X_PrivateSwimmingPool`).

---

## Sync Client Examples

For complete implementations with OAuth, pagination, retry logic, and progress tracking:

| File | Language | Use Case |
|------|----------|----------|
| [`sync-client-example.ts`](sync-client-example.ts) | TypeScript | React apps, Node.js |
| [`sync-client-example.js`](sync-client-example.js) | Vanilla JS | Browser, Node.js 18+ |

### Quick Start

```javascript
const client = new MLSSyncClient({
  baseUrl: 'https://your-server.com/reso',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
});

// Sync all active properties
const properties = await client.syncAllParallel({
  filter: "StandardStatus eq 'Active'",
});
```

### Progress Tracking

Both clients support an `onProgress` callback for UI updates:

```javascript
await client.syncAllParallel({
  onProgress: (p) => {
    console.log(`${p.percent}% (${p.fetched}/${p.total}) - ${p.propertiesPerSecond}/s`);
  },
});
```

**Progress object fields:**

| Field | Description |
|-------|-------------|
| `percent` | Completion 0-100 |
| `fetched` | Items fetched |
| `total` | Total items |
| `propertiesPerSecond` | Current speed |
| `estimatedRemainingMs` | ETA in milliseconds |
| `elapsedMs` | Time elapsed |

### Progress Bar Examples

See the usage examples section in each client file:

- **Vanilla JS progress bar** → [`sync-client-example.js`](sync-client-example.js) (Section 2)
- **React component** → [`sync-client-example.ts`](sync-client-example.ts) (Section 3)
- **React hook** → [`sync-client-example.ts`](sync-client-example.ts) (Section 4)
- **Two-phase sync (properties + media)** → Both files (Section 5)
- **Animated CSS progress bar** → Both files (Section 6)

### Incremental Sync

Only fetch changes since last sync:

```javascript
const lastSync = new Date('2024-12-01T00:00:00Z');
const updates = await client.syncModifiedSince(lastSync);
```

### Media (Photos)

```javascript
// Get photos for single property
const photos = await client.getPropertyMedia('QOBRIX_123');

// Bulk fetch for multiple properties
const mediaMap = await client.getMediaForProperties(['KEY1', 'KEY2', 'KEY3']);

// Full sync with media attached
const propertiesWithMedia = await client.syncAllWithMedia();
```

**Tip:** Use `X_MainPhoto` for listing pages - no extra request needed!

### Performance

| Mode | Throughput |
|------|------------|
| Sequential | ~600 props/s |
| Parallel (3) | ~1,200 props/s |

**Tips:**
- Use `$top=1000` for max batch size
- Use `$select` to reduce payload
- Use parallel mode with `maxConcurrent: 3`

---

## TypeScript Types

Available in [`sync-client-example.ts`](sync-client-example.ts):

- `Property` - Property listing
- `Media` - Photo/document
- `SyncProgress` - Progress callback data
- `SyncOptions` - Sync configuration
- `ODataResponse<T>` - API response wrapper

---

## Environment Variables

```env
VITE_RESO_API_URL=https://your-server.com/reso
VITE_RESO_CLIENT_ID=your-client-id
VITE_RESO_CLIENT_SECRET=your-client-secret
```

---

## Error Handling

| Status | Description |
|--------|-------------|
| 401 | Token missing or expired |
| 429 | Rate limited (retry after) |
| 500 | Server error (retry with backoff) |

The sync clients include automatic retry with exponential backoff.

---

## RESO Compliance

This API implements:
- **OAuth 2.0 Client Credentials** (RESO Web API Core)
- **OData 4.0** query syntax
- **RESO Data Dictionary 2.0** field names
