# Digital Ecosystem Architecture

> Source: `vision/Sarp SIR Platform-2026-02-18-125014.mmd` (Mermaid system diagram)
> Source: `vision/Sharp-Sothebys-International-Realty.pdf` (slides 10-13)
>
> **For Lovable**: This shows the full ecosystem. For how to build apps, see [app-template.md](app-template.md).

## Three-Platform Architecture

| Platform | Role | Key Components |
|----------|------|---------------|
| **Supabase** | CDL & system of record | SSO instance (auth/permissions) + App DB instances (per app) |
| **Databricks** | DWH & ETL engine | Bronze/Silver/Gold pipeline, CDC, analytics |
| **Lovable** | App builder | `matrix-apps-template`, builds all Matrix Apps |

## Full Platform Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL CHANNELS                                │
│  ┌───────┐ ┌──────────┐ ┌──────────────┐ ┌───────┐ ┌────────────────┐ │
│  │ Email │ │ Telegram │ │ WhatsApp BSP │ │ Voice │ │ Google/Meta Ads│ │
│  └───┬───┘ └────┬─────┘ └──────┬───────┘ └───┬───┘ └───────┬────────┘ │
└──────┼──────────┼──────────────┼─────────────┼─────────────┼───────────┘
       │          │              │             │             │
┌──────┼──────────┼──────────────┼─────────────┼─────────────┼───────────┐
│      │     OWN CHANNELS        │             │             │           │
│  ┌───┴────────┐ ┌──────────────┴──┐ ┌───────┴─────────┐   │           │
│  │ Public     │ │ Client Portal   │ │ Mobile App      │   │           │
│  │ Website    │ │ (Personal       │ │                 │   │           │
│  │            │ │  Cabinet)       │ │                 │   │           │
│  └─────┬──────┘ └───────┬────────┘ └────────┬────────┘   │           │
└────────┼────────────────┼───────────────────┼─────────────┼───────────┘
         │                │                   │             │
    ┌────┴────────────────┴───────────────────┴─────────────┴──────┐
    │              API GATEWAY / ESB (Integration Layer)            │
    └──┬──────────┬──────────┬──────────────┬──────────────┬───────┘
       │          │          │              │              │
┌──────┴──────────┴──────────┴──────────────┴──────────────┴───────────┐
│              MATRIX APPS (Built by Lovable from template)             │
│                                                                       │
│  CDL-Connected:                                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ Broker App   │ │ Manager App  │ │ Marketing    │ │ Client      │ │
│  │ (Sales +     │ │ (Pipeline +  │ │ Platform     │ │ Portal      │ │
│  │  Listings)   │ │  Kanban)     │ │              │ │             │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘ │
│         │                │                │                │         │
│  Domain-Specific:                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ HRMS         │ │ Finance App  │ │ Contact      │                  │
│  │ (own DB)     │ │ (own DB)     │ │ Center       │                  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                  │
│         │                │                │                           │
│  ┌──────┴────────────────┴────────────────┴──────────────────────┐   │
│  │ SSO Console │ Admin Console │ BI Dashboard │ Website CMS       │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────┬───────────────┬────────────────┬──────────────────────────┘
           │               │                │
