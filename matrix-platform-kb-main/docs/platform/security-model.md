# Security Model — Auth, Roles, Permissions, RLS

> Source: `matrix-platform-foundation` (SSO instance `xgubaguglsnokjyudgvc`)
> Implementation: `matrix-platform-foundation/SECURITY_MODEL.md`, `supabase/migrations/`, `supabase/functions/`
>
> **For Lovable**: This document defines how auth, roles, and permissions work.
> Every Matrix App must follow these patterns. See also [app-template.md](app-template.md) for how apps consume the security model.

## 5-Level Scope Hierarchy

```
self → team → global → org_admin → system_admin
```

Each higher scope includes the visibility of all lower scopes.

| Scope | Data Visibility | Typical Role | Example |
|-------|----------------|-------------|---------|
| `self` | Own records only | Broker, Staff | A broker sees only their own clients and listings |
| `team` | Own + team members' records | Team Leader, Manager | A sales manager sees all records for their team |
| `global` | All records in tenant | Director, C-suite | A sales director sees every listing and deal across all teams |
| `org_admin` | Full tenant access + admin functions | Organization Admin | Can manage users, roles, app configurations for the organization |
| `system_admin` | Cross-tenant access | System Admin | Platform-wide access across all organizations |

## CRUD Permission Strings

Format: any combination of characters `c`, `r`, `u`, `d`.

| Value | Meaning | Typical Use |
|-------|---------|-------------|
| `r` | Read only | View-only roles, reports |
| `cr` | Create + Read | Data entry, content creators |
| `ru` | Read + Update | Editors, reviewers |
| `crud` | Full access | Managers, admins |
| `rud` | Read + Update + Delete | Moderators |

**In RLS policies**: `(SELECT get_crud()) LIKE '%r%'` checks for read permission.

**In app hooks**: `useActiveRole()` returns `canCreate`, `canRead`, `canUpdate`, `canDelete` booleans.

## Roles (23 Predefined)

### Staff Level (scope: self)

| Role Key | Name | CRUD | Description |
|----------|------|------|-------------|
| `broker` | Broker | r | Default role — view own records only |
| `senior_broker` | Senior Broker | cru | Create and edit own records |

### Team Level (scope: team)

| Role Key | Name | CRUD | Description |
|----------|------|------|-------------|
| `team_leader` | Team Leader | cru | View and manage team records |
| `sales_manager` | Sales Manager | crud | Full control of sales team records |
| `office_manager` | Office Manager | crud | Full control of office team records |
| `marketing_manager` | Marketing Manager | cru | Manage marketing team records |
| `operations_manager` | Operations Manager | crud | Manage operations team records |
| `hr_manager` | HR Manager | crud | Manage HR team records |
| `it_support` | IT Support | cru | IT support with team visibility |
| `finance_officer` | Finance Officer | cru | Finance team member with team visibility |
| `bu_ceo` | BU CEO | crud | Business unit CEO — manage BU teams |
| `bu_ceo_hr` | BU CEO HR | crud | BU CEO with HR oversight responsibilities |

### Director Level (scope: global)

| Role Key | Name | CRUD | Description |
|----------|------|------|-------------|
| `sales_director` | Sales Director | crud | Global sales oversight across all teams |
| `marketing_director` | Marketing Director | crud | Global marketing oversight across all teams |
| `operations_director` | Operations Director | crud | Global operations oversight |
| `hr_director` | HR Director | crud | Global HR oversight across all teams |
| `finance_director` | Finance Director | crud | Global finance oversight |
| `it_director` | IT Director | crud | Global IT oversight |

### C-Suite Level (scope: global)

| Role Key | Name | CRUD | Description |
|----------|------|------|-------------|
| `coo` | COO | crud | Chief Operating Officer — full operational access |
| `cfo` | CFO | crud | Chief Financial Officer — full financial access |
| `ceo` | CEO | crud | Chief Executive Officer — full access |

### Admin Level (scope: org_admin / system_admin)

| Role Key | Name | Scope | CRUD | Description |
|----------|------|-------|------|-------------|
| `org_admin` | Organization Admin | org_admin | crud | Organization-wide admin with full access |
| `system_admin` | System Admin | system_admin | crud | System administrator with full cross-tenant access |

## JWT Claims Structure

The `oauth-token` Edge Function produces this JWT payload, consumed by all Matrix Apps and all RLS policies:

