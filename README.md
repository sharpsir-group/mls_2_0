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

> **Requirement:** Databricks CLI **>= 0.298** (the unified `databricks jobs
> {submit,get-run,get-run-output}` verbs replaced the removed `databricks runs ...`
> subcommands). `scripts/run_pipeline.sh` exits with an explicit error if a
> lower version is detected. Install via:
> `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh`

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
# Databricks
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-token>
DATABRICKS_WAREHOUSE_ID=<your-warehouse-id>
DATABRICKS_CATALOG=mls2

# Data sources (SRC_1 = Qobrix API, SRC_2 = DASH file, SRC_3 = DASH API)
SRC_1_OFFICE_KEY=SHARPSIR-CY-001
SRC_1_API_USER=<your-qobrix-api-user-uuid>
SRC_1_API_KEY=<your-qobrix-api-key>
SRC_1_API_URL=https://<instance>.qobrix.com/api/v2

# RESO Web API Server
RESO_API_HOST=0.0.0.0
RESO_API_PORT=3900

# OAuth 2.0 (numbered clients, one per office)
OAUTH_JWT_SECRET=<secret>
OAUTH_CLIENT_1_ID=reso-client-xxx
OAUTH_CLIENT_1_SECRET=<secret>
OAUTH_CLIENT_1_OFFICES=SHARPSIR-CY-001
```

Generate OAuth secrets with: `openssl rand -hex 32`

### Pipeline Commands

#### Full Refresh

```bash
./scripts/run_pipeline.sh bronze           # Raw data from Qobrix API
./scripts/run_pipeline.sh silver           # All Qobrix silver tables
./scripts/run_pipeline.sh silver-dash      # DASH silver tables (property, property_features, media)
./scripts/run_pipeline.sh gold             # All RESO gold tables
./scripts/run_pipeline.sh all              # Full pipeline (bronze → silver → gold → integrity)
./scripts/run_pipeline.sh integrity        # Data integrity verification
```

#### CDC — Incremental Sync

```bash
./scripts/run_pipeline.sh cdc             # Full incremental sync (Bronze CDC → Qobrix Silver → DASH Silver → Gold → Exports)
./scripts/run_pipeline.sh cdc-bronze      # CDC bronze only
./scripts/run_pipeline.sh silver-dash     # Manually rebuild dash_silver.{property, property_features, media}
./scripts/run_pipeline.sh cdc-catchup     # Reset metadata → next CDC must self-recover (use only when bronze tables are corrupt)
```

> **Heads-up on `cdc-catchup`:** clears `qobrix_bronze.cdc_metadata` so the
> next `cdc` run is forced to fetch ALL records via the
> "no last_sync → full refresh" code path in
> `00a_cdc_qobrix_bronze.py::get_last_sync()`. Snapshot
> `qobrix_bronze.cdc_metadata` first if you may need to roll back.

#### Exports

```bash
./scripts/run_pipeline.sh export-homesoverseas   # XML feed for portal export
```

### CDC (Change Data Capture)

The CDC pipeline uses `cdc_metadata` in `qobrix_bronze` to track the last successful sync timestamp per entity. On each run it fetches only records modified since that timestamp.

| Scenario | Behavior |
|---|---|
| **Normal daily run** | Fetches changes since last sync (minutes to seconds) |
| **First run / empty catalog** | Self-recovery: delegates to full refresh notebook, seeds `cdc_metadata`, sends notification email |
| **Missed several days** | Picks up from last successful sync timestamp (self-healing) |
| **Table corruption** | Run `cdc-catchup` to reset metadata → next CDC auto-recovers via full refresh |

#### Cron Schedule

```bash
# All Sources CDC — daily
0 0 * * * /path/to/mls_2_0/scripts/cron_all_sources_cdc.sh >> /path/to/mls_2_0/logs/cron.log 2>&1
```

The cron script orchestrates all sources sequentially:
1. **Source 1** — Qobrix CDC via Databricks notebooks (incl. DASH silver as Stage 2b inside the cdc workflow, so HU/KZ rows reach `reso_gold.{property,media}`)
2. **Source 2** — DASH API fetch
3. **Source 3** — DASH file sync
4. **API integration tests** — verify data integrity
5. **Email report** — HTML summary sent via Resend API

The cron script's status banner (`✅ SUCCESS` / `⚠️ WARNING` / `❌ FAILED`) is
now driven by `OVERALL_STATUS` and the script exits non-zero when any critical
source fails; the previous behaviour was a hardcoded green banner + `exit 0`
that masked failures from log-greppers and external watchdogs.

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

Unity Catalog: **`mls2`**

```
mls2 (catalog)
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
2. Name: **`mls2`**
3. Schemas are created by the SQL script or by notebooks on first run

