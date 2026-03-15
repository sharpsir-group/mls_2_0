# System Architecture

> Technology map for the Sharp Matrix Platform.
> For app-building patterns, see [platform/app-template.md](platform/app-template.md).
> For the full ecosystem diagram, see [platform/ecosystem-architecture.md](platform/ecosystem-architecture.md).

## Three-Platform Architecture

Sharp Matrix is built on three platforms, each chosen for what it does best:

| Platform | Role | Why Chosen |
|----------|------|-----------|
| **Supabase** | Common Data Layer (CDL) — system of record for apps | Edge Functions, Realtime, Auth, RLS, Lovable integration |
| **Databricks** | DWH & ETL engine — data ingestion, transformation, analytics | Medallion architecture (Bronze/Silver/Gold), CDC, SQL analytics |
| **Lovable** | App builder — builds all Matrix Apps | Rapid UI, native Supabase integration, uses `matrix-apps-template` |

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOVABLE (App Builder)                                               │
│  matrix-apps-template → Vite + React + TypeScript + shadcn/ui       │
├─────────────────────────────────────────────────────────────────────┤
│  MATRIX APPS                                                         │
│  CDL-Connected: Broker │ Manager │ Client Portal │ Marketing         │
│  Domain-Specific: HRMS │ Finance │ Contact Center                    │
├─────────────────────────────────────────────────────────────────────┤
│  SUPABASE CDL (System of Record)                                     │
│  ┌─────────────────────────────┐ ┌────────────────────────────────┐ │
│  │ SSO Instance                │ │ App DB Instances (per app)     │ │
│  │ xgubaguglsnokjyudgvc       │ │ RESO tables (CDL-Connected)   │ │
│  │ Auth, Tenants, Permissions  │ │ Domain tables (Domain-Specific)│ │
│  │ Edge Functions, AD Users    │ │ RLS enforced via SSO JWT      │ │
│  └─────────────────────────────┘ └────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  DATABRICKS (DWH & ETL)                                             │
│  mls_2_0 pipeline: Sources → Bronze → Silver → Gold → CDL sync     │
│  Analytics, BI, AI/ML training data                                  │
├─────────────────────────────────────────────────────────────────────┤
│  EXTERNAL SOURCES & SYNDICATION                                      │
│  Inbound: Qobrix API, DASH API/FILE → Databricks (being phased out)│
│  Outbound: RESO Web API, Dash push, Portal exports (target state)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Two Types of Matrix Apps

| Type | CDL Usage | Supabase Tables | Example |
|------|-----------|----------------|---------|
| **CDL-Connected** | Reads/writes shared Dash-derived tables | `property`, `member`, `contacts`, `media` (Dash field names) | Broker, Manager, Client Portal |
| **Domain-Specific** | Only uses CDL for auth/permissions | Own domain tables (e.g., `employees`, `vacations`) | HRMS, Finance |

Both types use the same template: dual-Supabase, SSO auth, 5-level scope, CRUD permissions, shadcn/ui.
See [app-template.md](platform/app-template.md) for full details.

## Dual-Supabase Architecture

Every Matrix App connects to two Supabase instances:

| Instance | Project ID | Purpose | Client |
|----------|-----------|---------|--------|
| **SSO / CDL** | `xgubaguglsnokjyudgvc` | Auth, permissions, tenants, AD users | `dataLayerClient.ts` |
| **App Database** | Per-app | Business data with RLS | `client.ts` |

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| App Builder | Lovable | Builds all Matrix Apps from `matrix-apps-template` |
| App Framework | Vite + React 18 + TypeScript | Frontend runtime |
| UI Components | shadcn/ui + Tailwind CSS | Sharp design system |
| Data Fetching | TanStack Query + Supabase JS v2 | Cached queries with RLS |
| Auth | Matrix SSO (OAuth 2.0 + PKCE) | JWT with scope, CRUD, tenant, teams |
| App Data Layer | Supabase (PostgreSQL + Edge Functions + RLS) | System of record for apps |
| Practical Data Model | Dash/Anywhere.com | Concrete field names for CDL-Connected apps |
| Interop Standard | RESO DD 2.0 | Standard names for syndication and external APIs |
| DWH & ETL | Databricks (mls_2_0 pipeline) | Bronze/Silver/Gold + CDC |
| Integration API | RESO Web API (FastAPI + OData 4.0) | External consumers & syndication |
| Reference CRM | Qobrix (REST API v2) | Migration source (being decommissioned) |
| Reference Forms | SIR / Anywhere.com | Field requirements for listings |
| Channel Management | Supabase Edge Functions + CDL tables | Ingress/egress channel config and routing (CDL MLS 2.1) |
| Security Model | SSO JWT + RLS helper functions | 5-level scope, 23 roles, patterns A-E |

## Phased Data Flow Evolution

### Current: Inbound from External Sources

```
Qobrix API (Cyprus) ──┐
DASH API (Kazakhstan) ─┼──→ Databricks (Bronze→Silver→Gold) ──→ Supabase CDL
DASH FILE (Hungary) ───┘                                  └──→ RESO Web API → some apps
```

### CDL MLS 2.1: Channel-Managed Platform

```
Ingress Channels                       Egress Channels
┌─────────────────────┐               ┌─────────────────────┐
│ Matrix Apps (direct) │               │ Dash CRUD (push)    │
│ New Constructions    │               │ RESO Web API        │
│ Partner MLS Feeds    │               │ Portal Feeds (XML)  │
└──────────┬──────────┘               └──────────┬──────────┘
           │                                     │
      ┌────┴─────────────────────────────────────┴────┐
      │   Supabase CDL (sole system of record)        │
      │   Ingress/Egress Channel Manager              │
      ├───────────────────────────────────────────────┤
      │   Databricks (DWH / BI / ML — analytics only) │
      └───────────────────────────────────────────────┘
```

Qobrix is decommissioned. Dash flips from pull to push. Managed ingress/egress channels replace ad-hoc integrations. See [mls-datamart.md](platform/mls-datamart.md) for full channel taxonomy.

## Supabase Instances

| Name | Project ID | Role |
|------|-----------|------|
| Sharp Matrix SSO | `xgubaguglsnokjyudgvc` | SSO, Auth, RBAC, Tenants, AD Users |
| CY Web Site | `yugymdytplmalumtmyct` | Cyprus real estate website |
| HRMS | `wltuhltnwhudgkkdsvsr` | HR Management System (domain-specific app) |
| Lovable Source | `ibqheiuakfjoznqzrpfe` | Development source (read-only) |

## Strategic Markets

| Market | Priority | Office Key | Data Source |
|--------|----------|-----------|------------|
| **Cyprus** | Core | `SHARPSIR-CY-001` | Qobrix API (current) → Matrix Apps (target) |
| **Hungary** | Growth | `SHARPSIR-HU-001` | DASH FILE (current) → Matrix Apps (target) |
| **Kazakhstan** | Emerging | `SHARPSIR-KZ-001` | DASH API (current) → Matrix Apps (target) |

## Implementation Roadmap (7 Phases)

| Phase | Period | Focus |
|-------|--------|-------|
| 1. Foundation | Jan-Mar 2026 | Audit, analysis, quick wins |
| 2. Platform Launch | Mar-Apr 2026 | Key platform deployment |
| 3. Process Alignment | Apr-Jun 2026 | Marketing, sales, listings transformation |
| 4. BI + AI Launch | Jul-Oct 2026 | BI platform, AI/ML models |
| 5. Model Testing | Oct-Nov 2026 | AI/ML testing and optimization |
| 6. Full Integration | Dec 2026 - Jan 2027 | Complete system integration |
| 7. Support & Optimization | From Feb 2027 | Continuous improvement, Qobrix decommission |