```typescript
{
  sub: string;                     // User UUID (permanent ID across all apps)
  email: string;                   // User email

  // Role & Access
  sso_role: {                      // Active role
    id: string;                    //   Role UUID
    name: string;                  //   "Sales Manager"
  };
  scope: {                         // Access scope
    id: string;                    //   "team"
    name: string;                  //   "Team"
  };
  crud: string;                    // "crud" | "cr" | "r" | etc.

  // Organization & Teams
  uoi: string;                     // Tenant UUID (organization ID)
  organization: {
    id: string;                    // Tenant UUID
    name: string;                  // "Sharp Sotheby's"
  };
  teams: Array<{                   // Team memberships
    id: string;
    name: string;
  }>;
  team_ids: string[];              // Team UUIDs (flat array for RLS)

  // App Access
  allowed_apps: Array<{            // Apps this user can access
    id: string;
    name: string;
  }>;
  available_roles: Array<{         // All roles user can switch to
    uuid: string;
    name: string;
    scope: string;
    is_primary: boolean;
  }>;

  // Legacy (backward compat)
  permissions: string[];           // ["app_access", "org_admin"]
  groups: string[];                // Group names
  member_type: string;             // "Broker" | "Staff" | "OfficeManager" | etc.
}
```

## RLS Helper Functions

All functions are `STABLE` with `SET search_path = public` for security and performance. Wrap calls in `(SELECT func())` in RLS policies for initPlan caching.

| Function | Returns | Purpose |
|----------|---------|---------|
| `get_current_tenant_id()` | `uuid` | Tenant UUID from JWT `uoi` claim — used in every RLS policy for tenant isolation |
| `get_active_scope()` | `text` | Scope string — defaults to `'self'` if missing. Falls back to `app_metadata` on CDL. |
| `get_crud()` | `text` | CRUD permission string (e.g., `"crud"`, `"cr"`, `"r"`). Falls back to `app_metadata` on CDL. |
| `get_current_user_id()` | `uuid` | SSO User UUID from JWT `sub` claim |
| `get_current_team_ids()` | `uuid[]` | Array of team UUIDs. Falls back to `app_metadata` on CDL. |
| `is_sso_admin_v2()` | `boolean` | `true` if scope is `org_admin` or `system_admin` (`SECURITY DEFINER`) |
| `is_in_my_teams(user_id)` | `boolean` | (CDL) `true` if `user_id` shares a team with the current JWT user via `sso_user_group_memberships` (`SECURITY DEFINER`) |
| `update_updated_at_column()` | trigger | Auto-sets `updated_at = now()` on UPDATE |

### app_metadata Fallback (CDL Instance)

On the CDL instance, three RLS helpers have a **fallback to `auth.users.raw_app_meta_data`**. This is critical because CDL-Connected apps (e.g., MLS) use **Supabase native tokens** for PostgREST calls (signed with the project JWT secret, which PostgREST accepts). These native tokens don't contain custom SSO claims like `scope`, `crud`, or `team_ids`.

The `oauth-token` Edge Function persists these claims to the user's `app_metadata` during login and token refresh:

```
oauth-token → auth.users.raw_app_meta_data:
  active_scope   = "system_admin" | "org_admin" | "global" | "team" | "self"
  active_crud    = "crud" | "cr" | "r" | etc.
  active_team_ids = ["uuid1", "uuid2", ...]
```

The RLS helpers then resolve claims in this priority order:
1. JWT claims (`current_setting('request.jwt.claims')`) — works with SSO JWTs
2. `auth.users.raw_app_meta_data` — works with Supabase native tokens
3. Default value (`'self'` for scope, `''` for crud, `'{}'` for team_ids)

### SQL Implementations

