# RESO Web API — OData 4.0 Endpoint Reference

> Source: `/home/bitnami/mls_2_0/api/` (FastAPI application)
> Integration guide: `/home/bitnami/mls_2_0/docs/integration-guide.md`
>
> **For Lovable**: New Matrix Apps should read/write to Supabase CDL directly
> (see [app-template.md](../platform/app-template.md)). Use the RESO Web API only when:
> - Building 3rd-party integrations that need OData compatibility
> - Feeding data to external portals or syndication partners
> - A specific feature requires the OData query language

## API Overview

| Setting | Value |
|---------|-------|
| Base URL | `https://{host}:3900/reso` |
| Protocol | OData 4.0 (JSON) |
| Auth | OAuth 2.0 Client Credentials |
| Multi-tenant | Office-based filtering via `OriginatingSystemOfficeKey` |
| Source data | Databricks `mls2.reso_gold` tables |

## Authentication

### OAuth 2.0 Client Credentials Flow

```typescript
// Step 1: Get access token
const tokenResponse = await fetch('https://{host}:3900/reso/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'client_credentials',
    client_id: 'YOUR_CLIENT_ID',
    client_secret: 'YOUR_CLIENT_SECRET',
  }),
});
const { access_token } = await tokenResponse.json();

// Step 2: Use token in requests
const response = await fetch('https://{host}:3900/reso/odata/Property', {
  headers: { 'Authorization': `Bearer ${access_token}` },
});
```

### Office-Based Access Control

Each OAuth client is configured with allowed offices:
- Client with `offices: ["SHARPSIR-CY-001"]` → sees only Cyprus data
- Client with `offices: ["SHARPSIR-CY-001", "SHARPSIR-HU-001"]` → sees Cyprus + Hungary
- Client with `offices: []` (empty) → admin access to all offices

The API automatically filters all queries by `OriginatingSystemOfficeKey` based on the JWT's `offices` claim.

## Endpoints

### Service Metadata

| Method | Path | Returns |
|--------|------|---------|
| `GET /odata` | Service document | Available resources |
| `GET /odata/$metadata` | Metadata document (XML) | Resource schemas |
| `GET /odata/{Resource}/$count` | Record count | Integer |

### RESO Resources

| Resource | List | Single | Key Field |
|----------|------|--------|-----------|
| Property | `GET /odata/Property` | `GET /odata/Property('{ListingKey}')` | `ListingKey` |
| Member | `GET /odata/Member` | `GET /odata/Member('{MemberKey}')` | `MemberKey` |
| Office | `GET /odata/Office` | `GET /odata/Office('{OfficeKey}')` | `OfficeKey` |
| Media | `GET /odata/Media` | `GET /odata/Media('{MediaKey}')` | `MediaKey` |
| Contacts | `GET /odata/Contacts` | `GET /odata/Contacts('{ContactKey}')` | `ContactKey` |
| ShowingAppointment | `GET /odata/ShowingAppointment` | `GET /odata/ShowingAppointment('{ShowingAppointmentKey}')` | `ShowingAppointmentKey` |

### Export Endpoints

| Method | Path | Returns | Auth |
|--------|------|---------|------|
| `GET /export/homesoverseas.xml` | HomeOverseas.ru V4 XML feed | XML | Public (no auth) |

## OData Query Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `$filter` | Filter records | `StandardStatus eq 'Active'` |
| `$select` | Choose fields | `ListingKey,ListPrice,City` |
| `$orderby` | Sort | `ListPrice desc` |
| `$top` | Limit results | `10` |
| `$skip` | Offset for pagination | `20` |
| `$count` | Include total count | `true` |

### Filter Operators

| Operator | SQL Equivalent | Example |
|----------|---------------|---------|
| `eq` | `=` | `City eq 'Limassol'` |
| `ne` | `!=` | `StandardStatus ne 'Closed'` |
| `gt` | `>` | `ListPrice gt 500000` |
| `ge` | `>=` | `BedroomsTotal ge 3` |
| `lt` | `<` | `ListPrice lt 1000000` |
| `le` | `<=` | `YearBuilt le 2020` |
| `and` | `AND` | `City eq 'Paphos' and ListPrice lt 500000` |
| `or` | `OR` | `City eq 'Limassol' or City eq 'Paphos'` |

### Filter Functions

| Function | Example |
|----------|---------|
| `contains(field, 'text')` | `contains(PublicRemarks, 'sea view')` |
| `startswith(field, 'text')` | `startswith(City, 'Lim')` |
| `toupper(field)` | `toupper(City) eq 'LIMASSOL'` |
| `year(field)` | `year(ListingContractDate) eq 2026` |

## Example Queries

**Active listings in Limassol with 3+ bedrooms:**
```
GET /odata/Property?$filter=StandardStatus eq 'Active' and City eq 'Limassol' and BedroomsTotal ge 3&$orderby=ListPrice desc&$top=20
```

**All agents with their office:**
```
GET /odata/Member?$select=MemberKey,MemberFullName,MemberEmail,OfficeKey&$filter=MemberStatus eq 'Active'
```

**Photos for a specific listing:**
```
GET /odata/Media?$filter=ResourceRecordKey eq 'QOBRIX_12345' and MediaCategory eq 'Photo'&$orderby=Order
```

## TypeScript Fetch Example

For when a Matrix App needs OData access (rare — prefer Supabase CDL):

```typescript
async function fetchResoProperties(filter: string): Promise<Property[]> {
  const tokenRes = await fetch(`${RESO_API_URL}/oauth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: RESO_CLIENT_ID,
      client_secret: RESO_CLIENT_SECRET,
    }),
  });
  const { access_token } = await tokenRes.json();

  const res = await fetch(
    `${RESO_API_URL}/odata/Property?$filter=${encodeURIComponent(filter)}&$count=true`,
    { headers: { 'Authorization': `Bearer ${access_token}` } }
  );
  const data = await res.json();
  return data.value;
}
```

## Response Format

```json
{
  "@odata.context": "https://host/reso/odata/$metadata#Property",
  "@odata.count": 142,
  "value": [
    {
      "ListingKey": "QOBRIX_abc123",
      "ListingId": "SIR-CY-001234",
      "StandardStatus": "Active",
      "PropertyType": "Apartment",
      "ListPrice": 850000,
      "City": "Limassol",
      "BedroomsTotal": 3,
      "BathroomsTotalInteger": 2,
      "LivingArea": 145.5,
      "PublicRemarks": "Luxury seafront apartment...",
      "OriginatingSystemOfficeKey": "SHARPSIR-CY-001"
    }
  ]
}
```

## Cross-Reference

| For | See |
|-----|-----|
| ETL pipeline that produces this data | [etl-pipeline.md](etl-pipeline.md) |
| MLS 2.0 datamart overview | [mls-datamart.md](../platform/mls-datamart.md) |
| RESO DD canonical schema | [reso-canonical-schema.md](reso-canonical-schema.md) |
| How new apps should access data (Supabase) | [app-template.md](../platform/app-template.md) |
