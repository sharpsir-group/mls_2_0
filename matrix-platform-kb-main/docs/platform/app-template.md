# Matrix App Template — How to Build Sharp Matrix Apps

> Source: `/home/bitnami/matrix-apps-template` (starter kit)
> Example: `/home/bitnami/matrix-hrms` (production app in development)
>
> **For Lovable**: Read this document before building ANY Matrix App. It defines the
> exact patterns, conventions, and architecture you must follow.

## Two Types of Matrix Apps

Before building, determine which type of app you're creating:

| Type | CDL Usage | App DB Usage | Example |
|------|-----------|-------------|---------|
| **CDL-Connected** | Reads/writes shared RESO tables (Property, Member, Contacts) | May have some app-specific tables | Broker App, Manager App, Client Portal, Marketing App |
| **Domain-Specific** | Only uses CDL for auth/permissions/tenants | Has its own Supabase instance with domain tables | HRMS (employees, vacations), Finance App |

**Decision rule**: If your app works with real estate listings, contacts, agents, or showings → CDL-Connected. If your app has its own domain (HR, finance, operations) → Domain-Specific.

**What stays the same in BOTH types:**
- Dual-Supabase architecture (SSO instance + App DB instance)
- SSO auth (OAuth 2.0 + PKCE + JWT)
- Permission model (5-level scope + CRUD + page/action access)
- RLS patterns (A-E)
- UI framework (shadcn/ui + Tailwind + Sharp design system)
- Data fetching (Supabase client + React Query)
- Routing (React Router v6 + ProtectedRoute)
- i18n (i18next EN/RU)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Vite + React 18 + TypeScript |
| UI | shadcn/ui (60+ Radix components) + Tailwind CSS |
| Design | Sharp design system: Navy palette, Playfair Display (headings) + Inter (body) |
| Data | `@supabase/supabase-js` v2 + TanStack Query (React Query) |
| Auth | Custom SSO (OAuth 2.0 + PKCE) via Supabase Edge Functions |
| i18n | i18next (EN/RU) |
| Routing | React Router v6 with `ProtectedRoute` guards |

## Dual-Supabase Architecture

Every Matrix App connects to **two Supabase instances**:

| Instance | Project ID | Client File | Purpose |
|----------|-----------|-------------|---------|
| **SSO / CDL** | `xgubaguglsnokjyudgvc` | `src/integrations/supabase/dataLayerClient.ts` | Authentication, permissions, tenants, shared data |
| **App Database** | Per-app (e.g., HRMS: `wltuhltnwhudgkkdsvsr`) | `src/integrations/supabase/client.ts` | App-specific business data with RLS |

### SSO Instance Tables

| Table | Purpose |
|-------|---------|
| `ad_users` | Azure AD user directory cache |
| `tenants` | Organization/tenant records |
| `app_settings` | Per-tenant app configuration (JSON) |
| `sso_user_groups` | Team/group memberships |
| `role_configurations` | Per-role page and action access lists |

### App DB Client Setup

The app database client injects the SSO JWT for RLS:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  global: {
    headers: { 'x-sso-email': userEmail },
  },
  accessToken: async () => ssoAccessToken,
});
```

The `accessToken` hook injects the SSO JWT into every request. RLS policies read claims from `current_setting('request.jwt.claims')`.

### CDL Client Setup (for CDL-Connected Apps)

CDL-Connected apps (e.g., MLS) make PostgREST calls to the shared CDL instance. These calls use the **Supabase native token** (signed with the CDL project's JWT secret), not the SSO JWT. This is because PostgREST validates tokens against its own project JWT secret.

```typescript
// dataLayerClient.ts — prioritize Supabase native token for PostgREST
const accessToken = localStorage.getItem('matrix_supabase_access_token')
  || MatrixSSOStorage.getAccessToken();  // SSO JWT fallback
