# Qobrix CRM Data Model — Reference & Migration Source

> Source: `qobrix/qobrix_openapi.yaml` (OpenAPI 3.0, API version 2.0)
> Documentation: https://qobrix.com/real-estate-crm/advanced-tools/rest-api/
>
> **Role in Sharp Matrix**: Qobrix is the **current CRM** used by Sharp Sotheby's International Realty.
> It is a **reference source** for understanding what data and capabilities the platform must support,
> and a **migration source** for existing data. It is NOT the system of record for the Sharp Matrix Platform —
> RESO DD 2.0 is the canonical data layer. See [reso-dd-overview.md](reso-dd-overview.md).

## Overview

Qobrix is the CRM currently used by Sharp Sotheby's International Realty. The Sharp Matrix Platform will replicate and extend Qobrix's capabilities through purpose-built apps (Broker App, Manager App, etc.), all sharing the RESO DD canonical data layer. The Qobrix API documentation serves as a reference for what the platform must support. The API is RESTful (JSON), uses UUID identifiers, and supports search expressions, pagination, and resource expansion.

## Migration Mapping to RESO

| Qobrix Entity | RESO Resource (canonical) | Migration Notes |
|---------------|--------------------------|-----------------|
| Property | Property | Direct mapping for most fields; see [property-field-mapping.md](property-field-mapping.md) |
| Contact | Contacts | first_name→ContactFirstName, last_name→ContactLastName, etc. |
| Agent / User | Member | Agent profiles map to Member resource |
| Groups | Teams | Team structures |
| Opportunity | HistoryTransactional | Deal/pipeline data; RESO doesn't have a direct "Opportunity" equivalent |
| Property Viewing | ShowingAppointment | Viewing records; add `outlook_event_id` for Outlook calendar sync |
| Task | — | No direct RESO equivalent; platform extension needed |
| Contract | — | No direct RESO equivalent; platform extension needed |
| Offer | — | No direct RESO equivalent; platform extension needed |
| Media | Media | Photo/video/document records |
| Project | — | Development projects; platform extension needed |
| Email Messages | `opportunity_emails` | Email metadata snapshots linked to opportunities; full emails remain in Exchange Online via Graph API. See [o365-exchange-integration.md](../platform/o365-exchange-integration.md) |
| Meetings | `broker_meetings` | Meeting records synced to Outlook calendar; types: seller_meeting, team_meeting, contract_signing, other |
| Calls | `broker_meetings` (type=follow_up_call) | Phone call records stored as broker_meetings with type `follow_up_call`; Outlook calendar events for scheduled calls |

## Authentication

- API key-based: `X-Api-User` + `X-Api-Key` headers
- OAuth 2.0: Authorization code flow with access/refresh tokens
- Session-based: Login endpoint returns session token

## Core Entities

### Properties (Listings)

The central entity. Each property represents a real estate listing.

| Key Fields | Description |
|-----------|-------------|
| id | UUID |
| property_type | Type classification |
| property_subtype | Detailed subtype |
| status | Listing status |
| sale_rent | For sale or for rent |
| list_selling_price_amount | Listing price |
| bedrooms | Number of bedrooms |
| bathrooms | Number of bathrooms |
| internal_area | Internal area in sq.m. |
| covered_verandas | Covered verandas area |
| plot_area | Plot/land area |
| city | City/location |
| country | Country |
| description | Property description |
| coordinates | Lat/long |

**Associations**: Agents, Media, Features, Projects, Recommendations, Viewings, Offers

### Contacts (Clients)

Buyers, sellers, leads, and other persons.

| Key Fields | Description |
|-----------|-------------|
| id | UUID |
| first_name | First name |
| last_name | Last name |
| email | Email address |
| phone | Phone number |
| source | Lead source |
| status | Contact status |
| assigned_to | Assigned broker (User ID) |

**Associations**: Opportunities, Properties, Tasks, Calls, Meetings, Emails, Lists

### Opportunities (Deals)

Tracks buyer-side deals through the pipeline.

| Key Fields | Description |
|-----------|-------------|
| id | UUID |
| contact_id | Related contact |
| amount | Deal value |
| status | Pipeline stage |
| probability | Close probability % |
| expected_close_date | Expected closing date |
| assigned_to | Responsible broker |

