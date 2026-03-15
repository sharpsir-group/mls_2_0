# ETL Pipeline Architecture — Bronze / Silver / Gold

> Source: `/home/bitnami/mls_2_0/notebooks/` (Databricks notebooks)
>
> **For Lovable**: This doc describes how data flows from external sources into
> the Supabase tables your apps query. You don't interact with Databricks directly —
> data arrives in Supabase CDL tables automatically via the sync process.

## Pipeline Overview

```
External Sources → Bronze (raw) → Silver (normalized) → Gold (RESO DD 2.0) → Supabase CDL
```

| Layer | Schema | Purpose | Column Types |
|-------|--------|---------|-------------|
| Bronze | `mls2.qobrix_bronze`, `mls2.dash_bronze` | Raw API data, stored as-is | All STRING |
| Silver | `mls2.qobrix_silver`, `mls2.dash_silver` | Normalized, typed, deduplicated | INT, DECIMAL, TIMESTAMP, BOOLEAN |
| Gold | `mls2.reso_gold` | RESO DD 2.0 compliant, unified across sources | RESO-typed |

## Bronze Layer

### Qobrix Bronze (17 tables in `mls2.qobrix_bronze`)

| Table | Source API Endpoint | Row Estimate |
|-------|-------------------|-------------|
| `properties` | `/api/v2/properties` | ~2,000+ |
| `agents` | `/api/v2/agents` | ~50 |
| `contacts` | `/api/v2/contacts` | ~5,000+ |
| `users` | `/api/v2/users` | ~30 |
| `property_media` | `/api/v2/properties/{id}/media` | ~20,000+ |
| `property_viewings` | `/api/v2/property-viewings` | ~1,000+ |
| `opportunities` | `/api/v2/opportunities` | ~500+ |
| `projects` | `/api/v2/projects` | ~50 |
| `project_features` | `/api/v2/projects/{id}/features` | ~200 |
| `property_types` | `/api/v2/property-types` | ~20 |
| `property_subtypes` | `/api/v2/property-subtypes` | ~50 |
| `locations` | `/api/v2/locations` | ~100 |
| `media_categories` | `/api/v2/media-categories` | ~10 |
| `property_translations_ru` | `/api/v2/properties/{id}?lang=ru` | ~2,000 |
| `cdc_metadata` | Internal tracking | ~15 rows |
| `bayut_locations` | Portal mappings | Static |
| `bazaraki_locations` | Portal mappings | Static |

### Dash Bronze (`mls2.dash_bronze`)

| Table | Source | Method |
|-------|--------|--------|
| `properties` | DASH API or JSON files | REST API (KZ) or file scan (HU) |
| `media` | Extracted from property records | Nested JSON flattened |

## Silver Layer

### Qobrix Silver (5 tables in `mls2.qobrix_silver`)

| Table | Source Bronze | Key Transformations |
|-------|-------------|-------------------|
| `property` | `qobrix_bronze.properties` | Type casting (areas→DECIMAL, counts→INT), coordinate parsing, timestamp normalization, boolean extraction |
| `agent` | `qobrix_bronze.agents` + `users` | UNION, name normalization, status mapping, commission extraction |
| `contact` | `qobrix_bronze.contacts` | Company vs individual classification, role normalization, demographics extraction |
| `media` | `qobrix_bronze.property_media` + project media | Category classification (image/video/document), URL cleaning, MIME type extraction |
| `viewing` | `qobrix_bronze.property_viewings` | Status inference (scheduled/completed/cancelled), assessment extraction, date normalization |

### Dash Silver (3 tables in `mls2.dash_silver`)

| Table | Source | Key Transformations |
|-------|--------|-------------------|
| `property` | `dash_bronze.properties` | Unit conversion (SF→SM, AC→SM), property type normalization, feature parsing from JSON |
| `media` | `dash_bronze.media` | Category classification, dimensions extraction, primary flag detection |
| `property_features` | `dash_bronze.properties` | JSON feature array → grouped columns (Cooling, Heating, Pool, View, etc.) |

## Gold Layer (6 RESO Resources in `mls2.reso_gold`)

### `reso_gold.property`

Unified from Qobrix + Dash. Key RESO field mappings:

| RESO StandardName | Qobrix Source | Dash Source |
|-------------------|-------------|------------|
| `ListingKey` | `QOBRIX_{id}` | `DASH_{id}` |
| `StandardStatus` | `available`→`Active`, `sold`→`Closed`, `reserved`→`Pending` | Similar mapping |
| `PropertyType` | `apartment`→`Apartment`, `house`→`SingleFamilyDetached` | Mapped from Dash types |
| `ListPrice` | `list_selling_price_amount` | `currentPrice` |
| `BedroomsTotal` | `bedrooms` | `bedrooms` |
| `City` | `city` | `city` |
| `OriginatingSystemOfficeKey` | `SHARPSIR-CY-001` | `SHARPSIR-HU-001` or `SHARPSIR-KZ-001` |

125+ total fields: 48 RESO standard + extension fields (X_ prefix in current pipeline).

