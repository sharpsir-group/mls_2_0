# Why the new DBML and ETL pipelines are better than the previous flattened approach

**Short version for your boss**

---

## 1. What was wrong with the flattened pipelines

- **Flattened JSON:** The old approach used `pandas.json_normalize()` (or similar) to flatten nested API responses into hundreds of columns. That led to:
  - **Brittle schema:** Any change in the API (new nested field, rename) broke the pipeline or produced empty/duplicate columns.
  - **Hard to maintain:** Column names like `agent.company.address.city` are tied to one API shape; when the API evolves, everything breaks.
  - **No single source of truth:** The “model” was implicit in the flattening logic, not in a documented schema.
- **No clear layering:** Bronze (raw), silver (cleaned, typed), and gold (business-ready) were mixed or missing, so it was unclear where to fix bugs or add business rules.
- **Full refresh only:** Re-running the whole pipeline for small changes was slow and resource-heavy.

---

## 2. What the new approach gives you

| Aspect | Flattened (before) | New DBML + ETL (now) |
|--------|--------------------|------------------------|
| **Schema** | Implicit in code, many columns | Explicit in `app_data_model.dbml`: tables, columns, relationships, notes |
| **API alignment** | One big flatten = breaks on API change | Bronze keeps API shape (nested → JSON string); no flattening |
| **Maintainability** | Change = dig through transform code | Change = update DBML + one silver/gold step; column list is clear |
| **Layers** | Unclear or mixed | Bronze (raw) → Silver (normalized, typed) → Gold (common_* for apps) |
| **Deduplication** | Ad hoc or missing | Defined in gold (e.g. by ref, by property_id+viewing_id), same pattern everywhere |
| **Incremental sync** | Not supported or custom hacks | CDC (00c): only fetch modified/created since last sync, then MERGE into bronze |
| **Reuse** | Pipelines tied to one use case | Gold tables (common_properties, common_contacts, etc.) are shared; apps and Knowledge Base read the same model |

The DBML file is the **single source of truth**: it documents what we have, what we build, and how entities relate. The ETL pipelines implement that model step by step.

---

## 3. Where and how the new model is used (and how it fits the Knowledge Base Sharp Matrix)

**English:**

The proposed data model is used in two main places:

1. **Databricks / data layer**  
   The ETL pipelines (00b, 00c, 02*, 03*) read from Qobrix and write **bronze** (raw), **silver** (cleaned), and **gold** (`common.*`) tables. All consumer applications and the Knowledge Base should rely on these **gold** tables (e.g. `common_properties`, `common_contact_profiles`, `common_leads`) so that:
   - Everyone uses the same definitions (from the DBML).
   - Changes to the model are done once (DBML + ETL) and all consumers benefit.

2. **Knowledge Base Sharp Matrix (Lovable)**  
   The Knowledge Base that you already started with can sit on top of this model:
   - **Data source:** It should treat the **gold** layer as the source of truth (e.g. via an API or direct queries that expose `common.*` tables or views).
   - **Consistency:** The same entities (properties, contacts, leads, agents, projects, etc.) and the same field names and relationships as in the DBML are then reflected in the Knowledge Base, so answers and references stay aligned with the real data.
   - **Where it applies:** Any part of Sharp Matrix that needs “listings”, “contacts”, “leads”, “agents”, “projects” or related concepts should be wired to these gold tables (or to an API that serves them), rather than to the old flattened or ad hoc tables.

So: the **proposed data model is applied** in the data platform (bronze/silver/gold) and in **all downstream use** of that data—including the Knowledge Base. The Knowledge Base uses the same model by consuming the gold layer.

---

**Russian (answer to your boss’s question):**

**В какой части и как предполагается применять предложенную модель данных с учётом Knowledge Base Sharp Matrix, с использованием которой мы уже начали работать?**

Предложенная модель данных применяется в двух местах.

1. **В слое данных (Databricks).**  
   ETL-пайплайны загружают данные из Qobrix в бронз (сырые), серебро (очищенные) и золотой слой (`common.*`). Золотой слой — единый источник правды для всех приложений и для Knowledge Base: общие таблицы по объектам, контактам, лидам, агентам, проектам и т.д. Все определения и связи зафиксированы в DBML и реализованы в пайплайнах.

2. **В Knowledge Base Sharp Matrix (Lovable).**  
   База знаний, с которой вы уже работаете, должна опираться на этот же слой:
   - **Источник данных:** в качестве источника фактов использовать золотой слой (таблицы `common.*` или API, построенный поверх них).
   - **Единообразие:** те же сущности (объекты, контакты, лиды, агенты, проекты) и те же поля, что и в DBML, тогда будут отражены в Knowledge Base — ответы и ссылки останутся согласованными с реальными данными.
   - **Где именно:** любой функционал Sharp Matrix, который использует объявления, контакты, лиды, агентов, проекты и т.п., целесообразно подключать к золотому слою (или к API поверх него), а не к старым «плоским» или разрозненным таблицам.

Итого: модель данных применяется в платформе данных (бронз → серебро → золото) и во всём последующем использовании этих данных, включая Knowledge Base. Sharp Matrix использует ту же модель за счёт потребления золотого слоя.

---

## 4. How to align the Knowledge Base (Lovable / Sharp Matrix) with this repo

To make the data model and the Knowledge Base explicitly aligned (and to show your boss the connection), you can:

1. **Add the Knowledge Base content to this repo**  
   - Export or copy from Lovable the files that describe:
     - entities (e.g. property, contact, lead),
     - fields,
     - any “data dictionary” or instructions that reference Qobrix/Sharp data.
   - Put them in a folder in this repo, e.g. `docs/knowledge_base_sharp_matrix/` or `knowledge_base/`.
   - Add a short `README` there explaining: “This is the Sharp Matrix Knowledge Base; it should use the gold layer described in `docs/app_data_model.dbml`.”

2. **Document the mapping**  
   - In this repo (e.g. in `docs/`), add a one- or two-page doc that maps:
     - Knowledge Base entities → gold tables (e.g. “Listings” → `common_properties` / `common_property_listing`),
     - Key fields → columns in those tables.
   - That gives a clear “where the model is applied” for the Knowledge Base.

3. **API / access**  
   - If Sharp Matrix talks to data via an API, ensure that API reads from the gold tables (or views on them) and exposes the same names and relationships as in the DBML. Then the “application of the model” is explicit in the API contract.

If you download or copy the Lovable/Sharp Matrix knowledge base files into this repo (e.g. under `docs/knowledge_base_sharp_matrix/`), we can:
- Propose exact mappings from KB entities to `common.*` tables,
- Suggest a small “data dictionary” section for the KB that references the DBML,
- And you can show your boss a single place (this repo + DBML + KB folder) where the model and its use in the Knowledge Base are documented.
