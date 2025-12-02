# MLS 2.0 Datamart - Qobrix → RESO

**Status**: ✅ Working (test mode with 10 properties)

## Databricks Free Edition Setup

### 1. Create Databricks Account

1. Go to https://www.databricks.com/try-databricks
2. Click **"Get started for free"**
3. Sign up with email or Google/Microsoft account
4. Select **Community Edition** (free) or trial workspace
5. Choose a cloud provider region (recommend **EU** for GDPR compliance)

### 2. Create SQL Warehouse

1. In Databricks workspace, go to **SQL** → **SQL Warehouses**
2. Click **Create SQL Warehouse**
3. Name it (e.g., `mls2-warehouse`)
4. Select **Serverless** (recommended) or smallest size
5. Click **Create**
6. Note the **HTTP Path** from warehouse settings (needed for `.env`)

### 3. Create Unity Catalog

1. Go to **Catalog** → **Create Catalog**
2. Name: `mls2`
3. Click **Create**
4. The schemas (`qobrix_bronze`, `qobrix_silver`, `reso_gold`) are created automatically by the notebooks

### 4. Generate Access Token

1. Click your username (top-right) → **User Settings**
2. Go to **Developer** → **Access tokens**
3. Click **Generate new token**
4. Description: `MLS 2.0 CLI`
5. Lifetime: 90 days (or as needed)
6. Copy the token immediately (shown only once!)

### 5. Install Databricks CLI

```bash
# Using pip
pip install databricks-cli

# Or using homebrew (macOS)
brew install databricks-cli
```

### 6. Configure CLI

```bash
databricks configure --token
# Enter your workspace URL: https://dbc-xxxxx.cloud.databricks.com
# Enter your access token: dapi...
```

### 7. Configure MLS 2.0

```bash
cd mls_2_0
cp .env.example .env
```

Edit `.env` with your values:
```
QOBRIX_API_USER=<from-qobrix>
QOBRIX_API_KEY=<from-qobrix>
QOBRIX_API_BASE_URL=https://<instance>.qobrix.com/api/v2
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
```

### 8. Import Notebooks & Run

```bash
# Import notebooks to Databricks
./scripts/import_notebooks.sh

# Run full pipeline
./scripts/run_pipeline.sh all
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `DIRECTORY_PROTECTED` error | Use `/Shared/` path (not `/Repos/`) |
| `INVALID_PARAMETER_VALUE` | Use multi-task format with `tasks` array |
| `CANNOT_INFER_TYPE_FOR_FIELD` | Convert to Pandas DataFrame first |
| `Public DBFS root is disabled` | Use Pandas approach, not DBFS temp files |
| SQL Warehouse not starting | Check warehouse status, may need to wake up |

---

## Documentation

### RESO Data Dictionary 2.0
- **Wiki**: https://ddwiki.reso.org/display/DDW20/
- **Resources**: Property, Member, Office, Media, Contacts, ShowingAppointment

### Qobrix API
- **Interactive Docs**: `${QOBRIX_API_BASE_URL}/../docs` (see your `.env`)
- **OpenAPI Spec**: [`docs/qobrix_openapi.yaml`](docs/qobrix_openapi.yaml) (local copy)

## Quick Start

```bash
# From the mls_2_0 directory:
cd mls_2_0

# Import notebooks to Databricks (one-time or after changes)
./scripts/import_notebooks.sh

# Run full pipeline (bronze → silver → gold → integrity test)
./scripts/run_pipeline.sh all

# Or run individual steps
./scripts/run_pipeline.sh bronze         # Raw data from API
./scripts/run_pipeline.sh silver         # All silver tables
./scripts/run_pipeline.sh silver-agent   # Silver agent only
./scripts/run_pipeline.sh silver-contact # Silver contact only
./scripts/run_pipeline.sh silver-media   # Silver media only
./scripts/run_pipeline.sh silver-viewing # Silver viewing only
./scripts/run_pipeline.sh gold           # All 6 RESO resources
./scripts/run_pipeline.sh gold-property  # Property only
./scripts/run_pipeline.sh gold-member    # Member only
./scripts/run_pipeline.sh gold-office    # Office only
./scripts/run_pipeline.sh gold-media     # Media only
./scripts/run_pipeline.sh gold-contacts  # Contacts only
./scripts/run_pipeline.sh gold-showing   # ShowingAppointment only
./scripts/run_pipeline.sh integrity

