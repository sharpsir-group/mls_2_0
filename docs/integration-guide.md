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

---

## Multi-Tenant Data Sources (NEW)

The API aggregates data from multiple sources. Your client is configured for specific office keys.

### Data Sources

| Office Key | Source | Data Type |
|------------|--------|-----------|
| `CSIR` | Qobrix CRM | Managed listings |
| `HSIR` | Dash/Sotheby's | Luxury listings |

### Filter by Data Source

```bash
# Qobrix only
$filter=OriginatingSystemOfficeKey eq 'CSIR'

# Dash/Sotheby's only
$filter=OriginatingSystemOfficeKey eq 'HSIR'

# Combined (default if client has access to both)
# No filter needed - returns all data client has access to

# Active Dash properties
$filter=StandardStatus eq 'Active' and OriginatingSystemOfficeKey eq 'HSIR'
```

### Identify Source in Results

```javascript
properties.forEach(p => {
  if (p.X_DataSource === 'dash_sothebys') {
    // Sotheby's listing - has YearBuilt, View, Flooring, etc.
    console.log(`${p.ListingKey}: ${p.View}, Built: ${p.YearBuilt}`);
  } else {
    // Qobrix listing - has DevelopmentStatus
    console.log(`${p.ListingKey}: ${p.DevelopmentStatus || 'Resale'}`);
  }
});
```

---

## Building Property Listing UI

### Recommended Fields for List View

```javascript
const listViewFields = [
  'ListingKey',           // Unique ID
  'ListPrice',            // Price
  'City',                 // Location
  'BedroomsTotal',        // Beds
  'BathroomsTotalInteger',// Baths
  'LivingArea',           // Size
  'StandardStatus',       // Status badge
  'X_DataSource',         // Source indicator
];

// Fetch with select for performance
const url = `/odata/Property?$select=${listViewFields.join(',')}&$top=20`;
```

### Getting Main Photos (Batch)

```javascript
// After fetching properties, batch-fetch main photos
const listingKeys = properties.map(p => p.ListingKey);
const photoMap = await client.getMainPhotos(listingKeys);

// Attach to properties
properties.forEach(p => {
  p.mainPhoto = photoMap.get(p.ListingKey) || '/placeholder.jpg';
});
```

### Property Card Component (React)

```jsx
function PropertyCard({ property }) {
  const formatPrice = (price, currency) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'EUR',
      maximumFractionDigits: 0,
    }).format(price);
  };

  return (
    <div className="property-card">
      <img src={property.mainPhoto} alt={property.City} />
      
      <div className="property-info">
        <h3>{formatPrice(property.ListPrice, property.X_CurrencyCode)}</h3>
        <p>{property.City}, {property.Country}</p>
        
        <div className="property-stats">
          {property.BedroomsTotal && <span>{property.BedroomsTotal} beds</span>}
          {property.BathroomsTotalInteger && <span>{property.BathroomsTotalInteger} baths</span>}
          {property.LivingArea && <span>{property.LivingArea} m²</span>}
        </div>
        
        {/* Source indicator */}
        {property.X_DataSource === 'dash_sothebys' && (
          <span className="badge luxury">Sotheby's</span>
        )}
        
        {/* Status badge */}
        <span className={`badge ${property.StandardStatus.toLowerCase()}`}>
          {property.StandardStatus}
        </span>
      </div>
    </div>
  );
}
```

---

## Building Property Detail UI

### Full Field Selection

```javascript
const detailFields = [
  // Core
  'ListingKey', 'ListingId', 'ListPrice', 'StandardStatus',
  'PropertyType', 'PropertySubType',
  
  // Location
  'UnparsedAddress', 'City', 'StateOrProvince', 'PostalCode', 
  'Country', 'Latitude', 'Longitude',
  
  // Details
  'BedroomsTotal', 'BathroomsTotalInteger', 'BathroomsHalf',
  'LivingArea', 'LotSizeSquareFeet', 'YearBuilt',
  
  // Features (Dash-rich)
  'View', 'Flooring', 'Heating', 'Cooling', 'PoolFeatures',
  'FireplaceYN', 'ParkingFeatures', 'Appliances',
  
  // Agent
  'ListAgentFirstName', 'ListAgentLastName', 'ListAgentEmail',
  'ListOfficeName',
  
  // Description
  'PublicRemarks',
  
  // Extensions
  'X_ListingUrl', 'X_CurrencyCode', 'X_DataSource',
];
```

