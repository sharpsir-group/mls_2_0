# Sharp Matrix Platform — App Catalog

> All applications in the Sharp Matrix ecosystem and their relationship to the RESO DD common data layer

## App Overview

| App | Primary Users | Purpose | Status |
|-----|--------------|---------|--------|
| **Broker App** | Brokers/Agents | Daily dashboard, AI Copilot, client management | Planned |
| **Manager App** | Sales Managers | Kanban pipelines, analytics, team management | Planned |
| **Client Portal** | Buyers, Sellers | Property search, Curated Lists, documents, communication | Planned |
| **Marketing App** | Marketing Team | Campaigns, automation, lead capture, analytics | Planned |
| **Listings Management (MLS)** | Brokers, Listing Coordinators, Marketing, Finance | Listing lifecycle, syndication, media management | CDL Deployed |
| **Contact Center** | Welcome Team | Omnichannel communication, lead qualification | Planned |
| **Finance App** | Finance Team | Commissions, invoicing, payment tracking | Planned |
| **AI Copilot** | All internal users | Next Best Action, matching, forecasting, automation | Planned |
| **BI Dashboard** | Leadership (CDSO, CDTO) | KPI tracking, management reporting | Planned |
| **SSO Console** | Admins | Authentication, authorization, RBAC | Active |
| **Admin Console** | System Admins | Platform configuration, user management | Planned |
| **Website CMS** | Content Managers | Public website content, SEO, property pages | Active |

## App Details

### Broker App
**Users**: Brokers and agents
**RESO Resources**: Property, Contacts, Member, ShowingAppointment, Media
**O365 Dependency**: Exchange Online (Mail.Read, Calendars.ReadWrite via Microsoft Graph API)
**Key Features**:
- Personal daily dashboard with auto-prioritized actions
- AI Copilot with Next Best Action per client
- Client cards with activity history
- Follow-up management (zero tolerance for missed)
- Property matching and Curated List generation
- Document generation (PDF brochures)
- **Exchange email integration**: Read inbox from CRM, search by contact/subject, attach emails to opportunities for deal context
- **Outlook calendar sync**: Viewings, meetings, and follow-ups created in CRM auto-sync to broker's Outlook with attendee invitations (client, seller/keyholder)
- **Free/busy conflict detection**: Scheduling warnings when creating events that overlap with existing calendar entries

### Manager App
**Users**: Sales managers, team leads
**RESO Resources**: Property, Contacts, Member, Office, Teams
**O365 Dependency**: Exchange Online (Calendars.ReadWrite, Mail.Read via Microsoft Graph API)
**Key Features**:
- Dual Kanban: seller-side (listings) + buyer-side (sales) pipelines
- Revenue forecast with probability-weighted calculations
- Team productivity metrics and broker comparisons
- Intervention tools: reassign, add tasks, comment
- Real-time pipeline monitoring with trouble spot detection
- **Team calendar overview**: Aggregated view of all broker Outlook calendars (viewings, meetings, availability)
- **Email audit on opportunities**: View emails attached to any team opportunity during pipeline reviews

### Client Portal
**Users**: Buyers and sellers (authenticated)
**RESO Resources**: Property, Media, ShowingAppointment, OpenHouse
**Key Features**:
- Personalized Curated Lists of properties
- Showing scheduling and confirmation
- Document exchange (contracts, title deeds)
- Communication with assigned broker
- Transaction status tracking
- **Personalized property recommendations** based on visit history and preferences (Phase 4)
- **Curated Lists powered by semantic matching** — not just manual broker curation (Phase 4)

### Marketing App
**Users**: Marketing team
**RESO Resources**: Property, Contacts, Media
**Key Features**:
- Campaign management (email, SMS, social)
- Lead capture and auto-qualification
- Segmentation and triggers
- A/B testing
- Marketing funnel analytics (CTR, opens, conversions)
- Syndication management to portals