# Run local integrity test (no Databricks job)
./scripts/verify_data_integrity.sh
```

## Directory Structure

```
mls_2_0/
├── .env                        # Credentials (git-ignored)
├── .env.example                # Template for .env
├── docs/
│   ├── qobrix_openapi.yaml     # Qobrix API OpenAPI spec (68k lines)
│   └── qobrix_api_docs.html    # API docs viewer
├── notebooks/
│   ├── 00_full_refresh_qobrix_bronze.py       # Bronze: All Qobrix data + lookups
│   ├── 02_silver_qobrix_property_etl.py       # Silver: Normalize properties
│   ├── 02a_silver_qobrix_agent_etl.py         # Silver: Normalize agents + users
│   ├── 02b_silver_qobrix_contact_etl.py       # Silver: Normalize contacts
│   ├── 02c_silver_qobrix_media_etl.py         # Silver: Normalize media
│   ├── 02d_silver_qobrix_viewing_etl.py       # Silver: Normalize viewings
│   ├── 03_gold_reso_property_etl.py           # Gold: RESO Property + extensions
│   ├── 03a_gold_reso_member_etl.py            # Gold: RESO Member (from silver.agent)
│   ├── 03b_gold_reso_office_etl.py            # Gold: RESO Office (from silver.agent)
│   ├── 03c_gold_reso_media_etl.py             # Gold: RESO Media (from silver.media)
│   ├── 03d_gold_reso_contacts_etl.py          # Gold: RESO Contacts (from silver.contact)
│   ├── 03e_gold_reso_showingappointment_etl.py # Gold: RESO ShowingAppointment
│   └── 10_verify_data_integrity_qobrix_vs_reso.py  # Integrity test
├── scripts/
│   ├── import_notebooks.sh     # Import notebooks to Databricks
│   ├── run_pipeline.sh         # Run ETL pipeline via CLI
│   └── verify_data_integrity.sh # Local integrity test
└── .cursorrules                # LLM context for Cursor
```

## Configuration

All credentials are in `mls_2_0/.env` (git-ignored):

```
QOBRIX_API_USER=<your-api-user-uuid>
QOBRIX_API_KEY=<your-api-key>
QOBRIX_API_BASE_URL=https://<your-instance>.qobrix.com/api/v2
DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-databricks-token>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<your-warehouse-id>
```

Copy `.env.example` to `.env` and fill in your values.

## Databricks Catalog Structure

Catalog: `mls2`

```
mls2 (catalog)
├── qobrix_bronze (schema) - 17 tables
│   ├── properties          # Raw Qobrix properties (241 fields)
│   ├── agents              # Real estate agents
│   ├── property_types      # Property type lookups
│   ├── property_subtypes   # Property subtype lookups
│   ├── projects            # Development projects
│   ├── project_features    # Project feature lookups
│   ├── contacts            # Sellers/buyers
│   ├── users               # System users
│   ├── locations           # Location/area lookups
│   ├── media_categories    # Media type lookups
│   ├── property_viewings   # Viewing appointments
│   ├── opportunities       # Leads/inquiries for properties
│   ├── bayut_locations     # Bayut portal location mappings
│   ├── bazaraki_locations  # Bazaraki portal location mappings
│   ├── spitogatos_locations # Spitogatos portal location mappings
│   ├── property_finder_ae_locations # Property Finder AE mappings
│   └── property_media      # Photos/documents/floorplans
├── qobrix_silver (schema) - 5 tables
│   ├── property            # Normalized properties
│   ├── agent               # Normalized agents + users
│   ├── contact             # Normalized contacts
│   ├── media               # Normalized property media
│   └── viewing             # Normalized property viewings
└── reso_gold (schema) - 6 RESO resources
    ├── property            # RESO Property + 70+ Qobrix extension fields
    ├── member              # RESO Member (agents + users)
    ├── office              # RESO Office (agencies)
    ├── media               # RESO Media (photos, documents, floorplans)
    ├── contacts            # RESO Contacts (buyers, sellers, leads)
    └── showing_appointment # RESO ShowingAppointment (property viewings)
