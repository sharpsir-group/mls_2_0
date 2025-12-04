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
pip install databricks-cli
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
# Edit .env with your values
```

### 8. Import Notebooks & Run

```bash
./scripts/import_notebooks.sh
./scripts/run_pipeline.sh all
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `DIRECTORY_PROTECTED` error | Use `/Shared/` path (not `/Repos/`) |
| `INVALID_PARAMETER_VALUE` | Use multi-task format with `tasks` array |
| SQL Warehouse not starting | Check warehouse status, may need to wake up |

---

## Configuration

All settings are stored in `.env` (copy from `.env.example`):

```bash
# 1. Qobrix API
QOBRIX_API_USER=<your-api-user-uuid>
QOBRIX_API_KEY=<your-api-key>
QOBRIX_API_BASE_URL=https://<instance>.qobrix.com/api/v2
QOBRIX_DEFAULT_CURRENCY=EUR

# 2. Databricks
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-token>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
DATABRICKS_WAREHOUSE_ID=<warehouse-id>

# 3. RESO Web API Server
RESO_API_HOST=0.0.0.0
RESO_API_PORT=3900

# 4. OAuth 2.0 Authentication
OAUTH_CLIENT_ID=reso-client-xxx
OAUTH_CLIENT_SECRET=<secret>
OAUTH_JWT_SECRET=<secret>
OAUTH_TOKEN_EXPIRE_MINUTES=60
```

Generate OAuth secrets with: `openssl rand -hex 32`

---

## Quick Start

```bash
# Import notebooks to Databricks
./scripts/import_notebooks.sh

# Run full pipeline
./scripts/run_pipeline.sh all

# Or run individual steps
./scripts/run_pipeline.sh bronze         # Raw data from API
./scripts/run_pipeline.sh silver         # All silver tables
./scripts/run_pipeline.sh gold           # All RESO resources
./scripts/run_pipeline.sh cdc            # Smart incremental sync
./scripts/run_pipeline.sh integrity      # Integrity test
```

---

## RESO Web API

FastAPI-based RESO Data Dictionary 2.0 compliant OData API.

### PM2 Management

```bash
./scripts/pm2-manage.sh start     # Start API
./scripts/pm2-manage.sh stop      # Stop API
./scripts/pm2-manage.sh restart   # Restart API
./scripts/pm2-manage.sh status    # Show status
./scripts/pm2-manage.sh logs      # View logs
./scripts/pm2-manage.sh health    # Health check
./scripts/pm2-manage.sh setup     # Initial setup
```

### Apache Reverse Proxy (HTTPS)

```apache
RedirectMatch ^/reso$ /reso/
ProxyPass        /reso/ http://127.0.0.1:3900/
ProxyPassReverse /reso/ http://127.0.0.1:3900/
```

### Frontend Integration

See **[Integration Guide](docs/integration-guide.md)** for:
- OAuth 2.0 authentication
- OData query examples
- TypeScript types
- React examples

---

## Documentation

| Document | Description |
|----------|-------------|
| [Integration Guide](docs/integration-guide.md) | Connect your app to the RESO API |
| [Field Mapping](docs/mapping.md) | Qobrix → RESO field mapping |
| [Qobrix OpenAPI](docs/qobrix_openapi.yaml) | Qobrix API specification |

