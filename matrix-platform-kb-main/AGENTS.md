# Sharp Matrix Platform — Agent Knowledge Map

> This file is the **table of contents** for the Sharp Matrix Platform knowledge base.
> It is deliberately short. Each pointer leads to a deeper source of truth in `docs/`.
> When working in this repository, read this file first, then navigate to the relevant chapter.

## For LLMs — Start Here

Before building or modifying ANY Matrix App:

### Step 1: Read the App Template (mandatory)
→ `docs/platform/app-template.md` — dual-Supabase, SSO auth, permissions, RLS, UI patterns, token architecture

### Step 2: Determine App Type

| Question | → App Type | Example Repo | Read Next |
|----------|-----------|-------------|-----------|
| Does the app work with listings, contacts, agents, showings? | **CDL-Connected** | `/home/bitnami/matrix-mls` | Steps 3a-3c below |
| Does the app have its own domain (HR, finance, operations)? | **Domain-Specific** | `/home/bitnami/matrix-hrms` | Step 3d below |

### Step 3a (CDL-Connected): Read the CDL Schema
→ `docs/data-models/mls-cdl-schema.md` — 18 MLS tables, RLS patterns, CDL connection architecture, key files
→ `docs/data-models/dash-data-model.md` — Dash field names used as column names

### Step 3b (CDL-Connected): Understand Token Architecture (critical)
CDL-Connected apps use **two tokens**:
- **SSO JWT** (custom claims) — for Edge Function calls and App DB PostgREST
- **Supabase native token** (project JWT secret) — for CDL PostgREST reads/writes

The `oauth-token` Edge Function persists role claims (`active_scope`, `active_crud`, `active_team_ids`) to `auth.users.raw_app_meta_data`. CDL RLS helpers fall back to this `app_metadata` when JWT claims aren't present.

→ `docs/platform/security-model.md` — full RLS helpers, app_metadata fallback, JWT claims

### Step 3c (CDL-Connected): CDL Write Pattern
Writes to CDL go through an Edge Function proxy on the app's Supabase instance:
`cdlWrite.ts` → `cdl-write` Edge Function → CDL PostgREST

### Step 3d (Domain-Specific): Read the HRMS Example
→ `/home/bitnami/matrix-hrms` — 25+ domain tables, 30+ hooks, Domain-Specific patterns

### Step 4: Read Relevant Business Processes
→ `docs/business-processes/listing-pipeline.md` — seller-side (8 stages)
→ `docs/business-processes/sales-pipeline.md` — buyer-side (8 stages)
→ `docs/business-processes/listing-checklist.md` — operational checklists

### Step 5 (as needed)
- Syndication/exports: `docs/data-models/dash-data-model.md` (RESO mapping column)
- Security deep-dive: `docs/platform/security-model.md`
- Deployment: `docs/platform/operations.md`
- GDPR/compliance: `docs/platform/compliance.md`

## Platform Identity

**Sharp Matrix** is the multi-app digital platform for **Sharp Sotheby's International Realty** —
luxury real estate brokerage operating in Cyprus, Hungary, and Kazakhstan.

**Built with**: Lovable (app builder) + Supabase (CDL / system of record) + Databricks (DWH / ETL).
**Practical data model**: Dash/Anywhere.com — CDL-Connected apps use Dash field names.
**Interop standard**: RESO DD 2.0 — used for syndication and external APIs.
**App template**: `matrix-apps-template` — defines stack, auth, permissions, UI patterns.
**Strategic goal**: Matrix Apps replace Qobrix CRM. Dash flips from pull to push (syndication).

## Knowledge Base Structure