```

## RESO Data Dictionary Compliance

### Standard RESO Resources

| Resource | Bronze Source | Silver Source | RESO Wiki |
|----------|---------------|---------------|-----------|
| Property | `properties` | `property` | [Property Resource](https://ddwiki.reso.org/display/DDW20/Property+Resource) |
| Member | `agents`, `users` | `agent` | [Member Resource](https://ddwiki.reso.org/display/DDW20/Member+Resource) |
| Office | `agents` (agencies) | `agent` | [Office Resource](https://ddwiki.reso.org/display/DDW20/Office+Resource) |
| Media | `property_media` | `media` | [Media Resource](https://ddwiki.reso.org/display/DDW20/Media+Resource) |
| Contacts | `contacts` | `contact` | [Contacts Resource](https://ddwiki.reso.org/display/DDW20/Contacts+Resource) |
| ShowingAppointment | `property_viewings` | `viewing` | [ShowingAppointment Resource](https://ddwiki.reso.org/display/DDW20/ShowingAppointment+Resource) |

### RESO Standard Fields (Mapped from Qobrix)

These Qobrix fields are mapped to official RESO Data Dictionary field names for better interoperability.

**Core Identifiers:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `ListingKey` | `id` | `CONCAT('QOBRIX_', id)` |
| `ListingId` | `ref` | Direct mapping |

**Status & Type:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `StandardStatus` | `status` | available→Active, reserved/under_offer→Pending, sold/rented→Closed, withdrawn→Withdrawn |
| `PropertyType` | `property_type` | apartment→Apartment, house→SingleFamilyDetached, land→Land, office→Office, etc. |
| `PropertySubType` | `property_subtype` | Label from lookup table |

**Property Details:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `BedroomsTotal` | `bedrooms` | INT |
| `BathroomsTotalInteger` | `bathrooms` | INT |
| `LivingArea` | `internal_area_amount` | DECIMAL |
| `LivingAreaUnits` | - | `'SquareMeters'` |
| `LotSizeSquareFeet` | `plot_area_amount` | DECIMAL |
| `LotSizeUnits` | - | `'SquareMeters'` |

**Pricing:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `ListPrice` | `list_selling_price_amount` | DECIMAL |
| `LeasePrice` | `list_rental_price_amount` | DECIMAL |

**Dates:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `ListingContractDate` | `listing_date` | Direct mapping |
| `ModificationTimestamp` | `modified` | Direct mapping |

**Location:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `UnparsedAddress` | `street` | Direct mapping |
| `City` | `city` | Direct mapping |
| `StateOrProvince` | `state` | Direct mapping |
| `PostalCode` | `post_code` | Direct mapping |
| `Country` | `country` | Direct mapping |
| `Latitude` | `coordinates` | Parse first value from "lat,lon" |
| `Longitude` | `coordinates` | Parse second value from "lat,lon" |

**Remarks & Agent:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `PublicRemarks` | `description` | Direct mapping |
| `ListAgentKey` | `agent` | `CONCAT('QOBRIX_AGENT_', agent)` |
| `CoListAgentKey` | `salesperson` | `CONCAT('QOBRIX_AGENT_', salesperson)` |

**Building & Features (Hybrid Mapping):**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `YearBuilt` | `construction_year` | INT |
| `YearBuiltEffective` | `renovation_year` | INT |
| `View` | `view` | Direct mapping (multi-value) |
| `PoolFeatures` | `pool_features` | Direct mapping (multi-value) |
| `Heating` | `heating` | Direct mapping |
| `Cooling` | `cooling` | Direct mapping |
| `Furnished` | `furnished` | true→Furnished, false→Unfurnished, partially→Partially |
| `PetsAllowed` | `pets_allowed` | true→Yes, false→No |
| `FireplaceYN` | `fireplace` | Boolean |
| `ParkingFeatures` | `parking`, `covered_parking`, `uncovered_parking` | Concatenated: "Covered,Uncovered" |
| `StoriesTotal` | `floors_building` | INT (total floors in building) |
| `Stories` | `floor_number` | INT (unit's floor) |

**Total: 34 RESO Standard Fields** mapped from Qobrix data.

### Extension Fields (X_ prefix)

Per RESO convention, vendor-specific fields use the `X_` prefix. These are Qobrix-specific attributes that don't have RESO equivalents:

| Category | Extension Fields |
|----------|-----------------|
| **Views (Regional)** | `X_SeaView`, `X_MountainView`, `X_BeachFront` (boolean flags) |
| **Pool Details** | `X_PrivateSwimmingPool`, `X_CommonSwimmingPool` |
| **Property Features** | `X_Elevator`, `X_AirCondition`, `X_Alarm`, `X_SmartHome`, `X_SolarWaterHeater` |
| **Building Details** | `X_ConstructionType`, `X_ConstructionStage`, `X_FloorType`, `X_NewBuild` |
| **Energy Details** | `X_EnergyEfficiencyGrade`, `X_HeatingType`, `X_HeatingMedium`, `X_CoolingType` |
| **Distances** | `X_DistanceFromBeach`, `X_DistanceFromAirport`, `X_DistanceFromCentre`, `X_DistanceFromSchool` |
| **Room Details** | `X_LivingRooms`, `X_Kitchens`, `X_KitchenType`, `X_WCBathrooms`, `X_OfficeSpaces` |
| **Area Details** | `X_CoveredArea`, `X_UncoveredArea`, `X_TotalArea`, `X_GardenArea`, `X_RoofGardenArea` |
| **Land Details** | `X_BuildingDensity`, `X_Coverage`, `X_CornerPlot`, `X_TownPlanningZone` |
| **Commercial** | `X_IdealFor`, `X_LicensedFor`, `X_BusinessTransferOrSale` |
| **Marketing** | `X_Featured`, `X_PropertyOfTheMonth`, `X_VideoLink`, `X_VirtualTourLink` |
| **Qobrix Metadata** | `X_QobrixId`, `X_QobrixRef`, `X_QobrixSource`, `X_QobrixCreated`, `X_QobrixModified` |

## Pipeline Flow

```
Qobrix API
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Bronze Layer (qobrix_bronze) - 17 tables                         │
│   properties, agents, users, contacts, projects, media, etc.     │
│   Raw data from API, all columns as STRING                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Silver Layer (qobrix_silver) - 5 tables                          │
│   property  - normalized properties (type casting, null handling)│
│   agent     - unified agents + users (cleaned contact info)      │
│   contact   - normalized contacts (company vs individual)        │
│   media     - normalized media (categorized, cleaned URLs)       │
│   viewing   - normalized viewings (status, assessments)          │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Gold Layer (reso_gold) - 6 RESO resources                        │
│   property           → RESO Property + X_ extensions             │
│   member             → RESO Member (from silver.agent)           │
│   office             → RESO Office (from silver.agent)           │
│   media              → RESO Media (from silver.media)            │
│   contacts           → RESO Contacts (from silver.contact)       │
│   showing_appointment → RESO ShowingAppointment (from viewing)   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
  Integrity Test