### External Resources
- [RESO Data Dictionary 2.0](https://ddwiki.reso.org/display/DDW20/)
- [OData 4.0 Specification](https://www.odata.org/documentation/)

---

## Directory Structure

```
mls_2_0/
├── .env.example                # Environment template
├── ecosystem.config.js         # PM2 config
├── api/                        # RESO Web API (FastAPI)
│   ├── main.py                 # Application entry
│   ├── config.py               # Settings from .env
│   ├── auth.py                 # OAuth 2.0 authentication
│   ├── routers/                # API endpoints
│   └── services/               # Business logic
├── docs/
│   ├── integration-guide.md    # Frontend integration
│   └── mapping.md              # Field mapping reference
├── notebooks/                  # Databricks ETL notebooks
│   ├── 00_full_refresh_*.py    # Full refresh ETLs
│   ├── 00a_cdc_*.py            # CDC incremental ETLs
│   ├── 02_silver_*.py          # Silver transforms
│   ├── 03_gold_*.py            # Gold RESO transforms
│   └── 10_verify_*.py          # Integrity tests
└── scripts/
    ├── import_notebooks.sh     # Import to Databricks
    ├── pm2-manage.sh           # API management
    └── run_pipeline.sh         # ETL orchestration
```

---

## Databricks Catalog Structure

```
mls2 (catalog)
├── qobrix_bronze (17 tables)
│   ├── properties, agents, contacts, users
│   ├── property_media, property_viewings, opportunities
│   ├── projects, project_features
│   ├── property_types, property_subtypes, locations
│   ├── media_categories, cdc_metadata
│   └── portal_locations (bayut, bazaraki, spitogatos, property_finder)
├── qobrix_silver (5 tables)
│   ├── property, agent, contact, media, viewing
└── reso_gold (6 RESO resources)
    ├── property, member, office
    ├── media, contacts, showing_appointment
```

---

## RESO Resources

| Resource | Source | RESO Wiki |
|----------|--------|-----------|
| Property | properties | [Property](https://ddwiki.reso.org/display/DDW20/Property+Resource) |
| Member | agents + users | [Member](https://ddwiki.reso.org/display/DDW20/Member+Resource) |
| Office | agents (agencies) | [Office](https://ddwiki.reso.org/display/DDW20/Office+Resource) |
| Media | property_media | [Media](https://ddwiki.reso.org/display/DDW20/Media+Resource) |
| Contacts | contacts | [Contacts](https://ddwiki.reso.org/display/DDW20/Contacts+Resource) |
| ShowingAppointment | property_viewings | [ShowingAppointment](https://ddwiki.reso.org/display/DDW20/ShowingAppointment+Resource) |

**Property Fields:** 48 RESO Standard + 129 Extensions (X_ prefix)

See [Field Mapping](docs/mapping.md) for complete mapping reference.

---

## Pipeline Flow

```
Qobrix API → Bronze (raw) → Silver (normalized) → Gold (RESO) → Web API
```

| Layer | Tables | Description |
|-------|--------|-------------|
| Bronze | 17 | Raw API data, all STRING columns |
| Silver | 5 | Normalized, typed, cleaned |
| Gold | 6 | RESO Data Dictionary compliant |

---

## CDC (Change Data Capture)

Smart incremental sync instead of full refresh:

```bash
# Smart CDC - only processes changed entities
./scripts/run_pipeline.sh cdc

# Force all ETLs regardless of changes
./scripts/run_pipeline.sh cdc-all
```

| Mode | Use Case | Time | API Calls |
|------|----------|------|-----------|
| Full Refresh | Initial load, weekly | 10-15 min | 50+ |
| CDC | Regular sync (15-30 min) | 15-60 sec | 5-10 |

### Recommended Schedule

```bash
*/15 * * * *  ./scripts/run_pipeline.sh cdc   # Every 15 min
0 0 * * 0     ./scripts/run_pipeline.sh all   # Weekly full refresh
```

---

## Completed

- [x] RESO Property, Member, Office, Media, Contacts, ShowingAppointment
- [x] Silver layer (property, agent, contact, media, viewing)
- [x] RESO standard field mapping (48 fields)
- [x] Extension fields (129 X_ prefix fields)
- [x] CDC incremental sync
- [x] OAuth 2.0 authentication
- [x] Full data load

---

## Disclaimer

This project is designed for Databricks Free Edition and provided for personal learning and non-commercial use only. For production use, migrate to a paid Databricks workspace.
