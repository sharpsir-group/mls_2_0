# Chapter 6: References — Index

> Raw API catalogs, data dictionary summaries, source repositories, and live endpoints.
> These are **reference and migration sources** for the Sharp Matrix Platform —
> not the platform itself. The canonical data layer is RESO DD 2.0.

## Documents

| Document | What It Contains | Role |
|----------|-----------------|------|
| [qobrix-api-summary.md](qobrix-api-summary.md) | All 83 Qobrix API resource groups and 149 schemas | Reference: current CRM capabilities to replicate |
| [reso-dd-fields-summary.md](reso-dd-fields-summary.md) | RESO DD 2.0 resource names, key fields, and lookup categories | Canonical: the standard Sharp Matrix builds on |

## Source Repositories

| Repo | Path | Purpose |
|------|------|---------|
| **matrix-apps-template** | `/home/bitnami/matrix-apps-template` | App starter kit: dual-Supabase, SSO, permissions, RLS, UI conventions |
| **matrix-hrms** | `/home/bitnami/matrix-hrms` | Working example: Domain-Specific app (25+ tables, 30+ hooks) |
| **mls_2_0** | `/home/bitnami/mls_2_0` | Data pipeline: Databricks ETL (Bronze/Silver/Gold) + RESO Web API |

## Live Endpoints

| Endpoint | URL | Auth | Purpose |
|----------|-----|------|---------|
| RESO Web API | `https://{host}:3900/reso` | OAuth 2.0 Client Credentials | OData 4.0 access to gold layer data |
| HomeOverseas Export | `https://{host}:3900/export/homesoverseas.xml` | Public | Cyprus listings XML feed |

## Supabase Project References

| Name | Project ID | Role |
|------|-----------|------|
| **Sharp Matrix SSO** | `xgubaguglsnokjyudgvc` | SSO, Auth, RBAC, Tenants, AD Users |
| **CY Web Site** | `yugymdytplmalumtmyct` | Cyprus real estate website |
| **HRMS** | `wltuhltnwhudgkkdsvsr` | HR Management System (domain-specific app) |
| **Lovable Source** | `ibqheiuakfjoznqzrpfe` | Development source (read-only) |

## Raw Source Files

| File | Where | Role in Sharp Matrix |
|------|-------|---------------------|
| `reso dd/RESO_Data_Dictionary_2.0.xlsx` | Fields + Lookups + Version sheets | **Canonical** — full field definitions and lookup values for the platform data layer |
| `reso dd/RESO_Data_Dictionary_1.7.xlsx` | Previous DD version | Reference for backward compatibility |
| `qobrix/qobrix_openapi.yaml` | 68,000+ lines OpenAPI 3.0 spec | **Migration source** — current CRM API, use for data migration and capability reference |
| `dash/BlankForm_*.docx` | 6 SIR/Anywhere.com form templates | **Reference** — broker-facing field requirements from Sotheby's International Realty |

## Reference Source Roles

| Source | What It Tells Us | How Sharp Matrix Uses It |
|--------|-----------------|-------------------------|
| **RESO DD 2.0** | Standard field names, types, lookups for real estate data | Canonical data layer — all CDL-Connected apps use these names |
| **Qobrix CRM** | Current entity schema, API patterns, workflow capabilities | Migration source + capability reference (being decommissioned) |
| **SIR / Anywhere.com** | What fields brokers need on listing forms | Field requirements reference — ensures coverage |
| **matrix-apps-template** | Tech stack, auth flow, permissions, RLS patterns | Blueprint for every Matrix App built by Lovable |
| **matrix-hrms** | Real app implementation: domain tables, hooks, workflows | Working example of a Domain-Specific app |
| **mls_2_0** | Data pipeline, ETL, RESO Web API | Data infrastructure — feeds Supabase CDL |
