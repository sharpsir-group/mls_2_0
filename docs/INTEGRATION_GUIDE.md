# RESO Web API Integration Guide

This guide explains how to connect your frontend application to the RESO Web API.

## Connecting from Lovable (Real Estate Site)

To connect your Lovable real estate project to this RESO Web API:

### 1. Set API Base URL

In your Lovable project, create an environment variable or config:

```typescript
// src/config/api.ts
export const RESO_API_BASE = 'https://your-server.com:3900';
// Or for local development: 'http://localhost:3900'
```

### 2. Create API Service

```typescript
// src/services/resoApi.ts
const API_BASE = import.meta.env.VITE_RESO_API_URL || 'http://localhost:3900';

export interface Property {
  ListingKey: string;
  ListPrice: number;
  City: string;
  StandardStatus: string;
  BedroomsTotal: number;
  BathroomsTotalInteger: number;
  LivingArea: number;
  Latitude: number;
  Longitude: number;
  // ... more fields
}

export interface ODataResponse<T> {
  '@odata.context': string;
  '@odata.count'?: number;
  '@odata.nextLink'?: string;
  value: T[];
}

// Fetch properties with OData query
export async function fetchProperties(params: {
  filter?: string;
  select?: string;
  orderby?: string;
  top?: number;
  skip?: number;
  count?: boolean;
}): Promise<ODataResponse<Property>> {
  const searchParams = new URLSearchParams();
  
  if (params.filter) searchParams.set('\$filter', params.filter);
  if (params.select) searchParams.set('\$select', params.select);
  if (params.orderby) searchParams.set('\$orderby', params.orderby);
  if (params.top) searchParams.set('\$top', params.top.toString());
  if (params.skip) searchParams.set('\$skip', params.skip.toString());
  if (params.count) searchParams.set('\$count', 'true');

  const response = await fetch(\`\${API_BASE}/odata/Property?\${searchParams}\`);
  if (!response.ok) throw new Error('Failed to fetch properties');
  return response.json();
}

// Get single property by key
export async function getProperty(listingKey: string): Promise<Property> {
  const response = await fetch(\`\${API_BASE}/odata/Property('\${listingKey}')\`);
  if (!response.ok) throw new Error('Property not found');
  return response.json();
}

// Get media for a property
export async function getPropertyMedia(listingKey: string) {
  const response = await fetch(
    \`\${API_BASE}/odata/Media?\$filter=ResourceRecordKey eq '\${listingKey}'&\$orderby=Order\`
  );
  if (!response.ok) throw new Error('Failed to fetch media');
  return response.json();
}
```

### 3. React Query Integration (Recommended)

```typescript
// src/hooks/useProperties.ts
import { useQuery } from '@tanstack/react-query';
import { fetchProperties, getProperty, getPropertyMedia } from '@/services/resoApi';

// Hook for property list with filters
export function useProperties(filters: {
  status?: string;
  city?: string;
  minPrice?: number;
  maxPrice?: number;
  bedrooms?: number;
  page?: number;
  pageSize?: number;
}) {
  const buildFilter = () => {
    const conditions: string[] = [];
    if (filters.status) conditions.push(\`StandardStatus eq '\${filters.status}'\`);
    if (filters.city) conditions.push(\`City eq '\${filters.city}'\`);
    if (filters.minPrice) conditions.push(\`ListPrice ge \${filters.minPrice}\`);
    if (filters.maxPrice) conditions.push(\`ListPrice le \${filters.maxPrice}\`);
    if (filters.bedrooms) conditions.push(\`BedroomsTotal ge \${filters.bedrooms}\`);
    return conditions.join(' and ') || undefined;
  };

  return useQuery({
    queryKey: ['properties', filters],
    queryFn: () => fetchProperties({
      filter: buildFilter(),
      select: 'ListingKey,ListPrice,City,StandardStatus,BedroomsTotal,BathroomsTotalInteger,LivingArea,X_MainPhoto',
      orderby: 'ListPrice desc',
      top: filters.pageSize || 20,
      skip: ((filters.page || 1) - 1) * (filters.pageSize || 20),
      count: true,
    }),
  });
}

// Hook for single property
export function useProperty(listingKey: string) {
  return useQuery({
    queryKey: ['property', listingKey],
    queryFn: () => getProperty(listingKey),
    enabled: !!listingKey,
  });
}

// Hook for property media
export function usePropertyMedia(listingKey: string) {
  return useQuery({
    queryKey: ['propertyMedia', listingKey],
    queryFn: () => getPropertyMedia(listingKey),
    enabled: !!listingKey,
  });
}
```

