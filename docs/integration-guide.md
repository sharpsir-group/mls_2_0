# Integration Guide

Connect your real estate website to the RESO Web API.

## API Base URL

```
https://your-server.com/reso
```

## Authentication

The API supports two authentication methods:

### 1. OAuth 2.0 (RESO Compliant - Recommended)

Use OAuth 2.0 Client Credentials flow for RESO-compliant authentication.

**Step 1: Get an Access Token**

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

**Step 2: Use Bearer Token**

```javascript
const response = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
```

**JavaScript Example:**

```javascript
const API_URL = 'https://your-server.com/reso';
const CLIENT_ID = 'your-client-id';
const CLIENT_SECRET = 'your-client-secret';

// Get access token
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

// Use token
const token = await getAccessToken();
const properties = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());
```

### 2. API Key (Legacy)

Simple API key authentication for backward compatibility.

**Option A: Header (Recommended)**
```javascript
const response = await fetch(`${API_URL}/odata/Property`, {
  headers: { 'X-API-Key': 'your-api-key' }
});
```

**Option B: Query Parameter**
```javascript
const response = await fetch(`${API_URL}/odata/Property?api_key=your-api-key`);
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 401 | Unauthorized | No credentials provided |
| 401 | InvalidToken | Bearer token expired or invalid |
| 403 | Forbidden | Invalid API key |

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

### Fetch Properties

```javascript
const API_URL = 'https://your-server.com/reso';

// Using Bearer token (recommended)
const token = await getAccessToken();
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

## React Example with OAuth

```tsx
import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_RESO_API_URL || 'https://your-server.com/reso';
const CLIENT_ID = import.meta.env.VITE_RESO_CLIENT_ID;
const CLIENT_SECRET = import.meta.env.VITE_RESO_CLIENT_SECRET;

// Token management hook
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

In your frontend project:

```env
VITE_RESO_API_URL=https://your-server.com/reso
# OAuth (recommended)
VITE_RESO_CLIENT_ID=your-client-id
VITE_RESO_CLIENT_SECRET=your-client-secret
# API Key (legacy)
VITE_RESO_API_KEY=your-api-key
```

## Error Handling

```javascript
async function fetchWithAuth(url, token) {
  try {
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 401) {
        // Token expired - refresh and retry
        const newToken = await getAccessToken();
        return fetchWithAuth(url, newToken);
      }
      
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

For full RESO certification, use OAuth 2.0 authentication.
