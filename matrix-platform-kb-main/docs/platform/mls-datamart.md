# MLS 2.0 Datamart — Data Pipeline for Sharp Matrix

> Source: `/home/bitnami/mls_2_0` (production pipeline)
>
> **For Lovable**: Data arrives in your Supabase CDL tables from this pipeline.
> You do NOT call Databricks or the RESO Web API directly from Matrix Apps.
> Your apps read/write to Supabase tables. This doc explains where that data comes from.

## What MLS 2.0 Is

MLS 2.0 is the **production data pipeline** that ingests real estate data from multiple external sources, transforms it through a Databricks medallion architecture (Bronze → Silver → Gold), and syncs the RESO-compliant gold layer into the Supabase CDL for app consumption.

## Three-Platform Architecture

| Platform | Role | Why Chosen |
|----------|------|-----------|
| **Supabase** | Common Data Layer (CDL) — system of record for apps | Edge Functions, Realtime, Auth, RLS, Lovable integration |
| **Databricks** | DWH & ETL engine — data ingestion and transformation | Medallion architecture, CDC, SQL analytics, scalable compute |
| **Lovable** | App builder — builds all Matrix Apps | Rapid UI, native Supabase integration, uses `matrix-apps-template` |

> **Why Supabase over Databricks for CDL?** Databricks (with Lakebase) is a strong DWH,
> but it lacks Edge Functions and has no Lovable integration. Supabase provides the
> app-facing data layer with built-in auth, realtime, and edge compute.

## Data Sources

| Source | System | Market | Office Key | Method |
|--------|--------|--------|-----------|--------|
| Qobrix API | Qobrix CRM | Cyprus | `SHARPSIR-CY-001` | REST API (pull) |
| DASH API | Dash / Anywhere.com | Kazakhstan | `SHARPSIR-KZ-001` | REST API with Okta OAuth (pull) |
| DASH FILE | Dash / Anywhere.com | Hungary | `SHARPSIR-HU-001` | JSON file import (pull) |

## Phased Migration Roadmap

### Phase 1: Current (Now)

Data flows **inward** from external systems into the platform:

```
Qobrix API ──┐
DASH API ────┼──→ Databricks Bronze → Silver → Gold ──→ Supabase CDL
DASH FILE ───┘                                    └──→ RESO Web API → Some apps
                                                  └──→ Exports (HomeOverseas.ru)
```

- Qobrix is the CRM of record for Cyprus brokers
- Dash is the source for Hungary and Kazakhstan listings
- Some Matrix Apps consume data via the RESO Web API
- Gold → Supabase CDL sync feeds the app-facing database

### Phase 2: Transition (Matrix Apps Replace Qobrix)

Matrix Apps go live. Brokers switch from Qobrix to the new apps:

```
Matrix Apps ←→ Supabase CDL (system of record)
                    │
                    ├──→ Databricks (analytics/BI sync)
                    ├──→ Dash API (push listings for syndication)
                    ├──→ RESO Web API (3rd-party integrations)
                    └──→ Portal Exports (HomeOverseas, etc.)

Qobrix ─ ─ ─→ Supabase CDL (read-only historical migration)
```

- Matrix Apps write directly to Supabase CDL
- Qobrix becomes read-only, data migrated, then decommissioned
- Dash flips from pull to push (listings syndication)

### Phase 3: Target (Qobrix Gone)

```
Matrix Apps ←→ Supabase CDL (sole system of record)
                    │
                    ├──→ Databricks (DWH / BI / AI/ML training)
                    ├──→ Dash / SIR (push listings for syndication)
                    ├──→ RESO Web API (outbound integration standard)
                    └──→ Portal Exports
```

- Qobrix is decommissioned — no longer a data source
- Data flows outward from CDL for syndication and analytics
- Databricks shifts to pure analytics/BI/ML

### CDL MLS 2.1 — Channel-Managed Evolution

CDL MLS 2.1 formalizes the Phase 3 target into a managed platform with explicit ingress and egress channel management.

**Version naming**: MLS 2.0 = Databricks inbound pipeline (current). CDL MLS 2.1 = Supabase CDL-centric with managed channels (target).