#### 4. Generate Access Token

1. Click username → **User Settings** → **Developer** → **Access tokens**
2. Click **Generate new token** (lifetime: 90 days)
3. Copy the token immediately

#### 5. Install & Configure CLI

> **The legacy `databricks-cli` PyPI package is unsupported.** The current
> Databricks CLI is a Go binary (>= 0.205); `scripts/run_pipeline.sh` requires
> >= 0.298 because it uses the unified `databricks jobs {submit,get-run,
> get-run-output}` verbs.

```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks --version            # must report >= 0.298
databricks configure --token    # paste host + token from step 4
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
| `unknown command "runs"` | CLI >= 0.205 unifies `runs *` under `jobs *`. Update the script (already done in this repo) and ensure CLI >= 0.298 |
| `Error: timed out:` from `databricks jobs submit` | Submit blocks until TERMINATED with a hidden ~20m timeout; long-running notebooks need `databricks jobs submit --no-wait ...` (already wired in `run_pipeline.sh`) |
| `unknown flag: --run-id` | CLI >= 0.205 takes RUN_ID as a positional arg: `databricks jobs get-run RUN_ID` (no flag) |

</details>

### Deploying a New Instance (Production Clone)

<details>
<summary>Expand for full deployment guide</summary>

This section covers how to set up a new MLS 2.0 instance (e.g., production) that is an exact copy of an existing one (e.g., dev).

#### Prerequisites

- Linux VM with Python 3.9+, Git, Apache
- SSH access configured (`~/.ssh/config`)
- A separate Databricks workspace (target)
- Databricks SQL Warehouse in the target workspace

#### Step 1: Clone the Repository

```bash
ssh your-server
cd /home/bitnami
git clone https://github.com/sharpsir-group/mls_2_0.git
cd mls_2_0
```

#### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with the **target** workspace credentials:

```bash
# Target Databricks workspace
DATABRICKS_HOST=https://dbc-XXXX.cloud.databricks.com
DATABRICKS_TOKEN=<target-workspace-token>
DATABRICKS_WAREHOUSE_ID=<target-warehouse-id>
DATABRICKS_CATALOG=mls2

# Source workspace (for cloning data)
CLONE_SOURCE_HOST=https://dbc-YYYY.cloud.databricks.com
CLONE_SOURCE_TOKEN=<source-workspace-token>
CLONE_SOURCE_WAREHOUSE_ID=<source-warehouse-id>
CLONE_SOURCE_CATALOG=mls2
```

Copy remaining credentials (Qobrix, OAuth, Resend) from the source `.env`.

#### Step 3: Initialize Databricks Catalog

```bash
# Install Databricks CLI
pip3 install --user databricks-cli
export PATH="$HOME/.local/bin:$PATH"

# Import notebooks
./scripts/import_notebooks.sh

# Create Unity Catalog structure
databricks sql execute --sql "$(cat scripts/sql/init_uc_catalog_mls_2_0.sql)"
```

#### Step 4: Load Data

**Option A — Full pipeline (recommended):** Run the ETL from scratch if the target has API access to data sources:

```bash
./scripts/run_pipeline.sh all
```

**Option B — Clone from source workspace (experimental):** Use only when the target cannot reach the data sources directly:

```bash
# Full clone — all tables (bronze, silver, gold, exports)
python3 scripts/clone_workspace.py

# Resume if interrupted (retries only failed/mismatched tables)
python3 scripts/clone_workspace.py --resume

# Verify row counts match
python3 scripts/clone_workspace.py --verify-only

# Clone specific tables only
python3 scripts/clone_workspace.py --tables qobrix_bronze.properties,exports.homesoverseas
```

The clone script reads data via Databricks SQL Statements API with `EXTERNAL_LINKS` disposition (no 25 MiB limit), uploads in batches, and uses `ORDER BY` on the first column for deterministic pagination across Delta Lake table versions.

#### Step 5: Install Node.js and PM2

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc

# Install Node.js and PM2
nvm install 20
npm install -g pm2

# Enable PM2 auto-startup
pm2 startup systemd -u bitnami --hp /home/bitnami
# Run the sudo command it outputs, then:
pm2 save
```

#### Step 6: Start the RESO Web API

```bash
./scripts/pm2-manage.sh setup    # Create venv, install deps
./scripts/pm2-manage.sh start    # Start API via PM2
./scripts/pm2-manage.sh health   # Verify health endpoint
```

#### Step 7: Configure Apache Reverse Proxy

Create `/opt/bitnami/apache/conf/vhosts/mls-sharpsir.conf`:

