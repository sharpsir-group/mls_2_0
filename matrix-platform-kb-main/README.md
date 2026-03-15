# Sharp Matrix Platform — Knowledge Base

LLM-readable knowledge base for the Sharp Matrix digital platform (Sharp Sotheby's International Realty).

## For Lovable

Start with **[AGENTS.md](AGENTS.md)** — it contains the reading order and navigation map.

### Quick Reading Order

1. [AGENTS.md](AGENTS.md) — master navigation
2. [docs/platform/app-template.md](docs/platform/app-template.md) — how to build Matrix Apps
3. [docs/data-models/dash-data-model.md](docs/data-models/dash-data-model.md) — practical field reference
4. [docs/INDEX.md](docs/INDEX.md) — full chapter index

### Raw URL Pattern

To fetch any file via URL:

```
https://raw.githubusercontent.com/sharpsir-group/matrix-platform-kb/main/{path}
```

Example:
```
https://raw.githubusercontent.com/sharpsir-group/matrix-platform-kb/main/AGENTS.md
```

## Structure

```
AGENTS.md                    ← Entry point for LLMs
README.md                    ← This file
docs/
  INDEX.md                   ← Master index with chapter summaries
  ARCHITECTURE.md            ← System architecture
  platform/                  ← Platform overview, app template, MLS datamart
  data-models/               ← Dash data model, RESO interop, ETL pipeline
  business-processes/        ← Listing pipeline, sales pipeline, lead qualification
  product-specs/             ← UI specs: dashboards, forms, Kanban
  vision/                    ← Digital strategy 2026-2028, AI sales model
  references/                ← API catalogs, field summaries
dash/                        ← SIR/Anywhere.com listing forms (DOCX)
qobrix/                      ← Qobrix OpenAPI spec (YAML)
reso dd/                     ← RESO Data Dictionary spreadsheets (XLSX)
vision/                      ← Strategy PDFs and architecture diagrams
current busienss practice/   ← Operational checklists (XLSX)
```

## Key Concepts

- **Dash/Anywhere.com** = practical core data model (field names for apps)
- **RESO DD 2.0** = interoperability standard (syndication, external APIs)
- **Supabase** = Common Data Layer (system of record for apps)
- **Databricks** = DWH & ETL engine (Bronze/Silver/Gold)
- **Lovable** = app builder (all Matrix Apps)
- **SSO** = 5-level scope, CRUD permissions, dual-Supabase architecture