```
docs/
├── platform/
│   ├── index.md                      ← Platform overview & three-platform architecture
│   ├── app-template.md              ← How to build Matrix Apps (Lovable must read first)
│   ├── security-model.md            ← Auth, roles, permissions, RLS patterns, JWT claims
│   ├── operations.md                ← CI/CD, deployment, monitoring, DR/backup
│   ├── compliance.md                ← GDPR, data protection, retention, DSAR procedures
│   ├── mls-datamart.md              ← MLS 2.0 data pipeline & phased migration roadmap
│   ├── ecosystem-architecture.md     ← Full ecosystem: channels, apps, data, AI/ML
│   ├── app-catalog.md               ← All platform apps: purpose, users, RESO resources
│   ├── performance.md              ← Latency targets, capacity planning, load testing
│   ├── mobile-strategy.md           ← PWA, responsive design, offline requirements
│   └── kb-methodology.md            ← KB design principles, versioning, contribution
├── INDEX.md                          ← Master index with chapter summaries
├── ARCHITECTURE.md                   ← System architecture & technology map
├── vision/
│   ├── index.md                      ← Vision chapter index
│   ├── digital-strategy-2026-2028.md ← Digital strategy: 3 markets, 7 phases, KPIs
│   ├── ai-driven-sales-model.md      ← AI-driven sales management model (16 elements)
│   └── core-beliefs.md              ← Operating principles & design philosophy
├── data-models/
│   ├── index.md                      ← Data models chapter index (Dash-first hierarchy)
│   ├── dash-data-model.md           ← Dash/Anywhere.com practical data model (START HERE)
│   ├── reso-dd-overview.md           ← RESO DD 2.0 — interop standard for syndication
│   ├── reso-canonical-schema.md      ← Which RESO resources/fields map to Dash
│   ├── platform-extensions.md        ← All x_sm_* fields not in Dash or RESO DD
│   ├── mls-cdl-schema.md            ← MLS Listing Management CDL schema (18 tables, 422 cols)
│   ├── etl-pipeline.md              ← Bronze/Silver/Gold ETL pipeline architecture
│   ├── data-quality.md              ← Data quality verification, validation, reporting
│   ├── reso-web-api.md              ← RESO Web API (OData 4.0) endpoint reference
│   ├── qobrix-data-model.md          ← Qobrix CRM reference & migration source
│   └── property-field-mapping.md     ← Field mapping: Dash ↔ RESO ↔ Qobrix ↔ SIR
├── business-processes/
│   ├── index.md                      ← Business processes chapter index
│   ├── listing-pipeline.md           ← Seller-side pipeline (8 stages)
│   ├── sales-pipeline.md             ← Buyer-side pipeline (8 stages)
│   ├── lead-qualification.md         ← MQL → SQL qualification with BANT
│   ├── follow-up-vs-active-sales.md  ← Nurturing vs active deal boundary
│   └── listing-checklist.md          ← Operational checklists (broker/marketing/finance)
├── product-specs/
│   ├── index.md                      ← Product specs chapter index
│   ├── sir-listing-forms.md          ← SIR/Anywhere.com form field specifications
│   ├── broker-dashboard.md           ← AI-powered broker dashboard design
│   ├── manager-kanban.md             ← Manager pipeline & Kanban views
│   ├── personalization.md            ← Personalization & recommendation engine (Phase 4)
│   ├── client-portal.md              ← Buyer/seller self-service portal
│   ├── contact-center.md             ← Lead processing and routing system
│   ├── marketing-platform.md        ← Campaign management and marketing automation
│   └── personas.md                   ← User personas for UX decisions
├── references/
│   ├── index.md                      ← References chapter index
│   ├── qobrix-api-summary.md         ← Qobrix OpenAPI resource catalog
│   └── reso-dd-fields-summary.md     ← RESO DD 2.0 field & lookup summary
```

## Quick Navigation by Task