```sql
-- get_current_tenant_id()
SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'uoi', '')::uuid;

-- get_active_scope() — CDL version with app_metadata fallback (SECURITY DEFINER)
SELECT coalesce(
  nullif(current_setting('request.jwt.claims', true)::json->'scope'->>'id', ''),
  nullif(current_setting('request.jwt.claims', true)::json->>'scope', ''),
  (SELECT raw_app_meta_data->>'active_scope' FROM auth.users WHERE id = auth.uid()),
  'self'
);

-- get_crud() — CDL version with app_metadata fallback (SECURITY DEFINER)
SELECT coalesce(
  nullif(current_setting('request.jwt.claims', true)::json->>'crud', ''),
  (SELECT raw_app_meta_data->>'active_crud' FROM auth.users WHERE id = auth.uid()),
  ''
);

-- get_current_user_id()
SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid;

-- get_current_team_ids() — CDL version with app_metadata fallback (SECURITY DEFINER)
SELECT coalesce(
  ARRAY(SELECT (value)::uuid FROM json_array_elements_text(
    COALESCE(current_setting('request.jwt.claims', true)::json->'team_ids', '[]'::json)
  )),
  (SELECT ARRAY(SELECT (jsonb_array_elements_text(
    coalesce(raw_app_meta_data->'active_team_ids', '[]'::jsonb)
  ))::uuid) FROM auth.users WHERE id = auth.uid()),
  '{}'::uuid[]
);

-- is_sso_admin_v2() — SECURITY DEFINER
SELECT COALESCE(
  (SELECT COALESCE(
    current_setting('request.jwt.claims', true)::json->'scope'->>'id',
    current_setting('request.jwt.claims', true)::json->>'scope'
  ) IN ('system_admin', 'org_admin')),
  false
);

-- is_in_my_teams(target_user_id) — CDL only, SECURITY DEFINER
SELECT EXISTS (
  SELECT 1 FROM sso_user_group_memberships m
  WHERE m.user_id = target_user_id
    AND m.group_id = ANY(get_current_team_ids())
);
```

> **App DB instances** use the simpler JWT-only versions (no `app_metadata` fallback) because they receive the SSO JWT directly via `accessToken` hook.

### Team-Scope Resolution

The `team` scope requires checking whether a record's owner is in the same team as the current user. Two resolver functions exist for different contexts:

| Function | Location | Resolution Method | Used By |
|----------|----------|------------------|---------|
| `is_my_direct_report_v2(target_id)` | App DB | Checks manager-subordinate hierarchy via app's manager table | HRMS (employees) |
| `is_in_my_teams(user_id)` | CDL | Checks shared team membership via `sso_user_group_memberships` | MLS (listings, contacts) |

Apps deploying tables to CDL should use `is_in_my_teams()`. Apps with their own DB should create an app-specific `get_my_record_id_v2()` and `is_my_direct_report_v2()` following the template in `001_sso_helper_functions.sql`.

### Legacy CDL Functions (Backward Compatibility)

The CDL instance also has legacy helper functions used by older apps (`matrix-client-connect`, `matrix-meeting-hub`). These are kept for backward compatibility and should NOT be used by new apps:

| Legacy Function | New Equivalent |
|----------------|---------------|
| `get_my_tenant_id()` | `get_current_tenant_id()` (note: `get_my_tenant_id()` has a 4-step fallback and is still used by MLS for compatibility) |
| `is_admin()` / `has_rw_global_permission()` | `(SELECT get_active_scope()) IN ('org_admin', 'system_admin')` for admin ops; `get_crud() LIKE '%u%'` for write checks |
| `can_access_all_tenant_data()` | `get_active_scope() IN ('global', 'org_admin', 'system_admin')` |
| `is_manager_or_above()` | `get_active_scope() IN ('team', 'global', 'org_admin', 'system_admin')` |

## RLS Policy Patterns

From `matrix-apps-template/supabase/migrations/003_data_model_template.sql`:

| Pattern | Use Case | Logic Summary |
|---------|----------|---------------|
| **A** | Reference tables (lookups, types) | Tenant isolation + CRUD check; admin-only write |
| **B** | User-owned records (listings, contacts, deals) | Self: own records; Team: own + direct reports; Global+: all in tenant |
| **C** | Tenant-wide records (shared config, announcements) | All records in tenant for anyone with read access |
| **D** | Admin-only tables (audit, configuration) | Full CRUD restricted to `org_admin` / `system_admin` |
| **E** | System tables (cross-tenant) | Cross-tenant access for `system_admin` only |

### Pattern B (most common) — scope-aware SELECT

This is the workhorse pattern used for any table where record ownership matters:

```sql
CASE (SELECT get_active_scope())
  WHEN 'system_admin' THEN true
  WHEN 'org_admin'    THEN tenant_id = (SELECT get_current_tenant_id())
  WHEN 'global'       THEN tenant_id = (SELECT get_current_tenant_id())
  WHEN 'team'         THEN tenant_id = (SELECT get_current_tenant_id())
                       AND (owner_id = (SELECT get_my_record_id_v2())
                            OR (SELECT is_my_direct_report_v2(owner_id)))
  WHEN 'self'         THEN tenant_id = (SELECT get_current_tenant_id())
                       AND owner_id = (SELECT get_my_record_id_v2())
  ELSE false
END
```

## `role_configurations` Table

