# Organizing the MLS 2.0 pipeline as a Databricks job

Use one of the patterns below depending on whether you run **full refresh** or **CDC** (incremental).

---

## Option A: Two jobs (recommended)

### Job 1: **Full refresh** (run rarely: initial load or recovery)

Single job that runs **00b** once, then all silver, then all gold.

**Tasks (in order):**

| Order | Task name      | Notebook / type | Notes |
|-------|----------------|------------------|--------|
| 1     | bronze_full    | `00b_full_refresh_qobrix_bronze_app_model` | Full bronze load |
| 2     | silver_props   | `02e_silver_qobrix_property_app_model_etl` | Depends on: bronze_full |
| 3     | silver_contacts| `02f_silver_qobrix_contacts_app_model_etl` | Depends on: bronze_full |
| 4     | silver_agents  | `02g_silver_qobrix_agents_app_model_etl`   | Depends on: bronze_full |
| 5     | silver_projects| `02h_silver_qobrix_projects_app_model_etl` | Depends on: bronze_full |
| 6     | silver_*       | 02i, 02j, 02k, 02l, 02m, 02n, 02o (and 02p, 02q if using media) | All depend on: bronze_full |
| 7     | gold_*         | 03e, 03f, 03g, 03h, 03i, 03j, 03k, 03l, 03m, 03n, 03o, 03p, 03q, 03r, 03s, 03t | Each gold task depends on its silver task(s) |

**Simpler variant:** run silver tasks in one “layer” (all depend only on bronze_full), then all gold tasks in a second layer (all depend on “last” silver or a dummy). Example:

- **Layer 1:** `bronze_full` (00b).
- **Layer 2:** all 02* silver tasks, each with dependency on `bronze_full`.
- **Layer 3:** all 03* gold tasks, each with dependency on one silver (e.g. 03e depends on silver_props, 03f on silver_contacts, …).

**Job parameters (or cluster env):**

- `QOBRIX_API_USER`
- `QOBRIX_API_KEY`
- `QOBRIX_API_BASE_URL`

Pass them as **widget values** or **environment variables** on the job cluster so 00b (and 00c) can read them.

---

### Job 2: **CDC** (run on a schedule, e.g. every 15–30 min)

Runs **00c** (incremental bronze), then the same silver and gold notebooks so downstream stays in sync.

**Tasks (in order):**

| Order | Task name | Notebook | Depends on |
|-------|-----------|----------|------------|
| 1     | cdc_bronze | `00c_cdc_qobrix_bronze_app_model` | — |
| 2+    | silver_*   | Same 02* as in Job 1 | cdc_bronze |
| 3+    | gold_*     | Same 03* as in Job 1 | corresponding silver |

Same parameters as Job 1: `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL`.

**When to use:**

- **Job 1 (full refresh):** once at the start, or after a fix/migration.
- **Job 2 (CDC):** on a schedule after the first full refresh.

---

## Option B: One job with a “mode” parameter

Single job with a parameter that switches between full refresh and CDC.

**Tasks:**

1. **bronze** – single task that runs either 00b or 00c:
   - Use a **wrapper notebook** that:
     - Reads a job parameter (e.g. `RUN_MODE = "full"` or `"cdc"`).
     - Calls `dbutils.notebook.run("00b_...", ...)` or `dbutils.notebook.run("00c_...", ...)`.
   - Or use **two tasks** (e.g. `bronze_full`, `bronze_cdc`) and **run only one** via a conditional (e.g. “run if `RUN_MODE == 'full'`”) if your scheduler supports it; otherwise the wrapper is simpler.
2. **Silver** – all 02* tasks depending on the bronze task.
3. **Gold** – all 03* tasks depending on the corresponding silver.

**Job parameter:**

- `RUN_MODE`: `full` or `cdc` (and credentials as above).

---

## How to create the job in the Databricks UI

1. **Workflows → Jobs → Create job**
2. **Task 1 – Bronze**
   - Add task, type **Notebook**.
   - Select the repo/path to `00b_full_refresh_qobrix_bronze_app_model` (or your wrapper).
   - Set **Cluster**: existing or new job cluster (e.g. single node for API calls).
3. **Add remaining tasks**
   - For each 02* and 03* notebook, add a **Notebook** task.
   - In **Depends on**, select the right upstream (e.g. 03e depends on 02e; all 02* can depend on the bronze task).
4. **Parameters**
   - In **Job** or **Task (00b/00c)** settings, add **Parameters** or **Environment variables**:
     - `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL`
   - In notebooks, keep using `dbutils.widgets.get(...)` and/or `os.getenv(...)` so they read from the job.
5. **Schedule (for CDC)**
   - In the CDC job, open **Schedule** and set e.g. **Every 30 minutes** (cron: `0 */30 * * * ?`).

---

## Suggested dependency DAG (conceptual)

```
[00b or 00c]
    |
    +-- 02e --> 03e
    +-- 02f --> 03f
    +-- 02g --> 03g
    +-- 02h --> 03h
    +-- 02i --> 03i
    +-- 02j --> 03j
    +-- 02k --> 03k
    +-- 02l --> 03l
    +-- 02m --> 03m
    +-- 02n --> 03n
    +-- 02o --> 03o
    +-- 02p --> 03p   (optional; media)
    +-- 02q --> 03q   (optional; media)
    |
    +-- 03r (property changelog; from bronze)
    +-- 03s (lead changelog; from bronze)
    +-- 03t (empty tables; no bronze dep)
```

03r, 03s, 03t can depend only on the bronze task (they read from bronze or create empty tables). The rest: each 03* depends on its 02*.

---

## Avoiding Delta "MetadataChangedException" (concurrent writes)

If you see **`MetadataChangedException: The metadata of the Delta table has been changed by a concurrent update`** when running the job, two writers touched the same table (e.g. two runs of the job at once, or duplicate task).

**Options:**

1. **Run silver (and gold) tasks sequentially**  
   Instead of "Layer 2: all 02* depend only on bronze", chain them: e.g. 02e → 02f → 02g → 02h → … so only one silver task runs at a time. Same idea for gold. Slower, but no conflicts.

2. **Don’t run the same job twice at the same time**  
   Ensure only one run of the full-refresh (or CDC) job is active; disable concurrent runs in the job settings if needed.

3. **Retries in the notebook**  
   Some silver notebooks (e.g. 02f) retry the write a few times on conflict. If conflicts are rare, that may be enough; if they persist, use (1).

---

## Credentials and secrets

- **Do not** put API keys in notebook code.
- In Databricks: **Settings → Secrets** (or Unity Catalog secrets). Create a scope and store `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL`.
- In the job (or in a small “config” notebook that runs first), set env vars from secrets, e.g.:
  - `QOBRIX_API_USER`: `{{secrets/your_scope/qobrix_api_user}}`
- Then 00b/00c read via `os.getenv("QOBRIX_API_USER")` (or widgets that you set from the job’s env).

---

## Quick checklist

- [ ] Job cluster or shared cluster with Python 3 + Spark.
- [ ] Repo or workspace path where notebooks (00b, 00c, 02*, 03*) are stored.
- [ ] Job parameters or env vars for `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL` (from secrets).
- [ ] Full-refresh job: 00b → all 02* → all 03* with correct dependencies.
- [ ] CDC job: 00c → same 02* → same 03* with same dependencies.
- [ ] Schedule only the CDC job (e.g. every 30 min); run full refresh manually when needed.