const cdlClient = createClient(CDL_URL, CDL_ANON_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
  global: { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} },
});
```

**How RLS claims reach PostgREST**: The `oauth-token` Edge Function persists `active_scope`, `active_crud`, and `active_team_ids` to the user's `app_metadata` (`auth.users.raw_app_meta_data`). CDL RLS helper functions fall back to `app_metadata` when JWT claims aren't present. See [security-model.md](security-model.md#app_metadata-fallback-cdl-instance).

### CDL Write Proxy (Edge Function Pattern)

CDL-Connected apps proxy write operations through an Edge Function to avoid CORS and maintain a clean security boundary:

```
App UI → cdlWrite.ts → supabase.functions.invoke('cdl-write') → CDL PostgREST
```

The `cdl-write` Edge Function on the app's Supabase instance:
1. Receives the operation, table, data, and the user's Supabase native token
2. Creates a CDL client with that token as the Authorization header
3. Executes the operation on the CDL instance
4. Returns the result (with `_debug` info on errors)

## SSO Auth Flow

1. App redirects to `https://intranet.sharpsir.group/sso-login/` with PKCE code challenge
2. User authenticates via Azure AD
3. Callback at `/auth/callback` exchanges authorization code for JWT via `oauth-token` Edge Function
4. Tokens stored in `localStorage`:
   - `matrix_sso_access_token` — SSO JWT (custom claims: scope, crud, team_ids, uoi)
   - `matrix_sso_refresh_token` — for token renewal
   - `matrix_supabase_access_token` — Supabase native token (for CDL PostgREST calls)
5. `oauth-token` also persists `active_scope`, `active_crud`, `active_team_ids` to user's `app_metadata` (enables RLS for native token)
6. SSO JWT injected into App DB client via `accessToken` hook; native token used for CDL client
7. Proactive token refresh at 80% of expiry time (also refreshes `app_metadata`)

### JWT Claims Structure

```typescript
{
  sub: string;                     // User UUID (permanent ID across all apps)
  email: string;                   // User email
  sso_role: { id: string; name: string };   // Active role (object, not string)
  scope: { id: string; name: string };      // Access scope (object, not string)
  crud: string;                    // "crud" | "cr" | "r" | "ru" | etc. (c/r/u/d letters)
  uoi: string;                     // Tenant UUID (organization ID)
  teams: Array<{ id: string; name: string }>;  // Team memberships
  team_ids: string[];              // Team UUIDs (flat array for RLS)
  allowed_apps: Array<{ id: string; name: string }>;  // Apps user can access
}
```

> See [security-model.md](security-model.md) for the full JWT claims structure with all fields.

### SSO Edge Functions Called

| Function | When Called |
|----------|-----------|
| `oauth-authorize` | Initiating login redirect |
| `oauth-token` | Exchanging auth code for JWT |
| `oauth-userinfo` | Fetching user info with claims |
| `switch-role` | User switches active role → re-issues JWT |
| `admin-ad-users` | Querying Azure AD user directory |

### Lovable Environment Detection

```typescript
function isLovableEnvironment(): boolean {
  const host = window.location.hostname;
  return host.includes('lovable.dev')
      || host.includes('lovable.app')
      || host.includes('lovableproject.com');
}
```

In Lovable dev mode: uses in-app login (bypasses external SSO redirect).
In production: redirects to external SSO login page.

## Permission Model

### 5-Level Scope Hierarchy

```
self → team → global → org_admin → system_admin
```

| Scope | Sees |
|-------|------|
| `self` | Own records only |
| `team` | Own records + team members' records |
| `global` | All records in tenant |
| `org_admin` | Full tenant access + admin functions |
| `system_admin` | Cross-tenant access |

### CRUD Permission String

Format: any combination of `c`, `r`, `u`, `d`.

| Value | Meaning |
|-------|---------|
| `r` | Read only |
| `cr` | Create + Read |
| `crud` | Full access |
| `ru` | Read + Update (no create, no delete) |

### Auth Hooks

| Hook | Returns | Usage |
|------|---------|-------|
| `useAuth()` | `user`, `roles`, `tenant`, `scope`, `crud`, `teams`, `isLoading` | Global auth state |
| `useActiveRole()` | `canCreate`, `canRead`, `canUpdate`, `canDelete`, `scope` | Per-action permission checks |
| `useRoleConfig()` | `canAccessPage(pageKey)`, `canPerformAction(actionKey)` | Page/route/action guards |

### Usage Patterns

```typescript
// Check if user can create records
const { canCreate, scope } = useActiveRole();
if (!canCreate) return <AccessDenied />;

// Check if user can access a page
const { canAccessPage } = useRoleConfig();
if (!canAccessPage('hr-dashboard')) return <NotFound />;

// Scope-aware data filtering (automatic via RLS, but useful for UI)
if (scope === 'self') showOnlyMyRecords();
if (scope === 'team') showTeamRecords();
if (scope === 'global') showAllRecords();
```

## Data Fetching Pattern

All data queries use Supabase client + TanStack React Query:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