```
Ingress Channels                       Egress Channels
┌─────────────────────┐               ┌─────────────────────┐
│ Matrix Apps (direct) │               │ Dash CRUD (push)    │
│ New Constructions    │               │ RESO Web API        │
│ Partner MLS Feeds    │               │ Portal Feeds (XML)  │
│ DASH API (legacy)    │               │ Website Realtime    │
└──────────┬──────────┘               └──────────┬──────────┘
           │                                     │
      ┌────┴─────────────────────────────────────┴────┐
      │   Supabase CDL (sole system of record)        │
      │   Ingress/Egress Channel Manager              │
      ├───────────────────────────────────────────────┤
      │   Databricks (DWH / BI / ML — analytics only) │
      └───────────────────────────────────────────────┘
```

#### Ingress Channel Management

Each data source is a managed "ingress channel" with configuration properties:

| Property | Type | Purpose |
|----------|------|---------|
| `source_id` | text | Unique channel identifier |
| `source_type` | enum | API, FILE, WEBHOOK, DIRECT |
| `market` | text | Cyprus, Hungary, Kazakhstan |
| `office_key` | text | `SHARPSIR-CY-001`, etc. |
| `filter_rules` | jsonb | Algebraic filters (price range, location, property type) |
| `record_limit` | int | Maximum records to ingest per sync |
| `sync_frequency` | interval | How often to pull (for API/FILE types) |
| `dedup_rules` | jsonb | Deduplication strategy (by ListingKey, by address, etc.) |
| `active` | boolean | Enable/disable channel |

**Channel types**:

| Type | Description | Example |
|------|------------|---------|
| **DIRECT** | Matrix Apps writing directly to CDL — no pipeline involved | Broker creates a listing in the Listings Management app |
| **API** | External REST API pulled on schedule via Databricks or Edge Function | New construction feeds from developers, partner MLS |
| **FILE** | JSON/XML file import | DASH FILE for Hungary |
| **WEBHOOK** | External system pushes data to a CDL Edge Function endpoint | Future: real-time partner notifications |

**Current channels**: Qobrix API (Cyprus, being decommissioned → DIRECT), DASH API (Kazakhstan, flipping to push), DASH FILE (Hungary, flipping to push).

**Future channels**: New construction feeds from developers/government registries, partner MLS feeds via RESO Web API.

#### Egress Channel Management

| Category | Description | Examples |
|----------|------------|---------|
| **Quasi-static feeds** | Generated on schedule, cached as files | HomeOverseas XML, Bazaraki feed |
| **Real-time API push** | CDL changes trigger outbound API calls | Dash CRUD for SIR syndication, RESO Web API for 3rd parties |
| **Website sync** | Supabase Realtime subscriptions | Public website, Client Portal see listing updates instantly |

**Current egress**: HomeOverseas XML export, RESO Web API.

**Target egress**: Dash API bidirectional CRUD, multiple portal feeds, expanded RESO Web API, website real-time sync via Supabase Realtime.

#### Listing Management: Local vs Ingress

| Listing Origin | Description | Editable? |
|---------------|-------------|-----------|
| **Local** | Created directly by agents in Matrix Apps | Full CRUD by the creating agent |
| **Ingress** | Arrived via an ingress channel (API, FILE, WEBHOOK) | Override/localize: agent can modify local copy while preserving source link |

Agents can localize ingress listings (custom pricing, photos, descriptions) without affecting the source record. The CDL maintains `origin_source` and `origin_key` fields for lineage tracking.

**Deactivation**: Soft-deactivate (archive) instead of hard delete — preserves historical data for analytics and audit trail.

## Why Supabase for CDL (Not Databricks)

Both platforms were evaluated for the CDL role:

| Capability | Supabase | Databricks (Lakebase) |
|-----------|----------|----------------------|
| Edge Functions (serverless API) | Native | Not available |
| Realtime subscriptions | Native (WebSocket) | Not available |
| Row-Level Security with JWT | Native, declarative | Requires custom implementation |
| Lovable integration | Native — Lovable generates Supabase client code | No integration |
| PostgreSQL pgvector | Available as extension | Not available (different query engine) |
| Auth / OAuth / SSO | Built-in via Edge Functions | Requires external integration |

Databricks retains its role as the DWH/ETL engine: medallion architecture, CDC pipelines, BI analytics, and AI/ML training data. The CDL role went to Supabase because it provides the app-facing capabilities that Databricks lacks.

## Databricks Catalog Structure

Catalog: `mls2`

