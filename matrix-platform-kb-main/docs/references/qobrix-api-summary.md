# Qobrix API Resource Catalog

> Source: `qobrix/qobrix_openapi.yaml` (OpenAPI 3.0, 68,149 lines)
> Base URL: `https://{tenant}.qobrix.com/api/v2/`

## API Resources (83 Resource Groups)

### Core Business Resources
| Resource | Endpoints | Description |
|----------|-----------|-------------|
| Properties | CRUD + search + bulk | Real estate listings |
| Contacts | CRUD + search + bulk + duplicates | Clients, leads, sellers, buyers |
| Opportunities | CRUD + search + bulk | Deals / sales pipeline |
| Offers | CRUD + search | Purchase offers |
| Contracts | CRUD + search | Listing agreements, purchase contracts |
| Contract Parties | CRUD | Parties to contracts |
| Property Viewings | CRUD + search | Showing appointments |
| Lists | CRUD + search | Custom lists (Curated Lists) |

### Agent & Team Management
| Resource | Description |
|----------|-------------|
| Agents | Broker profiles |
| Users | System users with credentials |
| Groups | User groups / teams |
| Roles | RBAC role definitions |

### Activity Tracking
| Resource | Description |
|----------|-------------|
| Tasks | Follow-ups, action items, reminders |
| Calls | Phone call logs |
| Meetings | Meeting records |
| Email Messages | Email correspondence |
| Email Logs | Email delivery tracking |
| Sms Messages | SMS correspondence |
| Calendar | Calendar events |

### Workflow & Automation
| Resource | Description |
|----------|-------------|
| Workflows | Workflow definitions |
| Workflow Stages | Pipeline stage definitions |
| Action Plans | Step-by-step templates |
| Action Plan Steps | Individual steps within plans |
| Campaigns | Marketing campaigns |
| Scheduled Emails | Email automation |

### Property Configuration
| Resource | Description |
|----------|-------------|
| Property Types | Type classification |
| Property Subtypes | Detailed subtypes |
| Property Features | Feature definitions |
| Property Sources | Lead/listing sources |
| Property Source Imports | Import tracking |
| Property Source Import Records | Import detail records |
| Property Website Publish Reviews | Publication review tracking |
| Recommended Properties | AI/manual recommendations |
| Favorite Properties | User favorites |

### Project Management
| Resource | Description |
|----------|-------------|
| Projects | Development projects |
| Project Features | Project feature definitions |
| Recommended Projects | Recommended projects |
| Favorite Projects | User favorite projects |

### Media & Content
| Resource | Description |
|----------|-------------|
| Media | Photos, videos, documents |
| Media Categories | Media classification |
| Brochures | Generated brochures |
| Dynamic Templates | Document templates |

### Integration & Syndication
| Resource | Description |
|----------|-------------|
| Feeds | Property syndication feeds |
| Portals | External portal connections |
| Integrations | Third-party integration configs |
| Integration Items | Integration data items |
| Integration Logs | Integration activity logs |
| Webhooks Notifications | Webhook event configs |

### Portal-Specific Locations
| Resource | Description |
|----------|-------------|
| Locations | General location hierarchy |
| Bayut Locations | Bayut portal locations (UAE) |
| Bazaraki Locations | Bazaraki portal locations (Cyprus) |
| PropertyFinder Locations | PropertyFinder locations |
| Property Finder A E Locations | PropertyFinder UAE locations |
| Spitogatos Locations | Spitogatos portal locations (Greece/Cyprus) |
| Us Zip Codes | US zip code lookup |

### System Configuration
| Resource | Description |
|----------|-------------|
| Configuration | System configuration |
| Settings | Application settings |
| Custom Fields | User-defined fields |
| Field Options | Picklist option management |
| Layouts | Form layout definitions |
| Module Views | Module view configurations |
| Dashboards | Dashboard configurations |
| Widgets | Dashboard widget definitions |
| Saved Searches | Stored search criteria |
| Schema | API schema introspection |

### System Operations
| Resource | Description |
|----------|-------------|
| Authentication | Login, OAuth, API keys |
| Profile | Current user profile |
| Notifications | System notifications |
| Imports | Bulk data import |
| Import Results | Import outcome tracking |
| Exports | Data export |
| Multidelete | Bulk delete operations |
| Jobs | Background job management |
| Job Types | Job type definitions |
| Lead Lost Reasons | Lead disqualification reasons |

### Branding & UI
| Resource | Description |
|----------|-------------|
| Brands | Branding configuration |
| Theme | UI theme settings |
| Fonts | Font configuration |
| Favicon | Favicon settings |
| Languages | Localization |
| Extended Capabilities | Feature flags |
| Tenant Info | Tenant metadata |
| Search Expressions | Search syntax docs |

## Key Schemas (149 Total)

### Core Entity Schemas
`Property`, `Contact`, `Opportunity`, `Offer`, `Contract`, `ContractParty`, `PropertyViewing`, `Agent`, `User`, `Group`, `Role`

### Activity Schemas
`Task`, `Call`, `Meeting`, `EmailMessage`, `SmsMessage`, `Campaign`, `ScheduledEmail`

### Configuration Schemas
`Workflow`, `WorkflowStage`, `ActionPlan`, `ActionPlanStep`, `CustomField`, `FieldOption`, `Layout`, `Dashboard`, `Widget`

### Media & Content Schemas
`Media`, `MediaFile`, `MediaRequest`, `MediaResponse`, `DynamicTemplate`

### Integration Schemas
`Feed`, `Portal`, `Integration`, `IntegrationItem`, `IntegrationLog`, `WebhooksNotification`

### System Schemas
`SearchExpression`, `BulkEdit`, `BulkOrder`, `Import`, `Export`, `ErrorResponse`, `pagination`

## API Conventions

- URL paths: `snake_case` (e.g., `/api/v2/property_viewings`)
- URL parameters: `CamelCase` (e.g., `?resource=Properties`)
- JSON body: `CamelCase`
- IDs: UUID format
- Dates: ISO 8601
- Pagination: `page` + `limit` parameters (max 100)
- Sorting: `sort[]` parameter, prefix `-` for descending
- Filtering: `search` parameter with expression syntax
- Expansion: `include[]` parameter for associations
- Partial response: `field[]` parameter