// READ
const { data, isLoading, error } = useQuery({
  queryKey: ['employees'],
  queryFn: async () => {
    const { data, error } = await supabase
      .from('employees')
      .select('*')
      .order('last_name');
    if (error) throw error;
    return data;
  },
});

// CREATE
const queryClient = useQueryClient();
const createMutation = useMutation({
  mutationFn: async (newEmployee: EmployeeInsert) => {
    const { data, error } = await supabase
      .from('employees')
      .insert(newEmployee)
      .select()
      .single();
    if (error) throw error;
    return data;
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['employees'] });
  },
});
```

## RLS Migration Patterns

From `supabase/migrations/003_data_model_template.sql` — use the correct pattern for each table:

| Pattern | Scope | When to Use | SQL Policy Logic |
|---------|-------|-------------|-----------------|
| **A** | Self | User sees only own records | `WHERE user_id = get_my_user_id()` |
| **B** | Team | User sees team records | `WHERE team_id = ANY(get_my_team_ids())` |
| **C** | Global | All records in tenant | `WHERE tenant_id = get_current_tenant_id()` |
| **D** | Org-admin | Full tenant CRUD | `WHERE tenant_id = get_current_tenant_id() AND is_org_admin()` |
| **E** | System-admin | Cross-tenant | `WHERE is_system_admin()` |

RLS helper functions (available on both App DB and CDL instances):
- `get_current_tenant_id()` — extracts tenant UUID from JWT `uoi` claim
- `get_active_scope()` — extracts scope from JWT; **on CDL: falls back to `app_metadata`** for Supabase native tokens
- `get_crud()` — extracts CRUD string from JWT; **on CDL: falls back to `app_metadata`**
- `get_current_user_id()` — extracts SSO user UUID from JWT `sub` claim
- `get_current_team_ids()` — extracts team UUID array; **on CDL: falls back to `app_metadata`**
- `is_sso_admin_v2()` — returns true if scope is `org_admin` or `system_admin`
- `is_in_my_teams(user_id)` — (CDL only) checks if user shares a team via `sso_user_group_memberships`

> **CDL Token Architecture:** CDL-Connected apps use Supabase native tokens (signed with the project
> JWT secret) for PostgREST calls. These tokens don't carry custom SSO claims, so CDL RLS helpers
> fall back to `auth.users.raw_app_meta_data` where `oauth-token` persists `active_scope`, `active_crud`,
> and `active_team_ids`. See [security-model.md](security-model.md#app_metadata-fallback-cdl-instance).
>
> **Legacy Functions:** The CDL also has `is_admin()`, `has_rw_global_permission()`, `can_access_all_tenant_data()`, etc. for backward compatibility with older apps (meeting-hub, client-connect). New apps should use Pattern A-E with the functions listed above.

## UI Conventions

### Layout

Every page uses `SidebarLayout`:

```tsx
import SidebarLayout from '@/layouts/SidebarLayout';

export default function MyPage() {
  return (
    <SidebarLayout>
      <div className="p-6">
        {/* Page content */}
      </div>
    </SidebarLayout>
  );
}
```

### Route Protection

Every route uses `ProtectedRoute` with a `requiredPage` key:

```tsx
<Route
  path="/hr-dashboard"
  element={
    <ProtectedRoute requiredPage="hr-dashboard">
      <HRDashboard />
    </ProtectedRoute>
  }
