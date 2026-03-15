# Testing Strategy — Unit, Integration, E2E, Contract Testing

> Source: matrix-apps-template, matrix-platform-foundation
>
> **For Lovable**: This document defines testing requirements for Matrix Apps.

## Testing Pyramid

| Layer | Tool | Scope |
|-------|------|-------|
| **Unit** | Vitest | React components, hooks, utilities |
| **Integration** | Supabase test helpers | RLS policies, Edge Function I/O |
| **E2E** | Playwright | Critical user flows |
| **Contract** | Schema diff + migration review | CDL schema compatibility across apps |

Unit tests form the base; integration validates RLS and Edge Functions; E2E covers critical paths; contract testing ensures 12+ apps sharing the CDL detect breaking schema changes.

## Coverage Targets

| Target | Scope |
|--------|-------|
| **80% unit** | Shared libs: auth hooks (`useAuth`, `useActiveRole`, `useRoleConfig`), permission checks, data transformation utilities |
| **Smoke E2E** | Critical paths: login flow, data CRUD, role switching, permission denial |

## Unit Testing (Vitest)

**Focus areas:**
- `useAuth()`, `useActiveRole()`, `useRoleConfig()` — mock JWT claims, assert returned values
- Data transformation utilities (RESO field mapping, form payloads)
- Form validation logic (required fields, format checks)
- Permission helpers (`canAccessPage`, `canPerformAction`)

**Example**: Mock `AuthContext` with different `scope`/`crud` values; assert `useActiveRole()` returns correct `canCreate`, `canRead`, etc.

## Integration Testing

- **Supabase local dev** for RLS policy verification
- **Edge Function** request/response validation (invoke with test JWT, assert response shape)
- Use `supabase functions serve` locally; call functions via `fetch` with mock tokens

## E2E Testing (Playwright)

**Critical flows:**
- OAuth login (redirect → callback → token exchange)
- Listing creation (CDL-Connected apps)
- Role switching (switch-role → JWT refresh → UI reflects new scope)
- Permission denial (access protected page without permission → redirect or 403)

## Contract Testing

**Problem**: 12+ apps share the CDL. A migration that drops or renames a column breaks every app that reads that table.

**Process:**
1. Every CDL migration must be reviewed against all apps that read the affected tables
2. Migration checklist: list apps + tables used; verify no breaking changes
3. If breaking: coordinate app updates or add backward-compatible columns first

**Detection**: Automated script comparing table/column names in KB docs vs actual Supabase schema. Run periodically or on migration PR.

## Definition of Done

A feature is done when:
- Unit tests pass
- E2E smoke passes for affected flows
- RLS policies verified (integration or manual)
- KB cross-reference updated if schema changed

## KB Validation

Periodic check that KB references match the codebase:
- Script: compare table names in `docs/data-models/*.md` vs `supabase/migrations/` or live schema
- Flag mismatches (tables in KB but not in schema, or vice versa)
- Run in CI or weekly manual check

## Implementation

| Component | Location | Purpose |
|-----------|----------|---------|
| Vitest config | `matrix-apps-template/vitest.config.ts` | Unit test runner, coverage thresholds |
| Playwright config | `matrix-apps-template/playwright.config.ts` | E2E browser tests, base URL, auth state |
| CI/CD | GitHub Actions | `test.yml`: `npm run test` (Vitest), `npx playwright test` on PR; block merge on failure |

**Template setup**: Add Vitest + Playwright to `matrix-apps-template`; document in README. New apps inherit config.

## Cross-Reference

| For | See |
|-----|-----|
| Deployment and CI/CD | [operations.md](operations.md) |
| App architecture and auth | [app-template.md](app-template.md) |
| CDL schema and RLS | [mls-cdl-schema.md](../data-models/mls-cdl-schema.md) |
