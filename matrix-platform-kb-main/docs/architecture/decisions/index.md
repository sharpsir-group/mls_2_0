# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Sharp Matrix platform. Each ADR documents a significant architectural choice, its context, and consequences.

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001.md) | Why Supabase over Firebase/Hasura for CDL | Accepted |
| [ADR-002](ADR-002.md) | Why dual-Supabase (SSO + per-app DB) over schema-based multi-tenancy | Accepted |
| [ADR-003](ADR-003.md) | Why Lovable as the app builder | Accepted |
| [ADR-004](ADR-004.md) | Why Databricks for ETL over dbt/Airbyte/Fivetran | Accepted |
| [ADR-005](ADR-005.md) | Why RESO DD 2.0 as interop layer with Dash as practical core | Accepted |
| [ADR-006](ADR-006.md) | Why FastAPI + OData 4.0 for the RESO Web API | Accepted |
| [ADR-007](ADR-007.md) | Why Edge Functions over traditional backend (Deno runtime) | Accepted |
| [ADR-008](ADR-008.md) | Why 5-level scope hierarchy over simpler RBAC | Accepted |
| [ADR-009](ADR-009.md) | Why medallion architecture (Bronze/Silver/Gold) for ETL | Accepted |
| [ADR-010](ADR-010.md) | Why PM2 + cron over Kubernetes/ECS for pipeline orchestration | Accepted |
