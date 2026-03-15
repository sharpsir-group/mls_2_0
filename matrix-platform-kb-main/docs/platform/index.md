# Chapter 0: Sharp Matrix Platform — Overview

> The Sharp Matrix Platform is the target digital ecosystem for Sharp Sotheby's International Realty.
> It connects all business applications through a common data layer with Dash/Anywhere.com as the practical data model.
>
> **For Lovable**: To build apps, start with [app-template.md](app-template.md).

## What is Sharp Matrix?

Sharp Matrix is a **multi-app platform** where every application — from broker tools to client portals to AI engines — shares a single, consistent data layer. Dash/Anywhere.com provides the practical field definitions used for app development; RESO DD 2.0 serves as the interoperability standard for syndication and external APIs. Apps are built by **Lovable** using the `matrix-apps-template` starter kit and run on **Supabase**.

### Core Principle

> **Dash/Anywhere.com is the practical data core.** CDL-Connected apps use Dash-derived field names (e.g., `list_price`, `bedrooms`, `city`). RESO DD names are used for outbound syndication and the RESO Web API.

## Three-Platform Architecture

| Platform | Role | Why |
|----------|------|-----|
| **Supabase** | Common Data Layer — system of record for apps | Edge Functions, Realtime, Auth, RLS, Lovable integration |
| **Databricks** | DWH & ETL engine — data ingestion and analytics | Medallion architecture (Bronze/Silver/Gold), CDC, SQL analytics |
| **Lovable** | App builder — builds all Matrix Apps | Rapid development, native Supabase integration |

**Why Supabase over Databricks for CDL?** Databricks (with Lakebase) is a strong DWH but lacks Edge Functions and has no Lovable integration. Supabase provides the app-facing data layer with built-in auth, realtime, and edge compute.

## Two Types of Matrix Apps

| Type | CDL Usage | Example Apps |
|------|-----------|-------------|
| **CDL-Connected** | Reads/writes shared RESO tables (`property`, `member`, `contacts`) | Broker, Manager, Client Portal, Marketing |
| **Domain-Specific** | Uses CDL only for auth/permissions; has own Supabase instance | HRMS, Finance, Contact Center |

Both types share the same template patterns: dual-Supabase, SSO auth, permissions, RLS, shadcn/ui.
See [app-template.md](app-template.md) for full technical details.

## Reference Sources

| Source | Role in Sharp Matrix | Location |
|--------|---------------------|----------|
| **Dash / Anywhere.com** | **Practical core** — concrete field definitions for app development | `dash/BlankForm_*.docx`, Dash API |
| **RESO DD 2.0** | Interop standard — names for syndication and external APIs | `reso dd/RESO_Data_Dictionary_2.0.xlsx` |
| **Qobrix CRM** | Legacy migration source — being decommissioned | `qobrix/qobrix_openapi.yaml` |

## Phased Migration

### Current → Target

| Aspect | Current | Target |
|--------|---------|--------|
| CRM | Qobrix | Matrix Apps on Supabase |
| Data direction (Dash) | Pull from Dash API/FILE | Push to Dash for syndication |
| System of record | Qobrix + Dash | Supabase CDL |
| Data warehouse | Databricks (ETL + DWH) | Databricks (analytics/BI only) |
| App builder | N/A | Lovable |

**Strategic goal**: Matrix Apps replace Qobrix CRM. Dash flips from pull to push. Supabase CDL becomes the sole system of record.

## Documents

| Document | What It Contains |
|----------|-----------------|
| [app-template.md](app-template.md) | **Start here** — How to build Matrix Apps: stack, auth, permissions, RLS, UI |
| [security-model.md](security-model.md) | Security model: 5-level scope, 23 roles, JWT claims, RLS patterns A-E |
| [operations.md](operations.md) | Operations: CI/CD, deployment, monitoring, logging, audit, DR/backup |
| [compliance.md](compliance.md) | Compliance: GDPR, data protection, retention, DSAR procedures |
| [mls-datamart.md](mls-datamart.md) | MLS 2.0 data pipeline: sources, Databricks ETL, Supabase CDL sync |
| [ecosystem-architecture.md](ecosystem-architecture.md) | Full platform architecture: channels, apps, data layer, AI/ML |
| [app-catalog.md](app-catalog.md) | All apps in the platform: purpose, users, RESO resources consumed |
| [testing-strategy.md](testing-strategy.md) | Testing: unit (Vitest), integration, E2E (Playwright), contract testing |
| [api-contracts.md](api-contracts.md) | Edge Function API surface, OpenAPI reference, per-app dependencies |
| [kb-methodology.md](kb-methodology.md) | KB design principles, versioning, contribution guidelines |

## How Apps Share Data

CDL-Connected apps operate on the same RESO-named Supabase tables:

1. **Broker App** writes a listing → stored in RESO `property` table
2. **Marketing App** reads the same listing → uses the same RESO field names
3. **Client Portal** displays the listing → renders from the same RESO data
4. **AI Copilot** analyzes the listing → reasons over the same RESO fields
5. **BI Dashboard** reports on the listing → aggregates from Databricks (synced from CDL)

Domain-Specific apps (like HRMS) use their own tables but share auth, permissions, and UI framework through the SSO instance.
