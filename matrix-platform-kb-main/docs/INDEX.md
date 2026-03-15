# Sharp Matrix Platform — Knowledge Base Index

> Master index for the LLM-readable knowledge base.
> Each chapter is self-contained. Start here, then navigate to the chapter you need.
>
> **For Lovable**: Before building any app, read `platform/app-template.md` first.

## Chapter 0: Platform Overview

What Sharp Matrix is, the three-platform architecture (Supabase + Databricks + Lovable), the app template, and the data pipeline.

| Document | Description |
|----------|-------------|
| [platform/app-template.md](platform/app-template.md) | **Read first** — How to build Matrix Apps: dual-Supabase, SSO, permissions, RLS, HRMS example |
| [platform/index.md](platform/index.md) | Platform overview, three-platform architecture, migration roadmap |
| [platform/mls-datamart.md](platform/mls-datamart.md) | MLS 2.0 data pipeline: Databricks ETL, CDC, Supabase CDL sync, phased migration |
| [platform/ecosystem-architecture.md](platform/ecosystem-architecture.md) | Full ecosystem: channels, apps, data & analytics, AI/ML, external services |
| [platform/app-catalog.md](platform/app-catalog.md) | All 12 platform apps: purpose, users, RESO resources consumed |
| [platform/security-model.md](platform/security-model.md) | Security model: 5-level scope, 23 roles, JWT claims, RLS patterns A-E |
| [platform/operations.md](platform/operations.md) | Operations: CI/CD, deployment, monitoring, logging, audit trail, DR/backup |
| [platform/compliance.md](platform/compliance.md) | Compliance: GDPR, data protection, retention policy, DSAR procedures |
| [platform/kb-methodology.md](platform/kb-methodology.md) | KB design principles, versioning, contribution guidelines |
| [platform/testing-strategy.md](platform/testing-strategy.md) | Testing: unit (Vitest), integration, E2E (Playwright), contract testing |
| [platform/api-contracts.md](platform/api-contracts.md) | Edge Function API surface, OpenAPI reference, per-app dependencies |

## Chapter 1: Vision & Strategy

The digital strategy 2026-2028 and AI-driven sales model for three markets (Cyprus, Hungary, Kazakhstan).

| Document | Description |
|----------|-------------|
| [digital-strategy-2026-2028.md](vision/digital-strategy-2026-2028.md) | Full digital strategy: 3 markets, client segments, 7-phase roadmap, KPI targets |
| [ai-driven-sales-model.md](vision/ai-driven-sales-model.md) | 4-element AI-driven sales model with customer journeys and AI Copilot spec |
| [core-beliefs.md](vision/core-beliefs.md) | Operating principles, platform beliefs, agent-first design philosophy |

## Chapter 2: System Architecture

Three-platform architecture: Supabase (CDL), Databricks (DWH), Lovable (app builder). Phased data flow evolution.

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technology map, three-platform architecture, dual-Supabase, data flow |

## Chapter 3: Data Models

Dash/Anywhere.com as the practical core data model. RESO DD 2.0 as interop standard. ETL pipeline. Platform extensions.

| Document | Description |
|----------|-------------|
| [dash-data-model.md](data-models/dash-data-model.md) | **Start here** — Dash/Anywhere.com practical field reference (50+ fields, 30+ features, media) |
| [reso-dd-overview.md](data-models/reso-dd-overview.md) | RESO DD 2.0 — interop standard for syndication and external APIs |
| [reso-canonical-schema.md](data-models/reso-canonical-schema.md) | Which RESO resources/fields map to Dash, extension governance |
| [platform-extensions.md](data-models/platform-extensions.md) | All 28 `x_sm_*` extensions: fields and lookup values not in Dash or RESO DD |
| [etl-pipeline.md](data-models/etl-pipeline.md) | Bronze/Silver/Gold ETL pipeline: table schemas, notebooks, CDC |
| [data-contracts.md](data-models/data-contracts.md) | ETL schema contracts: layer boundaries, JSON Schema, validation |
| [data-quality.md](data-models/data-quality.md) | Data quality: verification scripts, RESO validation, email reporting |
| [reso-web-api.md](data-models/reso-web-api.md) | RESO Web API (OData 4.0): endpoints, queries, auth, office filtering |
| [qobrix-data-model.md](data-models/qobrix-data-model.md) | Qobrix CRM reference & legacy migration source |
| [property-field-mapping.md](data-models/property-field-mapping.md) | Cross-reference: Dash ↔ RESO ↔ Qobrix ↔ SIR field mapping |

## Chapter 4: Business Processes

Current operational workflows, pipelines, qualification rules, and checklists.

| Document | Description |
|----------|-------------|
| [listing-pipeline.md](business-processes/listing-pipeline.md) | Seller-side pipeline: 8 stages from Prospect to Closed |
| [sales-pipeline.md](business-processes/sales-pipeline.md) | Buyer-side pipeline: 8 stages from Qualification to Closed |
| [lead-qualification.md](business-processes/lead-qualification.md) | MQL → SQL path with BANT criteria |
| [follow-up-vs-active-sales.md](business-processes/follow-up-vs-active-sales.md) | Nurturing vs active deal boundary & triggers |
| [listing-checklist.md](business-processes/listing-checklist.md) | Operational checklists: broker, marketing, finance |

## Chapter 5: Product Specifications

UI/UX specs for dashboards, forms, and Kanban views that the system must implement.

| Document | Description |
|----------|-------------|
| [sir-listing-forms.md](product-specs/sir-listing-forms.md) | SIR/Anywhere.com form field specs (reference for Sharp Matrix forms) |
| [broker-dashboard.md](product-specs/broker-dashboard.md) | AI-powered broker dashboard with auto-prioritization |
| [manager-kanban.md](product-specs/manager-kanban.md) | Manager Kanban & pipeline views |

## Chapter 6: References

Raw API catalogs, data dictionary summaries, and source repositories.

| Document | Description |
|----------|-------------|
| [qobrix-api-summary.md](references/qobrix-api-summary.md) | Qobrix OpenAPI resource & endpoint catalog (83 resources, 149 schemas) |
| [reso-dd-fields-summary.md](references/reso-dd-fields-summary.md) | RESO DD 2.0 field names & lookup names |

---

## How to Use This Knowledge Base

**For Lovable (building Matrix Apps):**
1. Read `platform/app-template.md` — the template patterns you must follow
2. Determine if your app is CDL-Connected or Domain-Specific
3. If CDL-Connected: read `data-models/dash-data-model.md` for practical field names
4. Read the relevant `business-processes/` doc for workflow logic
5. Use Dash-derived field names for all CDL table columns (RESO names for syndication only)
6. Follow the dual-Supabase, SSO, RLS patterns from the template
7. For security model details: see `platform/security-model.md`
8. For deployment and operations: see `platform/operations.md`
9. For data protection (GDPR): see `platform/compliance.md`

**For general context:**
1. Start with `AGENTS.md` (repository root) for quick navigation
2. Read Chapter 0 (Platform) to understand the three-platform architecture
3. Read Chapter 1 (Vision) for strategic context
4. Navigate to the specific chapter relevant to your task
