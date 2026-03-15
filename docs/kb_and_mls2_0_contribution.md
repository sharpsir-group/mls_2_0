# Matrix Platform Knowledge Base — purposes and how MLS 2.0 (DBML + ETL) contributes

## 1. What the Knowledge Base (`matrix-platform-kb-main`) is for

The **Sharp Matrix Platform Knowledge Base** is an LLM-readable documentation set for the Sharp Matrix digital platform (Sharp Sotheby's International Realty — Cyprus, Hungary, Kazakhstan). It is used with **Lovable** (and similar tools) so that:

- **Developers and AI** know how to build and change Matrix Apps consistently.
- **Data and integrations** are described in one place: CDL schema, ETL, Qobrix, RESO, Dash.

**Main purposes:**

| Purpose | Where in the KB | What it gives |
|--------|------------------|----------------|
| **Build Matrix Apps** | `docs/platform/app-template.md`, `AGENTS.md` | How to build apps (dual-Supabase, SSO, RLS, CDL-connected vs domain-specific). |
| **Use the right data model** | `docs/data-models/dash-data-model.md`, `mls-cdl-schema.md` | Dash field names and **18 MLS tables** (e.g. `mls_listings`, `mls_contacts`) deployed on the **Supabase CDL** — 422 columns, RLS, RESO-aligned. |
| **Understand the data pipeline** | `docs/data-models/etl-pipeline.md`, `docs/platform/mls-datamart.md` | Bronze/Silver/Gold ETL in Databricks; gold → Supabase CDL sync; CDC via `cdc_metadata`; phased migration (Qobrix → Matrix Apps → CDL as system of record). |
| **Map systems** | `docs/data-models/qobrix-data-model.md`, `property-field-mapping.md` | Qobrix as **migration source**; mapping to RESO (Property, Contacts, Member, ShowingAppointment, etc.). |
| **Business processes** | `docs/business-processes/` | Listing pipeline, sales pipeline, lead qualification, checklists. |
| **Product and vision** | `docs/product-specs/`, `docs/vision/` | Broker dashboard, forms, Kanban, client portal, contact center, marketing; strategy 2026–2028, AI sales model. |

The KB’s data-model index states: **Dash/Anywhere.com = practical core** for app fields; **RESO DD 2.0 = interop** for syndication and APIs; **Qobrix = reference/migration source**. The pipeline is described as: *External sources → Bronze (raw) → Silver (normalized) → Gold (RESO DD 2.0) → Supabase CDL*. So the KB is the single place where platform identity, app-building rules, data models, ETL, and business processes are defined for both humans and LLMs.

---

## 2. How your work (DBML + ETL in `mls_2_0`) contributes

Your repo **`mls_2_0`** is explicitly referenced in the KB as:

> **mls_2_0** — MLS 2.0 pipeline: Databricks ETL + RESO Web API

The KB mls-datamart doc states that MLS 2.0 is the production pipeline (source: `mls_2_0`), with Databricks medallion and gold → Supabase CDL sync. So the KB expects this pipeline to exist and to feed the “MLS” / CDL side of the platform. Your work is the **implementation** of the data pipeline and model that the KB describes at a high level.

### 2.1 You implement the pipeline the KB describes

- The KB says: **Databricks = DWH & ETL (Bronze/Silver/Gold)** and points to **ETL pipeline** and **mls-datamart**.
- You deliver:
  - **Bronze:** `00b` (full) and `00c` (CDC) → `sharp.mls2.qobrix_api_*` — raw Qobrix, no flattening, DBML-aligned names.
  - **Silver:** `02e`–`02q` → `sharp.mls2.qobrix_silver_*` — normalized, typed, same entities as in DBML.
  - **Gold:** `03e`–`03t` → `sharp.common.common_*` — deduplicated, business-ready tables (properties, contacts, leads, agents, projects, etc.).

So your work **is** the Bronze/Silver/Gold pipeline that the KB’s “ETL pipeline” and “mls-datamart” docs refer to. The KB etl-pipeline and mls-datamart docs describe gold as `mls2.reso_gold` (6 RESO resources); your implementation uses **`common.*`** aligned to the app data model (DBML), the right schema to sync to the Supabase CDL 18 `mls_*` tables or to serve via RESO Web API.

### 2.2 You give the KB a concrete, single source of truth for the “MLS” model

- The KB talks about **Dash/Anywhere.com** as the practical model and **18 MLS tables** in the CDL.
- Your **`docs/app_data_model.dbml`** is the exact schema of what you produce in Databricks:
  - Tables and columns (including `common_*` = gold = what apps and the KB should treat as “the” MLS data).
  - Relationships (e.g. property → project, contact → user, lead → contact).
  - Notes and intent (e.g. “Bazaraki”, “changelog”, “audit”).

So your **DBML is the technical source of truth** for the MLS data model that the KB describes in prose (e.g. in `mls-cdl-schema.md`, `dash-data-model.md`). The KB can point to “gold tables in `common.*` as defined in mls_2_0’s app_data_model.dbml”.

### 2.3 You align with Qobrix without locking the platform to one API shape

- The KB describes **Qobrix** as the current CRM and migration source (`qobrix-data-model.md`, property-field-mapping).
- You:
  - Ingest Qobrix via API into **bronze** (no flattening), so API changes don’t break the pipeline.
  - Normalize in **silver** and expose a stable **gold** (`common_*`) so apps and the KB can rely on a stable schema even when Qobrix changes.

So your work **implements** the “Qobrix as source” story in the KB and makes it maintainable.

### 2.4 You enable incremental sync (CDC) after full refresh

- The KB and operations docs assume a data pipeline that can be run regularly.
- You add **00c (CDC)** so that after the first **00b** full refresh, only changed/new records are fetched and merged into bronze, then silver and gold are refreshed. That matches the idea of “regular sync” and “mls-datamart” without re-running a full Qobrix dump every time.

So your work **implements** the “ongoing sync” behaviour that the KB’s pipeline/operations narrative implies.

### 2.5 You feed the “CDL” that Matrix Apps and the KB refer to

- The KB says **Supabase = Common Data Layer (system of record for apps)** and that **CDL-Connected apps** (e.g. matrix-mls) use “18 MLS tables” and Dash field names.
- In practice, the CDL can be:
  - **Option A:** Supabase tables that are **synced from** Databricks gold (e.g. `common_properties` → Supabase).
  - **Option B:** Apps query an API that **reads from** Databricks gold (e.g. MLS 2.0 RESO Web API or another API backed by `common.*`).

Either way, your **gold layer** (`common.*`) is the canonical “MLS” dataset. The KB’s “CDL schema” and “Dash data model” can be aligned to these tables and to the DBML, so that:
- Lovable and app developers use the same entity and field names as in your DBML/gold.
- The Knowledge Base can state: “MLS data comes from mls_2_0 gold tables (see app_data_model.dbml); CDL/Supabase sync from or expose these.”

So your work **produces the data** that the KB’s “CDL” and “MLS tables” refer to.

---

## 3. Short summary you can give your boss

- **Knowledge Base (matrix-platform-kb-main):**  
  Defines *what* the Sharp Matrix platform is, how to build apps (Lovable), which data model and pipeline to use, and how Qobrix/RESO/Dash fit in. It’s the “contract” for humans and AI.

- **Your work (mls_2_0 — DBML + ETL):**  
  Implements *the* data pipeline and model that the KB describes:
  - **DBML** = single source of truth for the MLS/CDL schema (tables, columns, relationships).
  - **ETL** = Bronze (Qobrix raw) → Silver (normalized) → Gold (`common.*`) in Databricks, plus CDC for incremental sync.
  - **Gold** = the dataset that Matrix Apps and the KB should treat as “the MLS data” (whether consumed via Supabase sync or via an API).

So: the **KB describes the platform and the role of the pipeline**; **your work is that pipeline and that model**. Keeping the KB’s data-model and ETL sections aligned with `mls_2_0` (and with `docs/app_data_model.dbml`) ensures that Lovable and the rest of the platform use one consistent story for MLS data.