### Listings Management (Matrix MLS)
**Users**: Brokers, listing coordinators, marketing, finance
**RESO Resources**: Property, Media, Contacts, Member, Office
**App Type**: CDL-Connected (18 `mls_*` tables on shared CDL instance)
**Repo**: `/home/bitnami/matrix-mls`
**CDL Schema**: `docs/data-models/mls-cdl-schema.md`
**Status**: Data model deployed, app under development
**Key Features**:
- Multi-step conditional listing form replacing Excel checklists (Apartment/House/Land/Development)
- Shared contact registry with role-based linking (seller, introducer, keyholder, lawyer)
- Document compliance with conditional mandatory rules (with/without title deed, land)
- Media management with Dash category alignment and development inheritance
- 9-stage status pipeline (DRAFT → PUBLISHED → SOLD) with immutable audit trail
- Multi-language marketing descriptions (EN/RU/HU) with approval workflow
- Portal syndication tracking (SIR Global, Cyprus Website, MLS Feed, social media)
- Role-based checklists (29 Broker, 10 Marketing, 5 Finance steps)
- Price history with approval workflow for large changes
- Task assignment system (photoshoot, marketing review, portal upload, finance filing)
- **Ingress channel configuration**: manage which external sources feed into CDL (CDL MLS 2.1)
- **Local vs ingress listings**: agents create local listings directly, or override/localize ingress listings from external sources
- **Soft-deactivate** (archive) instead of hard delete — preserves historical data and audit trail
- **Egress syndication controls**: per-listing toggle for which egress channels receive the listing

### Contact Center
**Users**: Welcome Team, call center
**RESO Resources**: Contacts
**Key Features**:
- Omnichannel inbox (Email, Telegram, WhatsApp, Voice)
- Lead qualification (Raw → MQL)
- Automated routing and assignment
- Communication logging

### Finance App
**Users**: Finance team
**RESO Resources**: Property (transaction data), Member
**Key Features**:
- Commission calculation and tracking
- Invoice generation
- Payment follow-up
- Agreement registry
- Financial reporting

### AI Copilot (Cross-Cutting Service)
**Users**: All internal users (embedded in other apps)
**RESO Resources**: All
**Key Features**:
- Context analysis and automatic stage determination
- Next Best Action with probability scoring
- Bidirectional matching (listings ↔ buyers)
- Lead scoring and deal probability
- Follow-up auto-scheduling
- Content suggestions for communication
- Engagement tracking and priority adjustment
- RAG-powered knowledge retrieval
- Semantic property search

### BI Dashboard
**Users**: Leadership (CDSO, CDTO), managers
**Key Features**:
- KPI tracking against targets
- Revenue vs forecast
- Marketing funnel visualization
- Sales pipeline health
- Regional comparisons (Cyprus, Hungary, Kazakhstan)

### Website CMS (Active)
**Users**: Content managers
**Key Features**:
- Public website content management and SEO optimization
- Property listing pages synced from CDL
- **Anonymous visitor profiling**: IP geolocation, device, visit patterns (Phase 4)
- **Personalized listing ranking** on property search pages (Phase 4)

### SSO Console (Active)
**Users**: System administrators
**Key Features**:
- OAuth/JWT authentication
- RBAC (role-based access control)
- User and group management
- App registration and permissions

## RESO Resource Usage Matrix

| RESO Resource | Broker | Manager | Client | Marketing | Listings | Contact | Finance | AI |
|--------------|--------|---------|--------|-----------|----------|---------|---------|-----|
| Property | R/W | R | R | R | R/W | — | R | R |
| Contacts | R/W | R | R (own) | R/W | R | R/W | R | R |
| Member | R | R/W | — | R | R | R | R | R |
| Office | R | R/W | — | R | R | — | R | R |
| Teams | R | R/W | — | — | — | — | — | R |
| Media | R/W | R | R | R/W | R/W | — | — | R |
| ShowingAppointment | R/W | R | R/W | — | R | — | — | R |
| OpenHouse | R | R | R | R/W | R/W | — | — | R |
| HistoryTransactional | R | R | — | R | R | — | R | R |
| Prospecting | R/W | R | — | R/W | — | R/W | — | R |

R = Read, W = Write, R/W = Read and Write

## O365 Integration Matrix

| Capability | Broker | Manager | Other Apps |
|-----------|--------|---------|------------|
| Exchange email read (own mailbox) | ✓ | — | — |
| Attach email to opportunity | ✓ | — | — |
| View attached emails (team) | ✓ (own) | ✓ (team) | — |
| Outlook calendar sync (own) | ✓ | — | — |
| Team calendar view | — | ✓ | — |
| Free/busy conflict detection | ✓ | ✓ | — |

See [o365-exchange-integration.md](o365-exchange-integration.md) for full technical details.