┌──────────┴───────────────┴────────────────┴──────────────────────────┐
│  SUPABASE (Common Data Layer & System of Record)                      │
│                                                                       │
│  ┌─────────────────────────────┐ ┌────────────────────────────────┐  │
│  │ SSO Instance                │ │ App DB Instances                │  │
│  │ xgubaguglsnokjyudgvc       │ │ CDL: RESO tables (Property,   │  │
│  │ Auth, Tenants, Permissions  │ │   Member, Contacts, Media)     │  │
│  │ Edge Functions (OAuth,      │ │ Domain: HRMS tables, Finance   │  │
│  │   admin, switch-role)       │ │   tables, etc.                 │  │
│  │ AD Users, Role Config       │ │ RLS enforced via SSO JWT       │  │
│  └─────────────────────────────┘ └────────────────────────────────┘  │
└──────────┬───────────────────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────────────────┐
│  DATABRICKS (DWH & ETL Engine)                                        │
│                                                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ Bronze       │ │ Silver       │ │ Gold (RESO)  │                  │
│  │ (raw strings)│→│ (normalized) │→│ (unified)    │──→ Supabase CDL  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
│  CDC every 15 min │ Analytics + BI │ AI/ML training data             │
└──────────────────────────────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────────────────┐
│  EXTERNAL SOURCES & SYNDICATION                                       │
│                                                                       │
│  Inbound (current, being phased out):                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ Qobrix API   │ │ DASH API     │ │ DASH FILE    │                  │
│  │ (Cyprus)     │ │ (Kazakhstan) │ │ (Hungary)    │                  │
│  │ ⚠ replacing  │ │ ⚠ flipping   │ │ ⚠ flipping   │                  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
│                                                                       │
│  Outbound (target state):                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ RESO Web API │ │ Dash/SIR     │ │ Portal       │                  │
│  │ (OData 4.0)  │ │ (push sync)  │ │ Exports      │                  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
└──────────────────────────────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────────────────┐
│  AI/ML & ANALYTICS                                                    │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐                    │
│  │ GenAI &     │  │ Scoring     │  │ AI Agents │                    │
│  │ Embedding   │  │ Models      │  │ (Copilot) │                    │
│  └─────────────┘  └─────────────┘  └───────────┘                    │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐                    │
│  │ RAG         │  │ Semantic    │  │ Recomm.   │                    │
│  │             │  │ Search      │  │ Engine    │                    │
│  └─────────────┘  └─────────────┘  └───────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### External Channels
Inbound communication touchpoints managed through the API Gateway.

| Channel | Purpose | Integration |
|---------|---------|-------------|
| Email | Client correspondence, marketing campaigns, opportunity context | SMTP/IMAP via API Gateway; Exchange Online via Microsoft Graph API (delegated, for broker mailbox read + attach to opportunity) |
| Telegram | Instant messaging (high priority: Cyprus, Kazakhstan) | Bot API via Gateway |
| WhatsApp BSP | Business messaging (high priority: all markets) | BSP API via Gateway |
| Voice | Phone calls, contact center | VoIP/SIP via Gateway |
| Google/Meta Ads | Lead generation, remarketing | Ads API via Gateway |

### Own Channels
Company-controlled digital properties.

| Channel | Purpose |
|---------|---------|
| Public Website | Property listings, brand, SEO, lead capture |
| Client Portal (Personal Cabinet) | Authenticated client area: Curated Lists, documents, communication |
| Mobile App | On-the-go access for brokers and clients |

### Integration Layer
**API Gateway / ESB** — central hub connecting all channels to application systems. Every request flows through this layer for consistent authentication (Matrix SSO), logging, and rate limiting.

**Ingress/Egress Channel Manager** (CDL MLS 2.1) — orchestration layer that manages data flow between external sources, the CDL, and syndication targets. Handles channel configuration, deduplication, filtering, and routing. See [mls-datamart.md](mls-datamart.md) for channel taxonomy.

### Matrix Apps (Application Layer)

All apps are built by **Lovable** from the `matrix-apps-template`. Two categories:

| Type | Apps | Supabase Tables |
|------|------|----------------|
| **CDL-Connected** | Broker, Manager, Marketing, Client Portal, Listings, Website CMS | Shared RESO tables: `property`, `member`, `contacts`, `media` |
| **Domain-Specific** | HRMS, Finance, Contact Center | Own tables: `employees`, `vacations`, `transactions`, etc. |

All apps share: SSO auth, dual-Supabase architecture, 5-level scope, CRUD permissions, shadcn/ui.

### Supabase (CDL & System of Record)