| Schema | Layer | Tables | Purpose |
|--------|-------|--------|---------|
| `mls2.qobrix_bronze` | Bronze | 17 tables | Raw Qobrix API data (all STRING columns) |
| `mls2.dash_bronze` | Bronze | Properties + Media | Raw Dash JSON data |
| `mls2.qobrix_silver` | Silver | 5 tables | Normalized, typed Qobrix data |
| `mls2.dash_silver` | Silver | 3 tables | Normalized, typed Dash data |
| `mls2.reso_gold` | Gold | 6 tables | RESO DD 2.0 compliant (unified all sources) |
| `mls2.exports` | Export | HomeOverseas + ID map | Portal export feeds |

## Pipeline Flow

```
Sources → Bronze (raw, all strings) → Silver (normalized, typed) → Gold (RESO DD 2.0) → Supabase CDL
```

### Bronze Layer (17 Qobrix tables)

Raw API responses stored as STRING columns: `properties`, `agents`, `contacts`, `users`, `property_media`, `property_viewings`, `opportunities`, `projects`, `project_features`, `property_types`, `property_subtypes`, `locations`, `media_categories`, `cdc_metadata`, `property_translations_ru`, plus portal location mapping tables.

### Silver Layer (5 tables per source)

Normalized with correct types (INT, DECIMAL, TIMESTAMP, BOOLEAN):
- `property` — cleaned property records
- `agent` — unified agents + users
- `contact` — classified contacts (individual vs company)
- `media` — categorized media (image/video/document)
- `viewing` — property viewing records with status inference

### Gold Layer (6 RESO Resources)

RESO DD 2.0 compliant, unified across all sources:

| RESO Resource | Gold Table | Source |
|--------------|-----------|--------|
| Property | `reso_gold.property` | Qobrix + Dash (UNION) |
| Member | `reso_gold.member` | Qobrix agents/users |
| Office | `reso_gold.office` | Qobrix agents (parent relationships) |
| Media | `reso_gold.media` | Qobrix + Dash (UNION) |
| Contacts | `reso_gold.contacts` | Qobrix contacts |
| ShowingAppointment | `reso_gold.showing_appointment` | Qobrix viewings |

Each record tagged with `OriginatingSystemOfficeKey` for multi-tenant filtering.

## CDC (Change Data Capture)

| Mode | When | Duration | API Calls |
|------|------|----------|-----------|
| Full Refresh | Weekly (or on-demand) | 10-15 min | 50+ |
| CDC (incremental) | Every 15 min | 15-60 sec | 5-10 |

CDC tracks changes via `cdc_metadata` table: last sync timestamp per entity, records processed, sync status.

## RESO Web API

FastAPI application serving OData 4.0 from the gold layer.

| Detail | Value |
|--------|-------|
| Port | 3900 |
| Base path | `/reso` |
| Auth | OAuth 2.0 Client Credentials |
| Format | OData JSON |

**Current role**: Data feed for some Matrix Apps and external consumers.
**Future role**: Outbound syndication/integration API (push to Dash, feed 3rd parties).

For full endpoint reference, see [reso-web-api.md](../data-models/reso-web-api.md).

## Export Pipeline

**HomeOverseas.ru XML feed**:
- Source: `reso_gold.property` + `reso_gold.media` + Russian translations
- Filters: Cyprus only (`SHARPSIR-CY-001`), Active listings only
- Format: HomeOverseas V4 XML spec
- Endpoint: `GET /export/homesoverseas.xml` (public, cached 15 min)

## Key Source Files in `mls_2_0`

| Path | Purpose |
|------|---------|
| `api/` | FastAPI RESO Web API (routers, models, services) |
| `api/main.py` | API entry point, endpoint registration |
| `api/auth.py` | OAuth 2.0 JWT validation |
| `api/services/databricks.py` | Async Databricks SQL connector |
| `api/services/odata_parser.py` | OData query → SQL translation |
| `notebooks/` | All ETL notebooks (Bronze/Silver/Gold + CDC variants) |
| `scripts/run_pipeline.sh` | Main pipeline runner (full + CDC modes) |
| `scripts/cron_cdc_pipeline.sh` | Cron wrapper for CDC (daily, with email reports) |
| `scripts/cron_all_sources_cdc.sh` | Multi-source CDC (Cyprus + Hungary + Kazakhstan) |
| `ecosystem.config.js` | PM2 process manager configuration |

## Cross-Reference

| For | See |
|-----|-----|
| ETL pipeline technical details | [etl-pipeline.md](../data-models/etl-pipeline.md) |
| RESO Web API endpoints | [reso-web-api.md](../data-models/reso-web-api.md) |
| RESO DD canonical schema | [reso-canonical-schema.md](../data-models/reso-canonical-schema.md) |
| How apps are built | [app-template.md](app-template.md) |
