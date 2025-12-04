# Integration Guide

Connect your real estate website to the RESO Web API.

## API Base URL

```
https://your-server.com/reso
```

## Authentication

If API key authentication is enabled, include your key in requests:

**Option 1: Header (Recommended)**
```javascript
const response = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'X-API-Key': 'your-api-key' }
});
```

**Option 2: Query Parameter**
```javascript
const response = await fetch(`${API_URL}/odata/Property?api_key=your-api-key`);
```

**Error Responses:**
| Status | Message | Cause |
|--------|---------|-------|
| 403 | API key required | No key provided |
| 403 | Invalid API key | Key not recognized |

## Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /odata/Property` | Property listings |
| `GET /odata/Property('{key}')` | Single property |
| `GET /odata/Media` | Property photos |
| `GET /odata/Member` | Agents |
| `GET /odata/Office` | Offices/agencies |
| `GET /odata/Contacts` | Contacts |
| `GET /odata/ShowingAppointment` | Showing appointments |
| `GET /docs` | Swagger UI |

## Quick Start

### Fetch Properties

```javascript
const API_URL = 'https://your-server.com/reso';
const API_KEY = 'your-api-key'; // Optional if auth disabled

// Get active listings
const response = await fetch(
  `${API_URL}/odata/Property?$filter=StandardStatus eq 'Active'&$top=20`,
  { headers: { 'X-API-Key': API_KEY } }
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

## Property Fields

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `ListingKey` | string | Unique ID |
| `ListPrice` | number | Listing price |
| `ListPriceCurrencyCode` | string | Currency (e.g., EUR, USD) |
| `StandardStatus` | string | Active, Pending, Closed, Withdrawn |
| `PropertyType` | string | Apartment, House, Land, etc. |
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
// Get photos for a property
const listingKey = 'QOBRIX_abc123';
const response = await fetch(
  `https://your-server.com/reso/odata/Media?$filter=ResourceRecordKey eq '${listingKey}'&$orderby=Order`
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
```

## React Example

```tsx
import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_RESO_API_URL || 'https://your-server.com/reso';
const API_KEY = import.meta.env.VITE_RESO_API_KEY;

function PropertyList() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/odata/Property?$filter=StandardStatus eq 'Active'&$top=20`, {
      headers: API_KEY ? { 'X-API-Key': API_KEY } : {}
    })
      .then(res => res.json())
      .then(data => {
        setProperties(data.value);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      {properties.map(property => (
        <div key={property.ListingKey} className="border rounded p-4">
          <img src={property.X_MainPhoto} alt="" className="w-full h-48 object-cover" />
          <h3>${property.ListPrice?.toLocaleString()}</h3>
          <p>{property.City}</p>
          <p>{property.BedroomsTotal} bed | {property.BathroomsTotalInteger} bath</p>
        </div>
      ))}
    </div>
  );
}
```

## Environment Variables

In your frontend project:

```env
VITE_RESO_API_URL=https://your-server.com/reso
VITE_RESO_API_KEY=your-api-key
```

Then use:

```javascript
const API_URL = import.meta.env.VITE_RESO_API_URL;
const API_KEY = import.meta.env.VITE_RESO_API_KEY;

const fetchProperties = async () => {
  const response = await fetch(`${API_URL}/odata/Property`, {
    headers: { 'X-API-Key': API_KEY }
  });
  return response.json();
};
```

## Error Handling

```javascript
try {
  const response = await fetch(`${API_URL}/odata/Property`, {
    headers: { 'X-API-Key': API_KEY }
  });
  
  if (!response.ok) {
    const error = await response.json();
    
    if (response.status === 403) {
      // Authentication error
      console.error('Auth error:', error.error.message);
    } else {
      console.error('API error:', error.error.message);
    }
    return;
  }
  
  const data = await response.json();
} catch (e) {
  console.error('Network error:', e);
}
```