Each app has this table in its App DB instance. It maps SSO roles to app-specific page and action access.

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid PK | Auto-generated |
| `role_id` | text | SSO role UUID from `sso_roles.id` |
| `pages` | text[] | Array of page keys (e.g., `['home', 'listings', 'contacts']`) |
| `actions` | text[] | Array of action keys (e.g., `['create', 'edit', 'delete']`) |
| `tenant_id` | uuid | Multi-tenant support |

**Wildcard**: `pages: ['*']` or `actions: ['*']` grants full access.

**Auto-bootstrap**: If the table is empty and the user has admin scope, the app auto-inserts the current role with `['*']` for both pages and actions. Once any config exists, strict mode applies.

## Platform-Standard Page Keys

Apps use `role_configurations.pages` to control which pages each role can access. Apps may add domain-specific keys.

| Category | Keys |
|----------|------|
| **Account** (all apps) | `home`, `profile`, `settings`, `design-showcase` |
| **Real Estate** (CDL-Connected) | `listings`, `listing-detail`, `listing-create`, `listing-edit`, `properties`, `showings`, `open-houses` |
| **CRM** (CDL-Connected) | `contacts`, `contact-detail`, `leads`, `opportunities`, `pipeline`, `deals` |
| **Marketing** | `campaigns`, `analytics`, `reports`, `marketing-dashboard` |
| **Operations** | `team-dashboard`, `team-management`, `calendar`, `tasks` |
| **Admin** | `users`, `roles`, `permissions`, `tenants`, `applications`, `audit-log` |
| **HR** (HRMS) | `directory`, `org-structure`, `personnel`, `onboarding`, `offboarding`, `vacations`, `vacations-admin`, `performance`, `my-performance`, `compensation`, `documents`, `my-documents`, `changes`, `social`, `hr-dashboard` |
| **Finance** | `invoices`, `commissions`, `payments`, `finance-dashboard`, `finance-reports` |

## Platform-Standard Action Keys

| Action Key | Description |
|------------|-------------|
| `create` | Create new records |
| `edit` | Edit existing records |
| `delete` | Delete records |
| `export` | Export data (CSV, PDF) |
| `import` | Bulk data import |
| `approve` | Approve requests/workflows |
| `reject` | Reject requests/workflows |
| `assign` | Assign records to users/teams |
| `archive` | Archive records (soft delete) |

## App-Side Hooks

| Hook | Returns | Usage |
|------|---------|-------|
| `useAuth()` | user, roles, tenant, scope, crud, teams, isLoading | Global auth state |
| `useActiveRole()` | canCreate, canRead, canUpdate, canDelete, scope | Per-action permission checks |
| `useRoleConfig()` | canAccessPage(pageKey), canPerformAction(actionKey) | Page/route/action guards |

## Role-to-Page Mapping Example (HRMS)

| Role | Scope | Pages | Actions |
|------|-------|-------|---------|
| System Admin | system_admin | `['*']` | `['*']` |
| Organization Admin | org_admin | `['*']` | `['*']` |
| HR Director | global | home, directory, profile, org-structure, onboarding, offboarding, vacations, vacations-admin, performance, compensation, documents, reports, settings | create, edit, delete, export |
| HR Manager | team | home, directory, profile, org-structure, onboarding, offboarding, vacations, vacations-admin, reports | create, edit, delete |
| Sales Director | global | home, directory, profile, org-structure, reports, settings | create, edit, delete, export |
| Broker | self | home, directory, profile | (none) |

## How-To Guides

### Add a New Role

1. Insert into `sso_roles` via SSO Console or `admin-roles` Edge Function
2. Assign to users via `user_role_assignments`
3. Configure page/action access in each app's `role_configurations` table

### Add a New Page Key

1. Add the page key to the app's `RoleConfigPanel.tsx` → `PAGE_GROUPS` array
2. Add matching `pageKey` to sidebar items in `AppSidebar.tsx`
3. Add `requiredPage` to the route's `ProtectedRoute` wrapper
4. Configure which roles see this page in `role_configurations`

### Add a New Action Key

1. Add the action key to the app's `RoleConfigPanel.tsx` → `ALL_ACTIONS` array
2. Use `canPerformAction('action-key')` in component logic
3. Configure which roles can perform this action in `role_configurations`

## Cross-Reference

| For | See |
|-----|-----|
| How apps consume auth/permissions | [app-template.md](app-template.md) |
| App catalog with per-app RESO resource access | [app-catalog.md](app-catalog.md) |
| Full ecosystem architecture | [ecosystem-architecture.md](ecosystem-architecture.md) |
| Compliance and data protection | [compliance.md](compliance.md) |