/>
```

The `requiredPage` key is checked against `role_configurations.pages` for the user's role.

### Sidebar Structure

The sidebar is defined in `AppSidebar.tsx` as an array of sections. Each item has a `pageKey` for permission-based visibility:

```typescript
const sidebarSections = [
  {
    title: 'Employee',
    items: [
      { title: 'My Dashboard', url: '/', icon: Home, pageKey: 'home' },
      { title: 'My Vacations', url: '/my-vacations', icon: Calendar, pageKey: 'my-vacations', countKey: 'myVacations' },
    ],
  },
  {
    title: 'Human Resources',
    requiredScope: 'global', // Section only visible to global+ scope
    items: [
      { title: 'Personnel', url: '/personnel', icon: Users, pageKey: 'personnel' },
    ],
  },
];
```

### Sharp Design System

| Element | Value |
|---------|-------|
| Primary color | Navy/Blue (HSL variables in `index.css`) |
| Heading font | Playfair Display |
| Body font | Inter |
| Sidebar | Dark navy background |
| Components | shadcn/ui with Radix primitives |

## i18n Pattern

```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  return <h1>{t('settings.title')}</h1>;
}
```

Supported languages: English (`en`), Russian (`ru`).
Language detected from `localStorage` or browser `navigator.language`.

## Lovable-Specific Rules

| Rule | Detail |
|------|--------|
| No `.env` files | All configuration hardcoded in `matrix-sso.ts` (Lovable doesn't support `.env`) |
| Environment detection | `isLovableEnvironment()` for dev vs production behavior |
| Component tagger | `lovable-tagger` Vite plugin in dev mode for AI component understanding |
| TypeScript strictness | Relaxed for Lovable compatibility |
| `CLIENT_ID` | Must be updated in `matrix-sso.ts` after app registration in SSO Console |
| `BASE_PATH` | Set in `matrix-sso.ts` for production subdirectory routing |

## Real App Example: Matrix HRMS

Source: `/home/bitnami/matrix-hrms` — a Domain-Specific app built from the template.

### What HRMS Added Beyond the Template

| Category | Template | HRMS |
|----------|----------|------|
| Database tables | 2 (`notifications`, `role_configurations`) | 25+ domain tables |
| Custom hooks | ~5 | 30+ |
| Pages | 4 (home, auth, callback, settings) | 20+ organized by role |
| Sidebar sections | 1 | 4 (Employee, Organization, Manager, HR Admin) |

### HRMS Domain Tables

**Employee management**: `employees`, `departments`, `locations`, `employee_managers`, `employee_ad_links`

**Leave management**: `vacations`, `vacation_balances`, `leave_policies`, `public_holidays`

**Performance**: `review_cycles`, `review_participants`, `goals`

**Onboarding/Offboarding**: `onboarding_templates`, `onboarding_template_tasks`, `onboarding_checklists`, `onboarding_tasks`, `offboarding_templates`, `offboarding_template_tasks`, `offboarding_checklists`, `offboarding_tasks`

**Compensation**: `compensation_history`, `payroll_records`

**Documents**: `document_templates`, `document_distributions`, `employee_documents`

**Other**: `internal_changes`, `social_posts`, `social_comments`, `social_reactions`, `employee_agreements`, `employee_edit_requests`

### Key Patterns from HRMS

**Approval workflow** (`internal_changes`):
- Status flow: `pending` → `approved` → `applied` (or `rejected`)
- Manager approves, HR applies changes to employee record
- IF status = 'approved' AND role = 'hr_admin' THEN apply changes to `employees` table

**Template-based processes** (onboarding):
- `onboarding_templates` → defines reusable task lists
- `onboarding_checklists` → instance of a template for a specific employee
- `onboarding_tasks` → individual tasks within a checklist, tracked to completion

**Role-based sidebar sections**:
- Employee section: visible to all (scope = self+)
- Manager section: visible when user has direct reports (scope = team+)
- HR Admin section: visible to global+ scope with HR role

**Directory view with privacy** (`employee_directory`):
- Database VIEW that masks sensitive columns (salary, personal phone, etc.)
- Public queries use the view; admin queries use the full `employees` table

### HRMS Supabase Instance

| Instance | Project ID | Purpose |
|----------|-----------|---------|
| SSO | `xgubaguglsnokjyudgvc` | Auth, permissions, AD users, tenants |
| HRMS App DB | `wltuhltnwhudgkkdsvsr` | All HR tables, RLS enforced via SSO JWT |

## Key Files Reference

### In `matrix-apps-template`

| File | Purpose |
|------|---------|
| `src/App.tsx` | Root component, route definitions |
| `src/main.tsx` | Entry point, QueryClient + i18n setup |
| `src/index.css` | Sharp design system CSS variables |
| `src/lib/matrix-sso.ts` | SSO client (1000+ lines): OAuth, JWT, refresh, config |
| `src/contexts/AuthContext.tsx` | React auth context provider |
| `src/components/ProtectedRoute.tsx` | Route guard with permission checks |
| `src/integrations/supabase/client.ts` | App DB Supabase client |
| `src/integrations/supabase/dataLayerClient.ts` | SSO/CDL Supabase client |
| `src/integrations/supabase/types.ts` | App DB TypeScript types (auto-generated) |
| `src/integrations/supabase/dataLayerTypes.ts` | SSO/CDL TypeScript types |
| `src/hooks/useActiveRole.ts` | CRUD permission helpers |
| `src/hooks/useRoleConfig.ts` | Page/action permission checks |
| `src/components/AppSidebar.tsx` | Main sidebar with role-based sections |
| `src/layouts/SidebarLayout.tsx` | Layout wrapper (sidebar + content) |
| `supabase/migrations/001_sso_helper_functions.sql` | RLS helper functions |
| `supabase/migrations/003_data_model_template.sql` | 5 RLS patterns (A-E) |

### In `matrix-hrms` (Domain-Specific example)

| File | What It Shows |
|------|--------------|
| `src/hooks/useEmployees.ts` | Querying employee directory with scope-aware filtering |
| `src/hooks/useVacations.ts` | CRUD operations with approval workflow |
| `src/hooks/useOnboarding.ts` | Template-based process management |
| `src/hooks/useInternalChanges.ts` | Change request workflow (create, approve, apply) |
| `src/hooks/useRoleConfig.ts` | Extended page/action permissions |
| `src/components/AppSidebar.tsx` | 4-section sidebar with badge counts and role-based visibility |

### In `matrix-mls` (CDL-Connected example)

| File | What It Shows |
|------|--------------|
| `src/lib/cdlWrite.ts` | CDL write helper — sends operations via `cdl-write` Edge Function with native token |
| `src/integrations/supabase/dataLayerClient.ts` | CDL read client — prioritizes Supabase native token for PostgREST |
| `supabase/functions/cdl-write/index.ts` | Edge Function proxy — table allowlist, conflict resolution, error `_debug` |
| `src/components/settings/DevToolsPanel.tsx` | Test data seeder — seeds 18 tables with SEED-prefixed records |
| `src/pages/AuthCallback.tsx` | Stores `supabase_access_token` from `oauth-token` into localStorage |
| `src/hooks/useActiveRole.ts` | `canCreate`/`canRead`/`canUpdate`/`canDelete` + `isAdmin`, `isGlobalOrAbove` |

## Common Pitfalls (LLM Guidance)

These are hard-learned lessons. Violating any of them will cause silent failures.

### 1. Never use SSO JWT for CDL PostgREST calls

**Wrong**: Send `MatrixSSOStorage.getAccessToken()` (SSO JWT) to CDL PostgREST.
**Why it fails**: PostgREST validates tokens against the **project's own JWT secret**, not the SSO `JWT_SECRET`. The SSO JWT is signed with a different key → `PGRST301: No suitable key or wrong key type`.
**Correct**: Use `localStorage.getItem('matrix_supabase_access_token')` (Supabase native token). This token is issued by Supabase Auth and signed with the correct project key.

### 2. CDL RLS helpers MUST have app_metadata fallback

**Wrong**: RLS helpers that only read `current_setting('request.jwt.claims')`.
**Why it fails**: Supabase native tokens don't contain custom SSO claims (`scope`, `crud`, `team_ids`). The functions return NULL → all RLS policies block access → empty query results.
**Correct**: CDL RLS helpers must fall back to `auth.users.raw_app_meta_data` where `oauth-token` persists these claims. Use `SECURITY DEFINER` to access `auth.users`.

### 3. oauth-token MUST persist claims to app_metadata

**Wrong**: `oauth-token` only returns tokens in the response body.
**Why it fails**: If claims aren't persisted to `app_metadata`, the RLS fallback has nothing to read.
**Correct**: After resolving the user's active role, scope, CRUD, and teams, persist them:
```typescript
await supabase.auth.admin.updateUserById(userId, {
  app_metadata: { ...existing, active_scope, active_crud, active_team_ids }
});
```

### 4. CDL writes need an Edge Function proxy

**Wrong**: Call CDL PostgREST directly from the browser.
**Why it fails**: CORS blocks cross-origin Supabase requests from `lovable.dev` to the CDL instance.
**Correct**: Route writes through an Edge Function on the app's own Supabase instance. The Edge Function creates a CDL client with the user's token and forwards the operation.

### 5. Don't conflate scope with admin privileges

**Wrong**: Treating `global` scope as admin for write operations on config tables.
**Why it fails**: `global` means visibility (see all records in tenant), not admin privileges. A Sales Director with `global` scope should NOT be able to modify checklist templates or document type configs.
**Correct**: Restrict config table writes to `(SELECT get_active_scope()) IN ('org_admin', 'system_admin')`.

### 6. Use `get_my_tenant_id()` (not `get_current_tenant_id()`) on CDL

**Wrong**: Using `get_current_tenant_id()` on CDL (only reads JWT `uoi` claim).
**Why it fails**: Legacy apps and some token types don't have the `uoi` claim.
**Correct**: CDL uses `get_my_tenant_id()` which has a 4-step fallback: `uoi` → `user_metadata.tenant_id` → `auth.users` → `admin_settings`.
