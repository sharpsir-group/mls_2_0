# MLS 2.0 Datamart - Qobrix → RESO

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

### Data Mapping
- **Full Mapping Reference**: [`docs/mapping.md`](docs/mapping.md) - Complete Qobrix → RESO field mapping

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

## RESO Web API

A FastAPI-based RESO Data Dictionary 2.0 compliant OData API that queries Databricks directly.

### PM2 Management (Production)

```bash
# Using the management script
./scripts/pm2-manage.sh start     # Start the API
./scripts/pm2-manage.sh stop      # Stop the API
./scripts/pm2-manage.sh restart   # Restart the API
./scripts/pm2-manage.sh status    # Show status
./scripts/pm2-manage.sh logs      # View logs
./scripts/pm2-manage.sh health    # Check API health
./scripts/pm2-manage.sh setup     # Initial setup (venv + deps)
./scripts/pm2-manage.sh save      # Save PM2 state for reboot

# Or use PM2 directly
pm2 start ecosystem.config.js
pm2 save
pm2 startup                       # Enable auto-start on boot
```

### API Key Authentication

Protect your API with API keys (optional):

```bash
# .env - comma-separated list of valid keys
API_KEYS=key1,key2,key3

# Leave empty to disable authentication
API_KEYS=
```

**Usage:**
```bash
# Via header
curl -H "X-API-Key: your-key" https://your-server.com/reso/odata/Property

# Via query parameter
curl "https://your-server.com/reso/odata/Property?api_key=your-key"
```

### Apache Reverse Proxy (HTTPS)

Add to your Apache VirtualHost config for HTTPS access:

```apache
# RESO Web API - Proxy /reso to FastAPI on port 3900
RedirectMatch ^/reso$ /reso/
ProxyPass        /reso/ http://127.0.0.1:3900/
ProxyPassReverse /reso/ http://127.0.0.1:3900/
```

Then restart Apache:
```bash
sudo apachectl configtest && sudo systemctl restart apache2
```

API will be available at: `https://your-server.com/reso`

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info and available endpoints |
| `GET /health` | Health check with Databricks connection status |
| `GET /docs` | Interactive Swagger UI documentation |
| `GET /odata` | OData service document |
| `GET /odata/$metadata` | OData metadata (XML) |
| `GET /odata/Property` | RESO Property resource |
| `GET /odata/Member` | RESO Member resource |
| `GET /odata/Office` | RESO Office resource |
| `GET /odata/Media` | RESO Media resource |
| `GET /odata/Contacts` | RESO Contacts resource |
| `GET /odata/ShowingAppointment` | RESO ShowingAppointment resource |

### Quick Test

```bash
curl "https://your-server.com/reso/odata/Property?\$top=5"
```

### Frontend Integration

See **[Integration Guide](docs/integration-guide.md)** for OData queries, TypeScript types, and React examples.

## Directory Structure

