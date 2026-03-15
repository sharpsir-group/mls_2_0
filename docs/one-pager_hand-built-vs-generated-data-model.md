# Hand-built data model vs generated — differences and benefits

**Purpose:** One-page reference for why a data model built from real data analysis and a single source of truth (DBML + ETL) delivers more than an auto-generated or template-derived schema.

---

## How they differ

| Aspect | Generated / template-derived | Hand-built from analysis |
|--------|-----------------------------|---------------------------|
| **Source of truth** | Inferred from API responses, or copied from a generic spec (e.g. RESO names). No single doc that defines tables and relationships. | One documented schema (e.g. DBML): tables, columns, relationships, and intent. ETL and apps align to it. |
| **Data reality** | Assumes clean, consistent payloads. Often wrong types, missing handling for nulls/empties, or wrong keys. | Based on what the source actually returns: optional columns, null handling (`col_or_null`, `try_cast_or_null`), dedup and keys chosen from real data (e.g. `ref`, composite keys). |
| **Relationships** | Often implied or guessed (e.g. property → project, contact → lead). Breaks when IDs or cardinality don’t match reality. | Explicit in the model; ETL enforces them; silver/gold stay consistent with how the business uses the data. |
| **Change and evolution** | Small API or business changes cause breakage or “magic” fixes because no one knows what was assumed. | Layered pipeline (bronze raw → silver normalized → gold business-ready). Changes are localised; schema evolution (e.g. optional columns, CDC) is designed in. |
| **Ownership** | No clear owner; “generated” or “vibecoded” logic is hard to trace. | One model (DBML), one pipeline (notebooks); when something breaks, there is a clear path from source to gold. |

---

## Benefits of the hand-built model (what you get in return)

1. **Single source of truth**  
   DBML defines the target schema once. Bronze/silver/gold and downstream apps reference the same tables and relationships. No drift between “what the docs say” and “what the pipeline does.”

2. **Data that matches reality**  
   Schema and ETL are informed by actual Qobrix (or other source) payloads: which fields exist, which are optional, how to deduplicate, which keys to use. Fewer runtime surprises and UNRESOLVED_COLUMN / type errors.

3. **Maintainability**  
   When the source API or business rules change, you have a clear map: change DBML if needed, then update the affected ETL layer. No reverse-engineering of generated or ad-hoc tables.

4. **Safe evolution**  
   Optional columns and careful typing avoid breaking pipelines when new fields appear. CDC with metadata (e.g. `cdc_metadata`, `_cdc_updated_at`) allows incremental sync without full refreshes. Layering isolates impact of changes.

5. **Auditability and debugging**  
   Intent is documented (e.g. “Bazaraki”, “changelog”, “audit”). When reports or apps are wrong, you can trace back through gold → silver → bronze to the source and the model.

---

## Short summary

- **Generated/template models:** Fast to produce, but no one has looked at the real data or locked in a single, owned design. Result: things that “don’t work properly” and are hard to fix.
- **Hand-built model (DBML + ETL):** Takes more upfront effort, but gives one source of truth, data aligned to reality, clear ownership, and a pipeline that can evolve and be debugged. That’s the benefit over generated things.