```apache
<VirtualHost *:80>
    ServerName mls.your-domain.com

    Alias /.well-known/acme-challenge/ /opt/bitnami/apache/htdocs/mls-acme/.well-known/acme-challenge/
    <Directory "/opt/bitnami/apache/htdocs/mls-acme/.well-known/acme-challenge/">
        Options None
        AllowOverride None
        Require all granted
    </Directory>

    RewriteEngine On
    RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName mls.your-domain.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/mls.your-domain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/mls.your-domain.com/privkey.pem

    ProxyPreserveHost On
    RedirectMatch ^/reso$ /reso/
    ProxyPass        /reso/ http://127.0.0.1:3900/
    ProxyPassReverse /reso/ http://127.0.0.1:3900/

    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
</VirtualHost>
```

```bash
sudo mkdir -p /opt/bitnami/apache/htdocs/mls-acme
sudo /opt/bitnami/ctlscript.sh restart apache
```

#### Step 8: SSL Certificate

```bash
sudo certbot certonly --webroot \
  -w /opt/bitnami/apache/htdocs/mls-acme \
  -d mls.your-domain.com

sudo /opt/bitnami/ctlscript.sh restart apache
```

#### Step 9: Set Up Cron (CDC)

```bash
crontab -e
```

Add (offset by 1 hour from source if both run daily):

```bash
# MLS 2.0 All Sources CDC - Daily at 4:00 AM MSK (1:00 UTC)
0 1 * * * /home/bitnami/mls_2_0/scripts/cron_all_sources_cdc.sh >> /home/bitnami/mls_2_0/logs/cron.log 2>&1
```

#### Step 10: Verify

```bash
# API health
curl -s https://mls.your-domain.com/reso/health | python3 -m json.tool

# HomeOverseas feed
curl -sI https://mls.your-domain.com/reso/export/homesoverseas.xml

# PM2 status
pm2 status
```

</details>

### Cloning Data Between Workspaces

> **Experimental** — The clone tool works but has known limitations with large Delta tables. Prefer running a full pipeline (`run_pipeline.sh all`) on the target workspace when possible. Use cloning only when the target has no direct API access to the data sources.

<details>
<summary>Expand for clone tool reference</summary>

The `scripts/clone_workspace.py` tool replicates all tables from one Databricks workspace to another via the SQL Statements API.

#### How It Works

1. Lists all schemas and tables in the source catalog
2. For each table: reads schema, drops and recreates the target table, then copies data in batches
3. Uses `EXTERNAL_LINKS` disposition to bypass the 25 MiB result size limit
4. Applies `ORDER BY` on the first column for deterministic pagination (critical for Delta tables with update history)
5. Preserves UTF-8 / Cyrillic content via `ensure_ascii=False` encoding

#### Environment Variables

```bash
# Source (clone FROM)
CLONE_SOURCE_HOST=https://dbc-XXXX.cloud.databricks.com
CLONE_SOURCE_TOKEN=<token>
CLONE_SOURCE_WAREHOUSE_ID=<warehouse-id>
CLONE_SOURCE_CATALOG=mls2

# Target (clone INTO) — uses standard DATABRICKS_* vars
DATABRICKS_HOST=https://dbc-YYYY.cloud.databricks.com
DATABRICKS_TOKEN=<token>
DATABRICKS_WAREHOUSE_ID=<warehouse-id>
DATABRICKS_CATALOG=mls2
```

#### Commands

```bash
python3 scripts/clone_workspace.py                 # Full clone (all tables)
python3 scripts/clone_workspace.py --resume         # Retry failed/mismatched only
python3 scripts/clone_workspace.py --verify-only    # Compare row counts (no writes)
python3 scripts/clone_workspace.py --bronze-only    # Clone bronze, regenerate derived
python3 scripts/clone_workspace.py --tables t1,t2   # Clone specific tables
```

#### Known Issues

- Delta tables with heavy update history may have stale row versions in physical files. The `ORDER BY` clause in `read_batch` ensures consistent reads.
- `VACUUM RETAIN 0 HOURS` is blocked on Serverless SQL Warehouses (168h minimum). Stale files self-clean after 7 days.
- If `id_map` tables have duplicates after cloning, re-clone them — duplicates cause row multiplication in downstream ETL joins.

</details>

### Management & Operations

<details>
<summary>Expand for day-to-day management</summary>

#### Checking Pipeline Status

```bash
# Today's CDC log
tail -f ~/mls_2_0/logs/all_sources_cdc_$(date +%Y-%m-%d).log

# Latest cron output
tail -50 ~/mls_2_0/logs/cron.log

# Check if CDC is currently running
ps aux | grep cron_all_sources | grep -v grep
```

#### API Management

```bash
pm2 status                        # Quick status
pm2 logs reso-web-api --lines 50  # Recent logs
pm2 restart reso-web-api          # Restart API
pm2 monit                         # Live monitoring dashboard
```