### 4. Example Component

```tsx
// src/components/PropertyGrid.tsx
import { useProperties } from '@/hooks/useProperties';

export function PropertyGrid() {
  const { data, isLoading, error } = useProperties({
    status: 'Active',
    pageSize: 12,
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading properties</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {data?.value.map((property) => (
        <div key={property.ListingKey} className="rounded-lg shadow-lg overflow-hidden">
          <img 
            src={property.X_MainPhoto || '/placeholder.jpg'} 
            alt={property.City}
            className="w-full h-48 object-cover"
          />
          <div className="p-4">
            <h3 className="text-xl font-bold">\${property.ListPrice?.toLocaleString()}</h3>
            <p className="text-gray-600">{property.City}</p>
            <div className="flex gap-4 mt-2 text-sm">
              <span>{property.BedroomsTotal} beds</span>
              <span>{property.BathroomsTotalInteger} baths</span>
              <span>{property.LivingArea?.toLocaleString()} sqft</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 5. Environment Variables in Lovable

Add to your Lovable project's environment:

```
VITE_RESO_API_URL=https://your-server.com:3900
```

### 6. CORS Configuration

The API allows all origins by default. For production, update \`api/config.py\`:

```python
cors_origins: list = ["https://your-lovable-app.lovable.app"]
```

## Common OData Queries for Real Estate

```typescript
// Active listings under \$500k
\$filter=StandardStatus eq 'Active' and ListPrice lt 500000

// Properties with 3+ bedrooms in Miami
\$filter=BedroomsTotal ge 3 and City eq 'Miami'

// Recently modified listings
\$orderby=ModificationTimestamp desc&\$top=10

// Search by city (contains)
\$filter=contains(City,'Beach')

// Luxury properties
\$filter=ListPrice gt 1000000&\$orderby=ListPrice desc
```

## Quick Integration Examples

### Vanilla JavaScript

```javascript
// Fetch active properties
fetch('https://your-server:3900/odata/Property?\$filter=StandardStatus eq \'Active\'&\$top=20')
  .then(res => res.json())
  .then(data => console.log(data.value));
```

### Next.js Server Component

```tsx
// app/properties/page.tsx
async function getProperties() {
  const res = await fetch('https://your-server:3900/odata/Property?\$top=20', {
    next: { revalidate: 60 } // Cache for 60 seconds
  });
  return res.json();
}

export default async function PropertiesPage() {
  const data = await getProperties();
  
  return (
    <div>
      {data.value.map(property => (
        <div key={property.ListingKey}>
          <h2>{property.City}</h2>
          <p>\${property.ListPrice?.toLocaleString()}</p>
        </div>
      ))}
    </div>
  );
}
```

## API Response Format

All endpoints return OData-formatted responses:

```json
{
  "@odata.context": "http://localhost:3900/\$metadata#Property",
  "@odata.count": 14034,
  "value": [
    {
      "ListingKey": "QOBRIX_abc123",
      "ListPrice": 750000,
      "City": "Miami",
      "StandardStatus": "Active",
      "BedroomsTotal": 3,
      "BathroomsTotalInteger": 2
    }
  ],
  "@odata.nextLink": "http://localhost:3900/odata/Property?\$skip=20&\$top=20"
}
```