### Property Viewings (Showings)

Records of property showings/appointments.

| Key Fields | Description |
|-----------|-------------|
| id | UUID |
| property_id | Viewed property |
| contact_id | Viewing client |
| date | Viewing date |
| feedback | Client feedback |
| result | Viewing outcome |

### Tasks (Follow-ups & Actions)

All follow-up tasks, reminders, and action items.

| Key Fields | Description |
|-----------|-------------|
| id | UUID |
| subject | Task title |
| description | Task details |
| due_date | Due date |
| status | Open/Completed/Overdue |
| assigned_to | Responsible user |
| related_to | Related entity (contact, property, opportunity) |

### Contracts (Agreements)

Listing agreements, purchase contracts.

### Offers

Purchase offers on properties.

### Projects

Development projects containing multiple properties.

## Supporting Entities

| Entity | Purpose |
|--------|---------|
| **Agents** | Broker profiles and assignments |
| **Users** | System users with roles |
| **Groups** | User groups / teams |
| **Roles** | RBAC role definitions |
| **Workflows** | Automated workflow definitions |
| **Workflow Stages** | Pipeline stage definitions |
| **Action Plans** | Step-by-step action plan templates |
| **Campaigns** | Marketing campaign records |
| **Calls** | Phone call logs → migrates to `broker_meetings` (type=follow_up_call) with Outlook sync |
| **Meetings** | Meeting records → migrates to `broker_meetings` with Outlook calendar sync |
| **Email Messages** | Email correspondence → migrates to `opportunity_emails` (snapshots); live access via Exchange Online / Graph API |
| **SMS Messages** | SMS correspondence |
| **Media** | Photos, videos, documents |
| **Lists** | Custom lists (e.g., Curated Lists) |
| **Saved Searches** | Stored search criteria |
| **Feeds** | Property syndication feeds |
| **Portals** | External portal integrations |
| **Dashboards** | Dashboard configurations |
| **Widgets** | Dashboard widget definitions |

## API Patterns

### Search Expression Syntax
```
list_selling_price_amount <= 200000 and type in ["house", "apartment"] and status == "available"
```

Special variables: `CURRENT_USER`, `THIS_WEEK`, `TODAY`

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page_count": 4,
    "current_page": 1,
    "has_next_page": true,
    "count": 38,
    "limit": 10
  }
}
```

### Resource Expansion
```
GET /api/v2/properties/{id}?include[]=Agents&include[]=Media
```

### Partial Responses
```
GET /api/v2/contacts?field[]=first_name&field[]=last_name
```

## Capabilities to Replicate in Sharp Matrix

Qobrix provides capabilities that the Sharp Matrix Platform must match or exceed:

| Qobrix Capability | Sharp Matrix Target App | Notes |
|-------------------|------------------------|-------|
| Property CRUD + search | Broker App | Enhanced with RESO-standard fields and AI-powered search |
| Contact management | Broker App, Client Portal | Split across agent-facing and client self-service apps |
| Deal pipeline (Opportunities) | Broker App, Manager App | Pipeline tracking with analytics |
| Task management | Broker App | Follow-ups, reminders, action plans |
| Property viewings | Broker App, Client Portal | Scheduling with client-facing booking |
| Media management | Broker App, Marketing App | Photo/video/virtual tour management |
| Campaigns & marketing | Marketing App | Syndication, email campaigns, SMM |
| Email correspondence | Broker App | Exchange Online read via Graph API; attach to opportunities. Replaces Qobrix internal email module. |
| Meeting scheduling | Broker App | Outlook calendar sync via Graph API; replaces Qobrix Meetings/Calls. |
| Dashboards & reporting | Manager App | Enhanced with BI/analytics layer |
| Workflow automation | All apps | Platform-level workflow engine |
| API integrations (feeds, portals) | Integration Layer | API Gateway with RESO-compliant endpoints |

## Full API Resource List

See [qobrix-api-summary.md](../references/qobrix-api-summary.md) for the complete endpoint catalog with 83 resource groups and 149 schemas. Use this as a reference when designing Sharp Matrix API endpoints.