**Dual-instance architecture per app:**
- SSO Instance (`xgubaguglsnokjyudgvc`) — auth, permissions, tenants
- App DB Instance (per app) — business data with RLS

CDL-Connected apps share RESO-named tables. Domain-Specific apps define their own schemas.

### Databricks (DWH & ETL)

MLS 2.0 pipeline (`/home/bitnami/mls_2_0`):
- Ingests from Qobrix API (Cyprus), DASH API (Kazakhstan), DASH FILE (Hungary)
- Transforms through Bronze → Silver → Gold (RESO DD 2.0)
- Syncs gold layer to Supabase CDL
- Runs CDC every 15 minutes for incremental updates

See [mls-datamart.md](mls-datamart.md) for details.

### External Sources & Syndication

**Current state (inbound pull):**
- Qobrix API → Databricks (being replaced by Matrix Apps)
- DASH API/FILE → Databricks (flipping to outbound push)

**Target state (outbound push):**
- RESO Web API → 3rd-party integrations
- Dash / SIR → syndication push
- Portal exports → HomeOverseas.ru, etc.

### AI/ML & Analytics Layer

| Component | Function |
|-----------|----------|
| GenAI & Embedding Providers | LLM services, text embedding for semantic capabilities |
| Scoring Models | Lead scoring, deal probability, property valuation |
| AI Agents (Copilot) | AI Brokerage Copilot: Next Best Action, forecasting, automation |
| RAG | Knowledge-grounded AI responses |
| Semantic Search | Natural language property and client search |
| Recommendation Engine | Property matching, Curated List generation |
| Personalization Engine | Visitor profiling, semantic ranking, personalized listing order |
| Visitor Profiling | Anonymous + authenticated user behavior tracking for recommendation input |

## Data Flow Patterns

### Listing Ingress Flow (CDL MLS 2.1)
```
Direct CDL write (Matrix Apps) → Supabase CDL → Realtime → all apps
API ingress (new constructions)  → Edge Function → Supabase CDL → Realtime
Legacy pipeline (Databricks)     → Gold sync → Supabase CDL (being phased out)
```

### Listing Creation Flow (Target State)
```
Broker (Broker App) → Supabase CDL (RESO Property table)
    → Realtime → Manager App, Client Portal see updates instantly
    → Sync → Databricks (analytics/BI)
    → Push → Dash/SIR (syndication), RESO Web API (3rd parties)
    → AI Copilot monitors: DOM, viewings, conversions
```

### Lead Processing Flow
```
Ads/Website/Referral → API Gateway → Marketing Platform → Contact Center
    → Supabase CDL (RESO Contacts table)
    → AI/ML (scoring, qualification, Next Best Action)
    → Assignment to broker via Manager App
```

### O365 Integration Flows

**Email (read + attach to opportunity):**
```
Broker App → email-messages Edge Function → Microsoft Graph API (/me/messages)
    → Exchange Online (broker's mailbox, delegated access)
    → Broker selects email → email-attach Edge Function
    → Snapshot stored in Supabase CDL (opportunity_emails table)
```

**Calendar (CRM ↔ Outlook sync):**
```
Broker creates viewing/meeting in CRM → calendar-events Edge Function
    → Microsoft Graph API (POST /me/calendar/events)
    → Outlook event created with attendees (client, seller/keyholder)
    → outlook_event_id stored back in CRM (showing_appointment / broker_meetings)

Broker views calendar in CRM → calendar-events Edge Function
    → Microsoft Graph API (GET /me/calendarView)
    → Merged view: CRM-linked events + Outlook-only events
```

See [o365-exchange-integration.md](o365-exchange-integration.md) for full architecture, data model, and security details.

### Analytics Flow
```
All Matrix Apps → Supabase CDL → Sync → Databricks DWH
    → BI dashboards → Scoring models → RAG knowledge base
    → Semantic Search → Recommendation Engine
```
