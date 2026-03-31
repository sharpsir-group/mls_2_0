<p align="center">
  <a href="https://sharpsir.group">
    <img src="https://raw.githubusercontent.com/sharpsir-group/.github/main/brand/logo-blue.png" alt="Sharp Sotheby's International Realty" width="400" />
  </a>
</p>

<h3 align="center">MLS 2.0 Pipeline</h3>

<p align="center">
  Multi-source ETL pipeline on Databricks with a RESO DD 2.0 compliant OData Web API.<br />
  Ingests property data from Qobrix CRM, DASH/Anywhere.com, and MLS feeds into a unified gold layer.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Databricks-FF3621?style=flat&logo=databricks&logoColor=white" alt="Databricks" />
  <img src="https://img.shields.io/badge/Delta_Lake-003366?style=flat&logo=delta&logoColor=white" alt="Delta Lake" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/RESO_DD_2.0-1A1A2E?style=flat&logoColor=white" alt="RESO" />
  <img src="https://img.shields.io/badge/OData_4.0-0078D4?style=flat&logo=odata&logoColor=white" alt="OData" />
  <img src="https://img.shields.io/badge/OAuth_2.0-EB5424?style=flat&logo=auth0&logoColor=white" alt="OAuth" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/PM2-2B037A?style=flat&logo=pm2&logoColor=white" alt="PM2" />
  <img src="https://img.shields.io/badge/Apache-D22128?style=flat&logo=apache&logoColor=white" alt="Apache" />
</p>

---

### Pipeline Architecture

```
Source 1:  Qobrix API  → qobrix_bronze → qobrix_silver ─┐
Source 2:  DASH FILE   → dash_bronze   → dash_silver    ─┤→ reso_gold → RESO Web API
Source 3:  DASH API    → dash_bronze   → dash_silver    ─┘            → exports (XML)
```

| Layer | Tables | Description |
|---|---|---|
| **Bronze** | 17+ | Raw API/file data, all STRING columns |
| **Silver** | 8 | Normalized, typed, cleaned |
| **Gold** | 6 | RESO Data Dictionary 2.0 compliant (all sources merged) |
| **Exports** | 1 | Portal feed data (XML) |

### Data Sources

| Source | Method | Script |
|---|---|---|
| Qobrix API | CDC (incremental via `modified` filter) | `run_pipeline.sh cdc` |
| DASH FILE | File sync (FTP/local directory) | `load_dash_bronze.py` |
| DASH API | Full sync (API pull) | `fetch_dash_api.py` |

### Quick Start

```bash
# Clone
git clone https://github.com/sharpsir-group/mls_2_0.git
cd mls_2_0

# Configure
cp .env.example .env
# Edit .env with your Databricks, Qobrix, and OAuth credentials

# Import notebooks to Databricks
./scripts/import_notebooks.sh

# Run full pipeline (initial load)
./scripts/run_pipeline.sh all

# Smart incremental sync (daily)
./scripts/run_pipeline.sh cdc
```

### Configuration

All settings are stored in `.env` (copy from `.env.example`):

```bash
# Qobrix API (primary CRM source)
QOBRIX_API_USER=<your-api-user-uuid>
QOBRIX_API_KEY=<your-api-key>
QOBRIX_API_BASE_URL=https://<instance>.qobrix.com/api/v2

# Databricks
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-token>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
DATABRICKS_CATALOG=mls_2_0

# Multi-source office keys
SRC_1_OFFICE_KEY=<your-office-key-1>
SRC_2_OFFICE_KEY=<your-office-key-2>
SRC_3_OFFICE_KEY=<your-office-key-3>

# RESO Web API Server
RESO_API_HOST=0.0.0.0
RESO_API_PORT=3900

# OAuth 2.0
OAUTH_CLIENT_ID=reso-client-xxx
OAUTH_CLIENT_SECRET=<secret>
OAUTH_JWT_SECRET=<secret>
```

Generate OAuth secrets with: `openssl rand -hex 32`

### Pipeline Commands

#### Full Refresh

```bash
./scripts/run_pipeline.sh bronze           # Raw data from Qobrix API
./scripts/run_pipeline.sh silver           # All silver tables
./scripts/run_pipeline.sh gold             # All RESO gold tables
./scripts/run_pipeline.sh all              # Full pipeline (bronze → silver → gold → integrity)
./scripts/run_pipeline.sh integrity        # Data integrity verification
```

#### CDC — Incremental Sync