```

## Test Mode

Currently configured for **10 properties** (test mode).

To change, edit `notebooks/00_full_refresh_qobrix_bronze.py`:
```python
test_mode = True
max_properties = 10  # Change to 100, 1000, or None for all
```

## Integrity Test Features

- Status mapping validation (Qobrix → RESO StandardStatus)
- Property type mapping (Qobrix → RESO PropertyType)
- RESO compliance (valid enums, required fields)
- Bidirectional coverage (API ↔ RESO)
- Test mode awareness (only reports critical issues)

## Key Files for LLM Context

When starting a new session, read these files to understand the project:

1. `mls_2_0/README.md` - This file (overview)
2. `mls_2_0/.cursorrules` - LLM context and common commands
3. `mls_2_0/.env` - Credentials (if needed)
4. `mls_2_0/notebooks/00_full_refresh_qobrix_bronze.py` - Bronze ingestion
5. `mls_2_0/notebooks/03_gold_reso_property_etl.py` - RESO Property with extensions
6. `mls_2_0/scripts/verify_data_integrity.sh` - Local integrity test

## Common Commands

```bash
# Check Databricks CLI is configured
databricks jobs list 2>&1 | grep -v "^WARN:" | head -5

# Check run status
databricks runs get --run-id <RUN_ID> 2>&1 | grep -v "^WARN:" | grep -E '"result_state"|"life_cycle_state"'

# Query tables in Databricks
# Use the SQL Warehouse UI or SQL API
```

## Databricks Job Names

| Job | Name |
|-----|------|
| Bronze | `MLS 2.0 - Qobrix Bronze Full Refresh` |
| Silver Property | `MLS 2.0 - Qobrix Silver Property ETL` |
| Silver Agent | `MLS 2.0 - Qobrix Silver Agent ETL` |
| Silver Contact | `MLS 2.0 - Qobrix Silver Contact ETL` |
| Silver Media | `MLS 2.0 - Qobrix Silver Media ETL` |
| Silver Viewing | `MLS 2.0 - Qobrix Silver Viewing ETL` |
| Gold Property | `MLS 2.0 - RESO Gold Property ETL` |
| Gold Member | `MLS 2.0 - RESO Gold Member ETL` |
| Gold Office | `MLS 2.0 - RESO Gold Office ETL` |
| Gold Media | `MLS 2.0 - RESO Gold Media ETL` |
| Gold Contacts | `MLS 2.0 - RESO Gold Contacts ETL` |
| Gold Showing | `MLS 2.0 - RESO Gold ShowingAppointment ETL` |
| Integrity | `MLS 2.0 - Qobrix vs RESO Integrity Test` |

## Next Steps

- [x] Add RESO Member resource (agents/users)
- [x] Add RESO Office resource (agencies)
- [x] Add RESO Media resource (photos/documents)
- [x] Add RESO Contacts resource (buyers/sellers)
- [x] Add RESO ShowingAppointment resource (property viewings)
- [x] Add Qobrix extension fields (X_ prefix) to Property
- [x] Map Qobrix fields to RESO standard names (hybrid approach)
- [x] Add Silver layer for all resources (agent, contact, media, viewing)
- [ ] Implement CDC (incremental updates)
- [ ] Scale to full data load