```
mls_2_0/
├── .env.example                # Template for .env
├── ecosystem.config.js         # PM2 config for RESO Web API
├── api/                        # RESO Web API (FastAPI)
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration (loads from parent .env)
│   ├── requirements.txt        # Python dependencies
│   ├── routers/                # API route handlers
│   │   ├── property.py         # /odata/Property
│   │   ├── member.py           # /odata/Member
│   │   ├── office.py           # /odata/Office
│   │   ├── media.py            # /odata/Media
│   │   ├── contacts.py         # /odata/Contacts
│   │   ├── showing.py          # /odata/ShowingAppointment
│   │   └── metadata.py         # /odata/$metadata
│   ├── services/               # Business logic
│   │   ├── databricks.py       # Databricks SQL HTTP connector
│   │   └── odata_parser.py     # OData query to SQL translator
│   └── models/                 # Pydantic models
│       └── reso.py             # RESO resource schemas
├── docs/
│   ├── integration-guide.md    # Connect your real estate site to this API
│   ├── mapping.md              # Complete Qobrix → RESO field mapping
│   ├── qobrix_openapi.yaml     # Qobrix API OpenAPI spec (68k lines)
│   └── qobrix_api_docs.html    # API docs viewer
├── notebooks/
│   ├── 00_full_refresh_qobrix_bronze.py       # Bronze: Full refresh all Qobrix data
│   ├── 00a_cdc_qobrix_bronze.py               # Bronze: CDC incremental sync
│   ├── 02_silver_qobrix_property_etl.py       # Silver: Full refresh properties
│   ├── 02_cdc_silver_property_etl.py          # Silver: CDC incremental properties
│   ├── 02a_silver_qobrix_agent_etl.py         # Silver: Normalize agents + users
│   ├── 02b_silver_qobrix_contact_etl.py       # Silver: Normalize contacts
│   ├── 02c_silver_qobrix_media_etl.py         # Silver: Normalize media
│   ├── 02d_silver_qobrix_viewing_etl.py       # Silver: Normalize viewings
│   ├── 03_gold_reso_property_etl.py           # Gold: Full refresh RESO Property
│   ├── 03_cdc_gold_reso_property_etl.py       # Gold: CDC incremental RESO Property
│   ├── 03a_gold_reso_member_etl.py            # Gold: RESO Member (from silver.agent)
│   ├── 03b_gold_reso_office_etl.py            # Gold: RESO Office (from silver.agent)
│   ├── 03c_gold_reso_media_etl.py             # Gold: RESO Media (from silver.media)
│   ├── 03d_gold_reso_contacts_etl.py          # Gold: RESO Contacts (from silver.contact)
│   ├── 03e_gold_reso_showingappointment_etl.py # Gold: RESO ShowingAppointment
│   └── 10_verify_data_integrity_qobrix_vs_reso.py  # Integrity test
├── scripts/
│   ├── import_notebooks.sh     # Import notebooks to Databricks
│   ├── pm2-manage.sh           # PM2 management for RESO Web API
│   ├── run_pipeline.sh         # Run ETL pipeline via CLI
│   └── verify_data_integrity.sh # Local integrity test
```

## Configuration

All settings are stored in `.env` (copy from `.env.example`):

```bash
# 1. Qobrix API Credentials
QOBRIX_API_USER=<your-api-user-uuid>
QOBRIX_API_KEY=<your-api-key>
QOBRIX_API_BASE_URL=https://<your-instance>.qobrix.com/api/v2
QOBRIX_DEFAULT_CURRENCY=EUR

# 2. Databricks Workspace
DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-databricks-token>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<your-warehouse-id>
DATABRICKS_WAREHOUSE_ID=<your-warehouse-id>

# 3. RESO Web API Authentication (optional)
API_KEYS=key1,key2,key3  # Leave empty to disable auth

# 4. RESO Web API Server
RESO_API_HOST=0.0.0.0
RESO_API_PORT=3900
```

Copy `.env.example` to `.env` and fill in your values.

## Databricks Catalog Structure

Catalog: `mls2`