### `reso_gold.member`

| RESO Field | Source |
|-----------|--------|
| `MemberKey` | `QOBRIX_AGENT_{id}` or `QOBRIX_USER_{id}` |
| `MemberFirstName`, `MemberLastName` | `first_name`, `last_name` |
| `MemberEmail` | `email` |
| `MemberStatus` | `active`→`Active` |
| `OfficeKey` | Linked via parent agent |

### `reso_gold.office`

Derived from agent hierarchy (agents with sub-agents or top-level agents).

### `reso_gold.media`

Unified from Qobrix + Dash media. `MediaCategory`: `image`→`Photo`, `video`→`Video`, `document`→`Document`.

### `reso_gold.contacts`

`ContactType` mapping: `buyer`→`Buyer`, `seller`→`Seller`, `tenant`→`Tenant`.

### `reso_gold.showing_appointment`

`ShowingStatus`: `scheduled`→`Scheduled`, `completed`→`Completed`, `cancelled`→`Cancelled`.

## Notebook Inventory

| Notebook | Layer | Mode | What It Does |
|----------|-------|------|-------------|
| `00_full_refresh_qobrix_bronze.py` | Bronze | Full | Qobrix API → all bronze tables |
| `00a_cdc_qobrix_bronze.py` | Bronze | CDC | Incremental sync from Qobrix API |
| `01_dash_silver_property_etl.py` | Silver | Full | Dash bronze → silver property |
| `01_dash_silver_media_etl.py` | Silver | Full | Dash bronze → silver media |
| `01b_dash_silver_features_etl.py` | Silver | Full | Dash features JSON → grouped columns |
| `02_silver_qobrix_property_etl.py` | Silver | Full | Qobrix bronze → silver property |
| `02_cdc_silver_property_etl.py` | Silver | CDC | Incremental silver property sync |
| `02a_silver_qobrix_agent_etl.py` | Silver | Full | Bronze agents+users → silver agent |
| `02b_silver_qobrix_contact_etl.py` | Silver | Full | Bronze contacts → silver contact |
| `02c_silver_qobrix_media_etl.py` | Silver | Full | Bronze media → silver media |
| `02d_silver_qobrix_viewing_etl.py` | Silver | Full | Bronze viewings → silver viewing |
| `03_gold_reso_property_etl.py` | Gold | Full | Silver properties → RESO Property |
| `03_cdc_gold_reso_property_etl.py` | Gold | CDC | Incremental RESO Property sync |
| `03a_gold_reso_member_etl.py` | Gold | Full | Silver agent → RESO Member |
| `03b_gold_reso_office_etl.py` | Gold | Full | Silver agent → RESO Office |
| `03c_gold_reso_media_etl.py` | Gold | Full | Silver media → RESO Media |
| `03d_gold_reso_contacts_etl.py` | Gold | Full | Silver contact → RESO Contacts |
| `03d_cdc_gold_reso_contacts_etl.py` | Gold | CDC | Incremental RESO Contacts |
| `03e_gold_reso_showingappointment_etl.py` | Gold | Full | Silver viewing → RESO ShowingAppointment |
| `04a_export_homesoverseas_etl.py` | Export | Full | Gold → HomeOverseas XML feed |
| `10_verify_data_integrity_qobrix_vs_reso.py` | QA | Full | Cross-layer integrity checks |

## CDC Metadata

```sql
CREATE TABLE cdc_metadata (
    entity_name STRING,
    last_sync_timestamp TIMESTAMP,
    last_modified_timestamp STRING,
    records_processed INT,
    sync_status STRING,         -- 'completed' | 'failed'
    sync_started_at TIMESTAMP,
    sync_completed_at TIMESTAMP
)
```

CDC queries Qobrix API with `modified >= last_sync` and `created >= last_sync`, deduplicates, then MERGEs into bronze.

## Pipeline Execution

Via `scripts/run_pipeline.sh`:

| Command | What It Runs |
|---------|-------------|
| `run_pipeline.sh all` | Full refresh: bronze → silver → gold → integrity |
| `run_pipeline.sh cdc` | CDC: cdc-bronze → cdc-silver → cdc-gold |
| `run_pipeline.sh bronze` | Bronze only (full refresh) |
| `run_pipeline.sh silver` | Silver only |
| `run_pipeline.sh gold` | Gold only |
| `run_pipeline.sh export-homesoverseas` | HomeOverseas export only |

## Gold → Supabase CDL Sync

The gold layer data syncs to Supabase CDL tables that Matrix Apps query. CDL-Connected apps (Broker App, Manager App, etc.) read from these RESO-named Supabase tables directly using the standard Supabase client + React Query pattern described in [app-template.md](../platform/app-template.md).

## Future: After Qobrix Decommission

When Qobrix is decommissioned, the Qobrix bronze/silver layers become historical archives. New data originates directly in the Supabase CDL (written by Matrix Apps), and syncs to Databricks for analytics/BI/ML only. The pipeline direction reverses: CDL → Databricks (instead of Databricks → CDL).
