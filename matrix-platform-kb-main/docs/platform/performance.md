# Performance Requirements & Capacity Planning

> **For Lovable**: This document defines performance targets for Matrix Apps.

---

## Latency Targets

| Component | Target (p95) |
|-----------|--------------|
| CDL query | <200ms |
| Edge Function | <500ms |
| CDC lag | <15 min |
| App page load | <2s |
| Listing detail | <1s |

## Concurrent Users

| User Type | Total | Peak Concurrent |
|-----------|-------|-----------------|
| Agents (brokers, managers, contact center) | ~200 across 3 markets | 80 |
| Portal clients | ~500 | 50 |

## CDL Capacity

- **12 apps** sharing Supabase connection pool
- **Pro plan**: 60 direct connections + Supavisor pooling
- **PgBouncer** for connection management

## Data Volume

| Metric | Current | Scale Target (2028) |
|--------|---------|---------------------|
| Active listings | ~2,000 | 10,000 across 5 markets |
| Contacts | ~10,000 | — |
| Transactions/year | ~500 | — |

## Load Testing Approach

- **Tools**: k6 or Artillery against staging instance
- **Key scenarios**: Login flow, listing search, listing CRUD, concurrent API calls

## Cross-Reference

| For | See |
|-----|-----|
| Deployment, monitoring, DR | [operations.md](operations.md) |
| MLS 2.0 pipeline, CDL schema | [mls-datamart.md](mls-datamart.md) |