#### Running Pipeline Steps Manually

```bash
# Re-run a specific ETL stage
./scripts/run_pipeline.sh gold              # Regenerate all gold tables
./scripts/run_pipeline.sh export-homesoverseas  # Regenerate XML feed

# Re-run CDC for Cyprus only
./scripts/run_pipeline.sh cdc

# Re-fetch Kazakhstan data
python3 scripts/fetch_dash_api.py --source SHARPSIR-KZ-001
```

#### Email Notifications

All pipeline notifications (CDC completion, full refresh completion, recovery alerts) use the same branded HTML template via `scripts/send_email.py` and the Resend API. Configure in `.env`:

```bash
RESEND_API_KEY=re_your_key_here
RESEND_EMAIL_FROM="MLS Pipeline <noreply@humaticai.com>"
RESEND_EMAIL_TO=user1@example.com,user2@example.com
```

If `RESEND_EMAIL_TO` or `RESEND_API_KEY` is empty, email sending is silently skipped.

Email statuses: **SUCCESS** (green), **WARNING** (amber), **FAILED** (red), **RECOVERY** (orange).

</details>

### Troubleshooting

<details>
<summary>Expand for common issues and solutions</summary>

#### Pipeline Issues

| Issue | Diagnosis | Solution |
|---|---|---|
| CDC log stuck on one step | `ps aux \| grep fetch_dash` — check if subprocess alive | Wait (KZ fetch processes 3000+ listings ~2h) or check network |
| CDC not running | `crontab -l` — verify cron entry exists | Re-add cron entry (see Cron Schedule section) |
| No email after CDC | Check `RESEND_API_KEY` and `RESEND_EMAIL_TO` in `.env` | Must be non-empty for emails to send |
| `databricks: command not found` | CLI not in PATH | `pip3 install --user databricks-cli` and add `~/.local/bin` to PATH |
| Notebook run fails `DIRECTORY_PROTECTED` | Notebooks imported to wrong path | Use `/Shared/mls_2_0` path, not `/Repos/` |
| Row count mismatch after clone | Duplicate entries in `id_map` tables | Re-clone the affected `id_map` table |

#### API Issues

| Issue | Diagnosis | Solution |
|---|---|---|
| API returns 502/503 | `pm2 status` — check if process is online | `pm2 restart reso-web-api` |
| API not starting | `pm2 logs reso-web-api` — check error | Usually `.env` syntax error (unquoted special chars) |
| SSL certificate expired | `sudo certbot certificates` | `sudo certbot renew` (check webroot path in renewal config) |
| Let's Encrypt renewal fails | HTTP redirect blocks ACME challenge | Ensure Apache vhost has `Alias` for `/.well-known/acme-challenge/` before `RewriteRule` |
| Health check fails | `curl http://127.0.0.1:3900/health` | Check if port 3900 is occupied, verify `.env` settings |

#### Databricks Issues

| Issue | Diagnosis | Solution |
|---|---|---|
| SQL Warehouse not responding | Check warehouse status in Databricks UI | May need to manually start (auto-sleep after inactivity) |
| `TABLE_OR_VIEW_NOT_FOUND` | Missing catalog/schema | Run `init_uc_catalog_mls_2_0.sql` or `./scripts/run_pipeline.sh all` |
| Clone shows 0 rows for a table | Delta pagination without ORDER BY | Already fixed in `clone_workspace.py`; re-clone the table |
| `VACUUM` fails with retention error | Serverless warehouse blocks < 168h | Use default retention; files self-clean after 7 days |
| Token expired | 90-day token lifetime | Generate new token in Databricks UI → User Settings → Access Tokens |

#### Server Issues

| Issue | Diagnosis | Solution |
|---|---|---|
| Apache not starting | `sudo /opt/bitnami/ctlscript.sh status` | Check vhost syntax: `apachectl configtest` |
| PM2 not starting on boot | `pm2 startup` not configured | Run `pm2 startup systemd -u bitnami --hp /home/bitnami`, execute sudo command, then `pm2 save` |
| Disk space low | `df -h` | Clean old logs: `ls ~/mls_2_0/logs/` (safe to remove old `.log` files) |

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
│   ├── 03_gold_*.py                # Gold RESO transforms
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
│   ├── send_email.py               # Branded email sender (Resend API)
│   ├── verify_api_integrity.sh     # Qobrix ↔ RESO API verification
│   └── verify_dash_api_integrity.sh
└── logs/                           # CDC run logs (auto-created)
```

---

<p align="center">
  <sub>Part of the <a href="https://github.com/sharpsir-group"><strong>Sharp Matrix</strong></a> platform · <a href="https://sharpsir.group">sharpsir.group</a></sub>
</p>