### Feature Display Component

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
  ].filter(f => f.value); // Only show non-null
  
  if (features.length === 0) return null;
  
  return (
    <div className="property-features">
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

### Photo Gallery

```javascript
// Fetch all photos for detail page
const photos = await client.getPropertyMedia(listingKey);

// photos are sorted by Order (first = main photo)
// Dash photos include dimensions: ImageWidth, ImageHeight
```

```jsx
function PhotoGallery({ photos }) {
  const [activeIndex, setActiveIndex] = useState(0);
  
  return (
    <div className="gallery">
      <img 
        src={photos[activeIndex]?.MediaURL}
        style={{
          // Use dimensions if available (Dash)
          aspectRatio: photos[activeIndex]?.ImageWidth && photos[activeIndex]?.ImageHeight
            ? `${photos[activeIndex].ImageWidth} / ${photos[activeIndex].ImageHeight}`
            : '16 / 9'
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

---

## Search & Filter UI

### Common Filter Combinations

```javascript
const filters = {
  // Status
  active: "StandardStatus eq 'Active'",
  pending: "StandardStatus eq 'Pending'",
  sold: "StandardStatus eq 'Closed'",
  
  // Property type
  residential: "PropertyClass eq 'RESI'",
  rental: "PropertyClass eq 'RLSE'",
  commercial: "PropertyClass eq 'COMS'",
  land: "PropertyClass eq 'LAND'",
  
  // Price ranges
  under500k: "ListPrice lt 500000",
  '500k-1m': "ListPrice ge 500000 and ListPrice lt 1000000",
  '1m-5m': "ListPrice ge 1000000 and ListPrice lt 5000000",
  over5m: "ListPrice ge 5000000",
  
  // Bedrooms
  '1bed': "BedroomsTotal eq 1",
  '2bed': "BedroomsTotal eq 2",
  '3bed': "BedroomsTotal eq 3",
  '4plus': "BedroomsTotal ge 4",
  
  // Features (Dash only)
  withPool: "PoolFeatures ne null",
  withView: "View ne null",
  
  // Source
  qobrix: "OriginatingSystemOfficeKey eq 'CSIR'",
  sothebys: "OriginatingSystemOfficeKey eq 'HSIR'",
};

// Combine filters
const buildFilter = (selected) => {
  return Object.entries(selected)
    .filter(([_, isSelected]) => isSelected)
    .map(([key]) => filters[key])
    .join(' and ');
};
```

### Search by City

```bash
# Exact match
$filter=City eq 'Budapest'

# Contains (partial match)
$filter=contains(City, 'Miami')

# Multiple cities
$filter=City in ('Miami', 'Fort Lauderdale', 'West Palm Beach')
```

### Sorting Options

```javascript
const sortOptions = {
  'Price: Low to High': '$orderby=ListPrice asc',
  'Price: High to Low': '$orderby=ListPrice desc',
  'Newest First': '$orderby=ModificationTimestamp desc',
  'Bedrooms': '$orderby=BedroomsTotal desc',
  'Size': '$orderby=LivingArea desc',
};
```

---

## Agent/Office Display

### Agent Card (Dash properties)

```jsx
function AgentCard({ property }) {
  // Only Dash properties have full agent details
  if (property.X_DataSource !== 'dash_sothebys') {
    return null;
  }
  
  return (
    <div className="agent-card">
      {property.X_ListAgentPhotoUrl && (
        <img src={property.X_ListAgentPhotoUrl} alt="Agent" />
      )}
      <div>
        <h4>{property.ListAgentFirstName} {property.ListAgentLastName}</h4>
        <p>{property.ListOfficeName}</p>
        {property.ListAgentEmail && (
          <a href={`mailto:${property.ListAgentEmail}`}>Contact Agent</a>
        )}
      </div>
    </div>
  );
}
```

---

## External Links

### Link to Original Listing

```jsx
function OriginalListingLink({ property }) {
  // Dash properties have direct listing URL
  if (property.X_ListingUrl) {
    return (
      <a href={property.X_ListingUrl} target="_blank" rel="noopener">
        View on Sotheby's →
      </a>
    );
  }
  return null;
}
```

---

## Responsive Image Loading

### Use ImageWidth/ImageHeight for Layout

```jsx
// Dash photos include dimensions - use for better CLS
function ResponsiveImage({ photo, className }) {
  const aspectRatio = photo.ImageWidth && photo.ImageHeight
    ? photo.ImageWidth / photo.ImageHeight
    : 16/9;
    
  return (
    <div 
      className={className}
      style={{ aspectRatio }}
    >
      <img 
        src={photo.MediaURL}
        loading="lazy"
        width={photo.ImageWidth}
        height={photo.ImageHeight}
      />
    </div>
  );
}
```

---

## Caching Recommendations

| Data | Cache Duration | Strategy |
|------|----------------|----------|
| Property list | 5 minutes | Stale-while-revalidate |
| Property detail | 15 minutes | Cache with revalidation |
| Media/Photos | 1 hour | Long cache, CDN |
| Main photos map | 5 minutes | Memory cache |

### Incremental Sync

```javascript
// Only fetch changes since last sync
const lastSync = localStorage.getItem('lastSync');
const since = lastSync ? new Date(lastSync) : new Date(0);

const updates = await client.syncModifiedSince(since);
localStorage.setItem('lastSync', new Date().toISOString());

// Merge updates into local cache
updates.forEach(p => {
  cache.set(p.ListingKey, p);
});
```