```bash
./scripts/run_pipeline.sh cdc             # Smart CDC (recommended for daily use)
./scripts/run_pipeline.sh cdc-catchup     # Reset metadata + full re-fetch (recovery)
./scripts/run_pipeline.sh cdc-all         # Force all entities through CDC pipeline
./scripts/run_pipeline.sh cdc-bronze      # CDC bronze only
./scripts/run_pipeline.sh cdc-silver      # CDC silver property only
./scripts/run_pipeline.sh cdc-gold        # CDC gold (property + contacts)
```

#### Exports

```bash
./scripts/run_pipeline.sh export-homesoverseas   # XML feed for portal export
```

### CDC (Change Data Capture)

The CDC pipeline uses `cdc_metadata` in `qobrix_bronze` to track the last successful sync timestamp per entity. On each run it fetches only records modified since that timestamp.

| Scenario | Behavior |
|---|---|
| **Normal daily run** | Fetches changes since last sync (minutes to seconds) |
| **First run / empty catalog** | No metadata → defaults to `2020-01-01` → fetches ALL records |
| **Missed several days** | Picks up from last successful sync timestamp (self-healing) |
| **Table corruption** | Run `cdc-catchup` to reset metadata and re-fetch everything |

#### Cron Schedule

```bash
# All Sources CDC — daily
0 0 * * * /path/to/mls_2_0/scripts/cron_all_sources_cdc.sh >> /path/to/mls_2_0/logs/cron.log 2>&1
```

The cron script orchestrates all sources sequentially:
1. **Source 1** — Qobrix CDC via Databricks notebooks
2. **Source 2** — DASH API fetch
3. **Source 3** — DASH file sync
4. **API integration tests** — verify data integrity
5. **Email report** — HTML summary sent via Resend API

### RESO Web API

FastAPI-based RESO Data Dictionary 2.0 compliant OData API.

#### PM2 Management

```bash
./scripts/pm2-manage.sh start     # Start API
./scripts/pm2-manage.sh stop      # Stop API
./scripts/pm2-manage.sh restart   # Restart API
./scripts/pm2-manage.sh status    # Show status
./scripts/pm2-manage.sh logs      # View logs
./scripts/pm2-manage.sh health    # Health check
```

#### Apache Reverse Proxy

```apache
RedirectMatch ^/reso$ /reso/
ProxyPass        /reso/ http://127.0.0.1:3900/
ProxyPassReverse /reso/ http://127.0.0.1:3900/
```

### RESO Resources