```
mls2 (catalog)
├── qobrix_bronze (schema) - 18 tables
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
│   ├── property_media      # Photos/documents/floorplans
│   └── cdc_metadata        # CDC sync tracking (timestamps, counts)
├── qobrix_silver (schema) - 5 tables
│   ├── property            # Normalized properties
│   ├── agent               # Normalized agents + users
│   ├── contact             # Normalized contacts
│   ├── media               # Normalized property media
│   └── viewing             # Normalized property viewings
└── reso_gold (schema) - 6 RESO resources
    ├── property            # RESO Property (48 standard + 129 extension fields)
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

**Additional RESO Standard Fields:**
| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `BathroomsHalf` | `wc_bathrooms` | INT (WC = half bath) |
| `LotSizeAcres` | `plot_area_amount` | `plot_area * 0.000247105` (m² → acres) |
| `LeaseAmountFrequency` | `rent_frequency` | monthly→Monthly, weekly→Weekly, etc. |
| `ListOfficeKey` | `agent` | `CONCAT('QOBRIX_OFFICE_', agent)` |
| `Flooring` | `flooring` | Direct mapping |
| `Fencing` | `fencing` | Direct mapping |
| `FireplaceFeatures` | `fireplace_features` | Direct mapping |
| `WaterfrontFeatures` | `waterfront_features` | Direct mapping |
| `PatioAndPorchFeatures` | `patio_porch` | Direct mapping |
| `OtherStructures` | `other_structures` | Direct mapping |
| `AssociationAmenities` | `association_amenities` | Direct mapping |

**Total: 48 RESO Standard Fields** mapped from Qobrix data (92% RESO coverage).

### Extension Fields (X_ prefix) - 129 Fields

Per RESO convention, vendor-specific fields use the `X_` prefix. These are Qobrix-specific attributes that don't have RESO equivalents:

| Category | Extension Fields |
|----------|-----------------|
| **Views (Regional)** | `X_SeaView`, `X_MountainView`, `X_BeachFront`, `X_AbutsGreenArea`, `X_ElevatedArea` |
| **Pool Details** | `X_PrivateSwimmingPool`, `X_CommonSwimmingPool` |
| **Property Features** | `X_Elevator`, `X_AirCondition`, `X_Alarm`, `X_SmartHome`, `X_SolarWaterHeater`, `X_ConciergeReception`, `X_SecureDoor`, `X_Kitchenette`, `X_HomeOffice`, `X_SeparateLaundryRoom` |
| **Building Details** | `X_ConstructionType`, `X_ConstructionStage`, `X_FloorType`, `X_NewBuild`, `X_Height`, `X_MaxFloor`, `X_UnitNumber` |
| **Energy Details** | `X_EnergyEfficiencyGrade`, `X_HeatingType`, `X_HeatingMedium`, `X_CoolingType`, `X_EnergyConsumptionRating`, `X_EnergyEmissionRating` |
| **Distances** | `X_DistanceFromBeach`, `X_DistanceFromAirport`, `X_DistanceFromCentre`, `X_DistanceFromSchool`, `X_DistanceFromRailStation`, `X_DistanceFromTubeStation` |
| **Room Details** | `X_LivingRooms`, `X_Kitchens`, `X_KitchenType`, `X_OfficeSpaces`, `X_VerandasCount`, `X_Reception`, `X_StoreRoom` |
| **Area Details** | `X_CoveredArea`, `X_UncoveredArea`, `X_TotalArea`, `X_GardenArea`, `X_RoofGardenArea`, `X_Frontage`, `X_MezzanineArea`, `X_StorageArea` |
| **Land Details** | `X_BuildingDensity`, `X_Coverage`, `X_CornerPlot`, `X_TownPlanningZone`, `X_LandLocked`, `X_CadastralReference` |
| **Commercial** | `X_IdealFor`, `X_LicensedFor`, `X_BusinessTransferOrSale`, `X_BusinessActivity`, `X_ConferenceRoom`, `X_ServerRoom`, `X_EnclosedOffice`, `X_OfficeLayout` |
| **Pricing Details** | `X_PricePerSquare`, `X_PriceQualifier`, `X_PlusVAT`, `X_MinimumTenancy`, `X_TenancyType`, `X_Occupancy` |
| **Price History** | `X_PreviousListPrice`, `X_PreviousLeasePrice`, `X_ListPriceModified`, `X_LeasePriceModified` |
| **Auction** | `X_AuctionStartDate`, `X_AuctionEndDate`, `X_ReservePrice`, `X_StartingBid` |
| **Property Subtypes** | `X_ApartmentType`, `X_HouseType`, `X_LandType`, `X_OfficeType`, `X_RetailType`, `X_IndustrialType`, `X_HotelType`, `X_BuildingType`, `X_InvestmentType` |
| **Marketing** | `X_Featured`, `X_PropertyOfTheMonth`, `X_VideoLink`, `X_VirtualTourLink`, `X_ShortDescription`, `X_PropertyName` |
| **Qobrix Metadata** | `X_QobrixId`, `X_QobrixRef`, `X_QobrixSource`, `X_QobrixCreated`, `X_QobrixModified`, `X_QobrixLegacyId`, `X_QobrixSellerId` |

**Total Gold Property Fields: 179** (48 RESO Standard + 129 Extensions + 2 ETL metadata)

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

### Full Refresh Jobs
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

### CDC Jobs (Incremental)
| Job | Name |
|-----|------|
| CDC Bronze | `MLS 2.0 - Qobrix CDC Bronze` |
| CDC Silver | `MLS 2.0 - Qobrix CDC Silver Property` |
| CDC Gold | `MLS 2.0 - RESO CDC Gold Property` |

## CDC (Change Data Capture)

### Overview

CDC enables incremental data sync instead of full refresh:

| Mode | When to Use | Time | API Calls |
|------|-------------|------|-----------|
| **Full Refresh** | Initial load, recovery, weekly | 10-15 min | 50+ |
| **CDC** | Regular sync (every 15-30 min) | 15-60 sec | 5-10 |

### CDC Commands

```bash
# Smart CDC - only runs Silver/Gold for changed entities
./scripts/run_pipeline.sh cdc