| If you need to…                              | Read this                                         |
|----------------------------------------------|---------------------------------------------------|
| Build a new Matrix App (start here)          | `docs/platform/app-template.md`                   |
| Understand the Sharp Matrix platform          | `docs/platform/index.md`                          |
| See the full ecosystem architecture           | `docs/platform/ecosystem-architecture.md`         |
| Understand the data pipeline (MLS 2.0)        | `docs/platform/mls-datamart.md`                   |
| Know which apps exist and what they do        | `docs/platform/app-catalog.md`                    |
| Understand the 2026-2028 strategy & roadmap   | `docs/vision/digital-strategy-2026-2028.md`       |
| Understand the AI-driven sales model          | `docs/vision/ai-driven-sales-model.md`            |
| Know the design philosophy                    | `docs/vision/core-beliefs.md`                     |
| See how systems connect                       | `docs/ARCHITECTURE.md`                            |
| See Dash field names for app development       | `docs/data-models/dash-data-model.md`             |
| Map a property field across systems            | `docs/data-models/property-field-mapping.md`      |
| See which RESO fields map to Dash              | `docs/data-models/reso-canonical-schema.md`       |
| Find or add a platform extension (x_sm_*)     | `docs/data-models/platform-extensions.md`         |
| See the MLS CDL schema (18 tables)             | `docs/data-models/mls-cdl-schema.md`              |
| Understand the ETL pipeline (Bronze→Gold)     | `docs/data-models/etl-pipeline.md`                |
| Use the RESO Web API (OData)                  | `docs/data-models/reso-web-api.md`                |
| Understand Qobrix entities & migration        | `docs/data-models/qobrix-data-model.md`           |
| Understand RESO DD 2.0 (interop standard)      | `docs/data-models/reso-dd-overview.md`            |
| Understand auth, roles, permissions, RLS       | `docs/platform/security-model.md`                 |
| Deploy an app or Edge Function                | `docs/platform/operations.md`                     |
| Performance targets, capacity planning        | `docs/platform/performance.md`                   |
| Mobile strategy (PWA, offline)                | `docs/platform/mobile-strategy.md`                |
| Test Matrix Apps (unit, E2E, contract)         | `docs/platform/testing-strategy.md`               |
| Edge Function API contracts                   | `docs/platform/api-contracts.md`                  |
| Handle GDPR, data retention, DSARs            | `docs/platform/compliance.md`                     |
| Understand KB methodology and contribution   | `docs/platform/kb-methodology.md`                 |
| Verify data quality in the pipeline           | `docs/data-models/data-quality.md`                |
| Build a listing workflow                      | `docs/business-processes/listing-pipeline.md`     |
| Build a buyer/sales workflow                  | `docs/business-processes/sales-pipeline.md`       |
| Implement lead scoring / qualification        | `docs/business-processes/lead-qualification.md`   |
| Design the broker dashboard UI                | `docs/product-specs/broker-dashboard.md`          |
| Design listing input forms                    | `docs/product-specs/sir-listing-forms.md`         |
| Build Client Portal, Contact Center, Marketing | `docs/product-specs/client-portal.md`, etc.      |
| Use user personas for UX                     | `docs/product-specs/personas.md`                  |
| Look up Qobrix API endpoints                  | `docs/references/qobrix-api-summary.md`           |
| Look up RESO standard field names             | `docs/references/reso-dd-fields-summary.md`       |

## Source Repos & Files

| Repo / File | Format | Contents |
|------------|--------|---------|
| `/home/bitnami/matrix-apps-template` | React/TS | App template: dual-Supabase, SSO, permissions, RLS, UI |
| `/home/bitnami/matrix-hrms` | React/TS | Example app: HRMS (25+ tables, 30+ hooks, domain-specific) |
| `/home/bitnami/matrix-mls` | React/TS | MLS Listing Management app (CDL-Connected, 18 tables on CDL) |
| `/home/bitnami/mls_2_0` | Python/FastAPI | MLS 2.0 pipeline: Databricks ETL + RESO Web API |
| `vision/Sharp-Sothebys-International-Realty.pdf` | PDF | Full 28-slide digital strategy 2026-2028 |
| `vision/Sarp SIR Platform-2026-02-18-125014.mmd` | Mermaid | Platform ecosystem architecture diagram |
| `vision/AI-driven-model-upravleniya-prodazhami.pdf` | PDF | 16-slide AI-driven sales model |
| `qobrix/qobrix_openapi.yaml` | YAML | Full Qobrix OpenAPI 3.0 spec (68K lines) |
| `reso dd/RESO_Data_Dictionary_2.0.xlsx` | XLSX | RESO DD 2.0 (Fields + Lookups) |
| `reso dd/RESO_Data_Dictionary_1.7.xlsx` | XLSX | RESO DD 1.7 (historical reference) |
| `dash/BlankForm_*.docx` | DOCX | SIR/Anywhere.com listing forms (6 types) |
| `current busienss practice/*.xlsx` | XLSX | Listing checklists 2024–2026 |
