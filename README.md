# MLS 2.0 — Databricks ETL pipeline

Data pipeline for **Sharp Sotheby's International Realty**: ingest from the **Qobrix API**, transform through a medallion (Bronze → Silver → Gold) in **Databricks**, and produce a **gold** layer aligned to the app data model for downstream use (Supabase CDL sync, RESO Web API, or analytics).

---

## What this repo does

- **Bronze:** Raw Qobrix API responses into `sharp.mls2.qobrix_api_*` (full refresh: **00b**; incremental CDC: **00c**).
- **Silver:** Normalized, typed tables in `sharp.mls2.qobrix_silver_*` (one notebook per entity: **02e**–**02q**).
- **Gold:** Deduplicated, business-ready tables in **`common.common_*`** (notebooks **03e**–**03t**), aligned to `docs/app_data_model.dbml`.

The **data model** is defined once in DBML; all ETL and downstream consumers reference it.

---

## Repo layout

| Path | Purpose |
|------|--------|
| `notebooks/00b_*` | Full refresh bronze (all Qobrix entities). |
| `notebooks/00c_*` | CDC bronze (incremental after 00b). |
| `notebooks/02e_*` – `02q_*` | Silver ETL (bronze → silver, one notebook per entity). |
| `notebooks/03e_*` – `03t_*` | Gold ETL (silver → `common.*`, plus changelogs/segments). |
| `docs/app_data_model.dbml` | Single source of truth: tables, columns, relationships. |
| `docs/databricks_job_setup.md` | How to run the pipeline as Databricks jobs (full refresh vs CDC, tasks, dependencies). |
| `docs/brief_new_model_vs_flattened.md` | Why this model and layering vs flattened pipelines. |
| `docs/one-pager_hand-built-vs-generated-data-model.md` | Benefits of the hand-built data model. |
| `matrix-platform-kb-main/` | Sharp Matrix Knowledge Base (platform docs; see `docs/kb_and_mls2_0_contribution.md` for how this repo fits). |

---

## Running the pipeline

1. **Databricks:** Use a cluster with access to the `sharp` catalog (and `common` for gold).  
2. **Credentials:** Set `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL` (e.g. via job env or secrets).  
3. **Jobs:**  
   - **Full refresh:** Run **00b** once, then all **02*** silver, then all **03*** gold.  
   - **CDC:** Run **00c** on a schedule, then the same silver and gold notebooks.

Details, task order, and how to avoid Delta metadata conflicts: **[docs/databricks_job_setup.md](docs/databricks_job_setup.md)**.

---

## Key docs

- [Databricks job setup](docs/databricks_job_setup.md) — job layout, dependencies, credentials, Delta concurrency.
- [App data model (DBML)](docs/app_data_model.dbml) — schema that bronze/silver/gold implement.
- [New model vs flattened](docs/brief_new_model_vs_flattened.md) — why this design.
- [KB and MLS 2.0 contribution](docs/kb_and_mls2_0_contribution.md) — how this pipeline fits the Sharp Matrix Knowledge Base.