| Resource | Source | RESO Wiki |
|---|---|---|
| Property | qobrix properties + dash properties | [Property](https://ddwiki.reso.org/display/DDW20/Property+Resource) |
| Member | agents + users | [Member](https://ddwiki.reso.org/display/DDW20/Member+Resource) |
| Office | agents (agencies) | [Office](https://ddwiki.reso.org/display/DDW20/Office+Resource) |
| Media | property_media | [Media](https://ddwiki.reso.org/display/DDW20/Media+Resource) |
| Contacts | contacts | [Contacts](https://ddwiki.reso.org/display/DDW20/Contacts+Resource) |
| ShowingAppointment | property_viewings | [ShowingAppointment](https://ddwiki.reso.org/display/DDW20/ShowingAppointment+Resource) |

**Property Fields:** 48 RESO Standard + 129 Extensions (X_ prefix). See [Field Mapping](docs/mapping.md) for the complete reference.

### Databricks Catalog Structure

Unity Catalog: **`mls_2_0`**

```
mls_2_0 (catalog)
├── qobrix_bronze (17+ tables)
│   ├── properties, agents, contacts, users
│   ├── property_media, property_viewings, opportunities
│   ├── projects, project_features
│   ├── property_types, property_subtypes, locations
│   ├── media_categories, property_translations_ru
│   ├── cdc_metadata (sync tracking)
│   └── portal_locations (bayut, bazaraki, spitogatos, property_finder)
├── qobrix_silver (5 tables)
│   ├── properties, agents, contacts, media, viewings
├── dash_bronze
│   └── properties
├── dash_silver
│   ├── properties, media, features
├── reso_gold (6 RESO resources)
│   ├── property, member, office
│   ├── media, contacts, showing_appointment
└── exports
    └── homesoverseas (XML feed data)
```

### Documentation

| Document | Description |
|---|---|
| [Integration Guide](docs/integration-guide.md) | Connect your app to the RESO API |
| [Field Mapping](docs/mapping.md) | Qobrix → RESO field mapping |
| [Sync Client (TS)](docs/sync-client-example.ts) | TypeScript MLS sync client example |
| [Sync Client (JS)](docs/sync-client-example.js) | Vanilla JS MLS sync client example |
| [Qobrix OpenAPI](docs/qobrix_openapi.yaml) | Qobrix API specification |

### External Resources

- [RESO Data Dictionary 2.0](https://ddwiki.reso.org/display/DDW20/)
- [OData 4.0 Specification](https://www.odata.org/documentation/)
- [Databricks Documentation](https://docs.databricks.com/)

### Databricks Setup

<details>
<summary>Expand for full Databricks setup instructions</summary>

#### 1. Create Databricks Account

1. Go to https://www.databricks.com/try-databricks
2. Click **"Get started for free"**
3. Sign up with email or Google/Microsoft account
4. Select **Community Edition** (free) or trial workspace
5. Choose a cloud provider region (recommend **EU** for GDPR compliance)

#### 2. Create SQL Warehouse

1. Go to **SQL** → **SQL Warehouses**
2. Click **Create SQL Warehouse**
3. Name it (e.g., `mls2-warehouse`)
4. Select **Serverless** (recommended) or smallest size
5. Note the **HTTP Path** from warehouse settings

#### 3. Create Unity Catalog

1. Go to **Catalog** → **Create Catalog** (or run [init_uc_catalog_mls_2_0.sql](scripts/sql/init_uc_catalog_mls_2_0.sql))
2. Name: **`mls_2_0`**
3. Schemas are created by the SQL script or by notebooks on first run

#### 4. Generate Access Token

1. Click username → **User Settings** → **Developer** → **Access tokens**
2. Click **Generate new token** (lifetime: 90 days)
3. Copy the token immediately

#### 5. Install & Configure CLI

```bash
pip install databricks-cli
databricks configure --token
```

#### 6. Import & Run

```bash
./scripts/import_notebooks.sh
./scripts/run_pipeline.sh all
```

#### Troubleshooting

| Issue | Solution |
|---|---|
| `DIRECTORY_PROTECTED` error | Use `/Shared/` path (not `/Repos/`) |
| `INVALID_PARAMETER_VALUE` | Use multi-task format with `tasks` array |
| SQL Warehouse not starting | Check warehouse status, may need to wake up |
| `No such command 'submit'` | Requires legacy databricks-cli (v0.18) |

</details>

### SSL/HTTPS Setup

<details>
<summary>Expand for SSL configuration</summary>

```bash
# Obtain Let's Encrypt certificate
sudo CERTBOT_EMAIL=your@email.com ./scripts/setup-ssl.sh

# Add to .env (setup-ssl.sh does this automatically):
# SSL_CERT_FILE=/etc/letsencrypt/live/<your-domain>/fullchain.pem
# SSL_KEY_FILE=/etc/letsencrypt/live/<your-domain>/privkey.pem

# Restart API
./scripts/pm2-manage.sh restart
```

</details>

### Directory Structure

```
mls_2_0/
├── .env.example                    # Environment template
├── ecosystem.config.js             # PM2 config
├── api/                            # RESO Web API (FastAPI)
│   ├── main.py                     # Application entry
│   ├── config.py                   # Settings from .env
│   ├── auth.py                     # OAuth 2.0 authentication
│   ├── routers/                    # API endpoints
│   └── services/                   # Business logic
├── docs/
│   ├── integration-guide.md        # Frontend integration
│   ├── mapping.md                  # Field mapping reference
│   └── qobrix_openapi.yaml        # Qobrix API spec
├── notebooks/                      # Databricks ETL notebooks
│   ├── 00_full_refresh_*.py        # Full refresh bronze
│   ├── 00a_cdc_*.py                # CDC incremental bronze
│   ├── 01_dash_silver_*.py         # DASH silver transforms
│   ├── 02_silver_*.py              # Qobrix silver transforms
│   ├── 02_cdc_silver_*.py          # CDC silver transforms
│   ├── 03_gold_*.py                # Gold RESO transforms
│   ├── 03_cdc_gold_*.py            # CDC gold transforms
│   ├── 04a_export_*.py             # Export feeds
│   └── 10_verify_*.py              # Integrity tests
├── scripts/
│   ├── sql/                        # UC bootstrap, CDC helper SQL
│   ├── cron_all_sources_cdc.sh     # Multi-source cron orchestrator
│   ├── fetch_dash_api.py           # DASH API fetcher
│   ├── load_dash_bronze.py         # DASH file loader
│   ├── import_notebooks.sh         # Import to Databricks
│   ├── pm2-manage.sh               # API management
│   ├── run_pipeline.sh             # ETL orchestration
│   ├── verify_api_integrity.sh     # Qobrix ↔ RESO API verification
│   └── verify_dash_api_integrity.sh
└── logs/                           # CDC run logs (auto-created)
```

---

<p align="center">
  <sub>Part of the <a href="https://github.com/sharpsir-group"><strong>Sharp Matrix</strong></a> platform · <a href="https://sharpsir.group">sharpsir.group</a></sub>
</p>