# Force all Silver/Gold ETLs regardless of changes
./scripts/run_pipeline.sh cdc-all

# Individual CDC stages
./scripts/run_pipeline.sh cdc-bronze   # Fetch changed records from API
./scripts/run_pipeline.sh cdc-silver   # Transform changed records
./scripts/run_pipeline.sh cdc-gold     # RESO transform changed records
```

**Smart CDC Output:**
```
📊 Checking which entities changed...
   Properties: 0 changed
   Agents: 0 changed
   Contacts: 0 changed
   Viewings: 0 changed
   Opportunities: 0 changed

✨ No changes detected - skipping Silver/Gold ETLs

⏱️  Total time: 1m 43s
```

### How It Works

1. **CDC Metadata Table** (`qobrix_bronze.cdc_metadata`)
   - Tracks last sync timestamp per entity
   - Records processed count and status
   - Enables reliable incremental sync

2. **Timestamp-Based Filtering**
   - Queries API: `GET /properties?search=modified>='2025-12-02 10:00:00'`
   - Only fetches records modified since last sync

3. **DELETE + INSERT Operations**
   - Uses DELETE + INSERT to handle schema evolution
   - Avoids schema mismatch issues with nested API fields
   - Preserves data integrity

### CDC Notebooks

| Notebook | Purpose |
|----------|---------|
| `00a_cdc_qobrix_bronze.py` | Incremental API fetch → bronze MERGE |
| `02_cdc_silver_property_etl.py` | Incremental silver transform |
| `03_cdc_gold_reso_property_etl.py` | Incremental gold RESO transform |

### Entity Sync Frequency

| Entity | CDC Method | Notes |
|--------|------------|-------|
| Properties | Incremental | High volume |
| Property Media | Incremental | For changed properties |
| Agents | Incremental | Low volume |
| Contacts | Incremental | Medium volume |
| Viewings | Incremental | Tied to properties |
| Opportunities | Incremental | Leads/inquiries |
| Users | Incremental | System users |
| Projects | Incremental | Developments |
| Lookups | Incremental | Types, subtypes, locations |
| Portal Locations | Skip (full refresh only) | No `modified` filter support |

### Soft Delete Handling

CDC detects trashed properties via `GET /properties?trashed=true` and updates their status in bronze.

### Recommended Schedule

```bash
# Cron examples
*/15 * * * *  ./scripts/run_pipeline.sh cdc   # Smart CDC every 15 min
0 0 * * 0     ./scripts/run_pipeline.sh all   # Weekly full refresh
```

---

## Next Steps

- [x] Add RESO Member resource (agents/users)
- [x] Add RESO Office resource (agencies)
- [x] Add RESO Media resource (photos/documents)
- [x] Add RESO Contacts resource (buyers/sellers)
- [x] Add RESO ShowingAppointment resource (property viewings)
- [x] Add Qobrix extension fields (X_ prefix) to Property
- [x] Map Qobrix fields to RESO standard names (hybrid approach)
- [x] Add Silver layer for all resources (agent, contact, media, viewing)
- [x] Implement CDC (incremental updates)
- [x] Scale to full data load

---

## Disclaimer

This project and all associated notebooks, workflows, and examples are designed to run on Databricks Free Edition and are provided solely for personal learning, academic coursework, and other not‑for‑profit, non‑commercial use cases that comply with the Databricks Free Edition terms. It must not be used for any production, commercial, revenue‑generating, or SLA‑backed workloads, including processing live MLS/CRM data for customers or operating customer‑facing applications. To use this project in any commercial or production context, you must migrate it to a paid Databricks workspace (or another appropriately licensed environment) and ensure that your usage complies with all applicable Databricks, cloud provider, and data source terms and conditions.
