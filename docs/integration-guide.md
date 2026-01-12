# RESO Web API - Integration Guide

Connect your real estate application to the RESO Web API.

## Quick Start

```javascript
const API_URL = 'https://your-server.com/reso';

// 1. Get OAuth token
const tokenResponse = await fetch(`${API_URL}/oauth/token`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}`
});
const { access_token } = await tokenResponse.json();

// 2. Fetch properties
const response = await fetch(`${API_URL}/odata/Property?$top=20`, {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const data = await response.json();
console.log(data.value); // Array of properties
```

---

## Authentication

OAuth 2.0 Client Credentials flow.

### Get Access Token

```bash
curl -X POST https://your-server.com/reso/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
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

Include in all API requests:
```
Authorization: Bearer {access_token}
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /oauth/token` | Get OAuth access token |
| `GET /odata/Property` | Property listings |
| `GET /odata/Property('{ListingKey}')` | Single property |
| `GET /odata/Media` | Property photos |
| `GET /odata/Member` | Agents |
| `GET /odata/Office` | Offices |
| `GET /odata/Contacts` | Contacts |
| `GET /odata/ShowingAppointment` | Showings |
| `GET /docs` | Swagger UI |

---

## OData Query Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `$filter` | `StandardStatus eq 'Active'` | Filter results |
| `$select` | `ListingKey,ListPrice,City` | Select fields |
| `$orderby` | `ListPrice desc` | Sort results |
| `$top` | `20` (max: 1000) | Limit results |
| `$skip` | `40` | Pagination offset |
| `$count` | `true` | Include total count |

---

## Data Sources

Your client may have access to one or both data sources:

| Office Key | Source | Description |
|------------|--------|-------------|
| `CSIR` | Qobrix | Managed listings |
| `HSIR` | Dash/Sotheby's | Luxury listings |

### Filter by Source

```bash
# All data (default)
/odata/Property

# Qobrix only
/odata/Property?$filter=OriginatingSystemOfficeKey eq 'CSIR'

# Dash/Sotheby's only
/odata/Property?$filter=OriginatingSystemOfficeKey eq 'HSIR'
```

### Identify Source in Results

```javascript
properties.forEach(p => {
  console.log(`${p.ListingKey}: ${p.X_DataSource}`);
  // QOBRIX_abc123: qobrix
  // DASH_xyz789: dash_sothebys
});
```

---

## Common Filters

### Status

```bash
# Active listings
$filter=StandardStatus eq 'Active'

# Pending
$filter=StandardStatus eq 'Pending'

# Sold/Closed
$filter=StandardStatus eq 'Closed'
```

### Property Type

```bash
# Residential for sale
$filter=PropertyClass eq 'RESI'

# Rentals
$filter=PropertyClass eq 'RLSE'

# Commercial
$filter=PropertyClass eq 'COMS'

# Land
$filter=PropertyClass eq 'LAND'
```

### Price Range

```bash
# Under 500K
$filter=ListPrice lt 500000

# 500K - 1M
$filter=ListPrice ge 500000 and ListPrice lt 1000000

# Over 1M
$filter=ListPrice ge 1000000
```

### Bedrooms

```bash
# 3+ bedrooms
$filter=BedroomsTotal ge 3

# Exactly 2 bedrooms
$filter=BedroomsTotal eq 2
```

### Location

```bash
# Specific city
$filter=City eq 'Budapest'

# City contains
$filter=contains(City, 'Miami')

# Multiple cities
$filter=City in ('Miami', 'Fort Lauderdale')

# By country
$filter=Country eq 'HU'
```

### Features (Dash properties)

```bash
# Has view
$filter=View ne null

# Has pool
$filter=PoolFeatures ne null
```

### Combined Filters

```bash
$filter=StandardStatus eq 'Active' and PropertyClass eq 'RESI' and ListPrice lt 1000000 and BedroomsTotal ge 2
```

---

## Sorting

```bash
# Price: Low to High
$orderby=ListPrice asc

# Price: High to Low
$orderby=ListPrice desc

# Newest first
$orderby=ModificationTimestamp desc

# By bedrooms
$orderby=BedroomsTotal desc
```

---

## Pagination

```bash
# First 20 results
$top=20

# Next 20 results
$top=20&$skip=20

# Get total count
$count=true
```

**Response with count:**
```json
{
  "@odata.count": 1500,
  "value": [...]
}
```

---

## Building a Property List

### Recommended Fields

```javascript
const listFields = [
  'ListingKey',
  'ListPrice',
  'City',
  'Country',
  'BedroomsTotal',
  'BathroomsTotalInteger',
  'LivingArea',
  'StandardStatus',
  'PropertyClass',
  'X_DataSource'
].join(',');

const url = `/odata/Property?$select=${listFields}&$filter=StandardStatus eq 'Active'&$top=20`;
```

### Get Main Photos

```javascript
// After fetching properties, get main photos
const listingKeys = properties.map(p => p.ListingKey);
const keyList = listingKeys.map(k => `'${k}'`).join(',');

const mediaUrl = `/odata/Media?$filter=ResourceRecordKey in (${keyList}) and Order eq 0&$select=ResourceRecordKey,MediaURL&$top=1000`;
const mediaResponse = await fetch(mediaUrl, { headers });
const mediaData = await mediaResponse.json();

// Create lookup map
const photoMap = new Map();
mediaData.value.forEach(m => photoMap.set(m.ResourceRecordKey, m.MediaURL));

// Attach to properties
properties.forEach(p => {
  p.mainPhoto = photoMap.get(p.ListingKey);
});
```

### Property Card Component

```jsx
function PropertyCard({ property }) {
  return (
    <div className="property-card">
      <img src={property.mainPhoto || '/placeholder.jpg'} alt="" />
      <div className="info">
        <h3>${property.ListPrice?.toLocaleString()}</h3>
        <p>{property.City}, {property.Country}</p>
        <p>{property.BedroomsTotal} bed • {property.BathroomsTotalInteger} bath • {property.LivingArea} m²</p>
        <span className={`status ${property.StandardStatus.toLowerCase()}`}>
          {property.StandardStatus}
        </span>
      </div>
    </div>
  );
}
```

---

## Building a Property Detail Page

### Full Field Selection

```javascript
const detailFields = [
  // Core
  'ListingKey', 'ListingId', 'ListPrice', 'StandardStatus', 'PropertyType',
  
  // Location
  'UnparsedAddress', 'City', 'StateOrProvince', 'PostalCode', 'Country',
  'Latitude', 'Longitude',
  
  // Details
  'BedroomsTotal', 'BathroomsTotalInteger', 'BathroomsHalf',
  'LivingArea', 'LotSizeSquareFeet', 'YearBuilt',
  
  // Features
  'View', 'Flooring', 'Heating', 'Cooling', 'PoolFeatures',
  'FireplaceYN', 'ParkingFeatures', 'Appliances',
  
  // Agent
  'ListAgentFirstName', 'ListAgentLastName', 'ListAgentEmail', 'ListOfficeName',
  
  // Description
  'PublicRemarks',
  
  // Extensions
  'X_ListingUrl', 'X_DataSource', 'X_CurrencyCode'
].join(',');

const url = `/odata/Property('${listingKey}')?$select=${detailFields}`;
```

### Get All Photos

```javascript
const mediaUrl = `/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`;
const response = await fetch(mediaUrl, { headers });
const { value: photos } = await response.json();

// First photo (Order=0) is main photo
// photos are sorted by Order
```

### Photo Gallery Component

```jsx
function PhotoGallery({ photos }) {
  const [activeIndex, setActiveIndex] = useState(0);
  
  return (
    <div className="gallery">
      <img 
        src={photos[activeIndex]?.MediaURL}
        alt=""
        style={{
          aspectRatio: photos[activeIndex]?.ImageWidth && photos[activeIndex]?.ImageHeight
            ? `${photos[activeIndex].ImageWidth}/${photos[activeIndex].ImageHeight}`
            : '16/9'
        }}
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
  );
}
```

### Feature Display

```jsx
function PropertyFeatures({ property }) {
  const features = [
    { label: 'View', value: property.View },
    { label: 'Flooring', value: property.Flooring },
    { label: 'Heating', value: property.Heating },
    { label: 'Cooling', value: property.Cooling },
    { label: 'Pool', value: property.PoolFeatures },
    { label: 'Parking', value: property.ParkingFeatures },
    { label: 'Appliances', value: property.Appliances },
  ].filter(f => f.value);
  
  if (features.length === 0) return null;
  
  return (
    <div className="features">
      <h3>Features</h3>
      <dl>
        {features.map(f => (
          <div key={f.label}>
            <dt>{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
```

### Agent Card (Dash properties)

```jsx
function AgentInfo({ property }) {
  if (!property.ListAgentFirstName) return null;
  
  return (
    <div className="agent-card">
      <h4>{property.ListAgentFirstName} {property.ListAgentLastName}</h4>
      <p>{property.ListOfficeName}</p>
      {property.ListAgentEmail && (
        <a href={`mailto:${property.ListAgentEmail}`}>Contact Agent</a>
      )}
    </div>
  );
}
```

---

## Incremental Sync

Only fetch changes since last sync:

```javascript
const lastSync = localStorage.getItem('lastSync') || '2024-01-01T00:00:00Z';

const url = `/odata/Property?$filter=ModificationTimestamp gt ${lastSync}&$orderby=ModificationTimestamp`;

const response = await fetch(url, { headers });
const { value: updates } = await response.json();

// Update your local cache
updates.forEach(p => cache.set(p.ListingKey, p));

// Save sync timestamp
localStorage.setItem('lastSync', new Date().toISOString());
```

---

## Error Handling

| Status | Description | Action |
|--------|-------------|--------|
| 401 | Token expired | Get new token |
| 403 | Access denied | Check client permissions |
| 429 | Rate limited | Retry after delay |
| 500 | Server error | Retry with backoff |

### Retry Logic

```javascript
async function fetchWithRetry(url, options, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.status === 401) {
        await refreshToken();
        continue;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
}
```

---

## Performance Tips

1. **Use `$select`** - Only request fields you need
2. **Use `$top=1000`** - Maximum batch size
3. **Batch photo requests** - Use `in (...)` filter for multiple properties
4. **Cache aggressively** - Properties change infrequently
5. **Use incremental sync** - Only fetch changes after initial load

---

## Sync Client Libraries

Full-featured sync clients with progress tracking:

- **TypeScript:** [`sync-client-example.ts`](sync-client-example.ts)
- **JavaScript:** [`sync-client-example.js`](sync-client-example.js)

Features:
- OAuth token auto-refresh
- Parallel requests
- Progress callbacks
- Retry logic
- React hooks

---

## RESO Compliance

This API implements:
- **OAuth 2.0 Client Credentials** (RESO Web API Core)
- **OData 4.0** query syntax
- **RESO Data Dictionary 2.0** field names

See [`mapping.md`](mapping.md) for complete field reference.
