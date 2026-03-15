# O365 Exchange Integration — Email & Calendar

> Source: Microsoft Graph API v1.0, Azure AD App Registration, `matrix-platform-foundation/supabase/functions/_shared/microsoft-graph.ts`
>
> **For Lovable**: This document defines how Matrix Apps (Broker App, Manager App) integrate
> with Microsoft 365 Exchange Online to read emails, attach them to opportunities, and
> synchronize calendar events (viewings, meetings, follow-ups) with Outlook.
> Prerequisite reading: [app-template.md](app-template.md), [security-model.md](security-model.md).

## Overview

The Sharp Matrix Platform extends its existing Azure AD integration (SSO + profile sync) to include **Exchange Online** capabilities via Microsoft Graph API:

| Capability | Purpose | Graph API Scope |
|-----------|---------|-----------------|
| **Email read** | Broker reads their Exchange inbox from within CRM | `Mail.Read` (delegated) |
| **Email attach** | Link an email snapshot to an opportunity record | `Mail.Read` (delegated) |
| **Calendar read** | Display broker's Outlook calendar in CRM | `Calendars.ReadWrite` (delegated) |
| **Calendar write** | Create viewings/meetings in Outlook from CRM | `Calendars.ReadWrite` (delegated) |
| **Calendar respond** | Accept/decline meeting invitations from CRM | `Calendars.ReadWrite` (delegated) |
| **Free/busy check** | Detect scheduling conflicts before booking | `Calendars.ReadWrite` (delegated) |

All operations use **delegated permissions** — each broker accesses only their own mailbox and calendar. There is no admin-level or application-level mail/calendar access.

## Existing Azure AD Foundation

The platform already has Azure AD integration for authentication and profile sync:

| Component | Location | Current Scopes |
|-----------|----------|---------------|
| Azure AD OAuth config | `admin_settings.oauth_config` (SSO DB) | `openid profile email User.Read` |
| App-only credentials | `admin_settings.oauth_config` (client_id, client_secret, tenant_id) | `User.Read.All` (app-only, for AD sync) |
| Profile sync | `sync-azure-profile` Edge Function | `User.Read` (delegated via provider_token) |
| AD user sync | `sync-ad-users` Edge Function | `User.Read.All` (app-only) |
| Graph helpers | `_shared/microsoft-graph.ts` | Profile + photo fetch only |

The O365 integration **extends** this foundation — it does not replace it.

## Azure AD App Registration Changes

### Additional Delegated Permissions

Add the following delegated permissions to the existing Azure AD app registration:

| Permission | Type | Purpose | Admin Consent |
|-----------|------|---------|---------------|
| `Mail.Read` | Delegated | Read user's mailbox (list, search, get emails) | Recommended |
| `Mail.ReadWrite` | Delegated | Read emails + manage flags/categories (future) | Recommended |
| `Calendars.ReadWrite` | Delegated | Full calendar CRUD (create, read, update, delete events) | Recommended |

### Updated Scope String

The SSO OAuth flow requests scopes when redirecting to Azure AD. The scope string changes from:

```
openid profile email User.Read
```

to:

```
openid profile email User.Read Mail.Read Calendars.ReadWrite
```

Admin consent should be granted tenant-wide so individual brokers do not see a consent prompt on first login.

### Redirect URI

No changes needed — the existing redirect URI (`https://xgubaguglsnokjyudgvc.supabase.co/auth/v1/callback`) remains the same.

## OAuth Flow Extension

### How Provider Tokens Work

When a user authenticates via Azure AD through Supabase Auth, Supabase captures the **Microsoft provider token** — this is the Azure AD access token that carries Graph API scopes. The flow:

```
1. oauth-authorize → redirects to Supabase Auth → redirects to Azure AD
2. User authenticates at Azure AD, consents to scopes
3. Azure AD returns auth code to Supabase Auth callback
4. Supabase Auth exchanges code for tokens:
   - Supabase session token (for Supabase operations)
   - Microsoft provider_token (Azure AD access token with Graph scopes)
   - Microsoft provider_refresh_token (for token renewal)
5. oauth-token Edge Function wraps these into the Matrix SSO JWT
6. Provider tokens are stored encrypted for later Graph API calls
```

### Provider Token Storage

Microsoft provider tokens must be persisted so Edge Functions can call Graph API on subsequent requests (not just at login time).

| Field | Table | Purpose |
|-------|-------|---------|
| `microsoft_provider_token` | `auth.users.raw_user_meta_data` or dedicated `user_tokens` table | Encrypted Azure AD access token |
| `microsoft_provider_refresh_token` | Same | Encrypted refresh token for renewal |
| `microsoft_token_expires_at` | Same | Token expiry timestamp |

### Token Refresh Strategy

Microsoft access tokens expire after ~60-90 minutes. The Edge Functions must handle token refresh:

1. Before calling Graph API, check `microsoft_token_expires_at`
2. If expired (or within 5 min of expiry), use the `provider_refresh_token` to get a new access token:
   ```
   POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
   grant_type=refresh_token
   refresh_token={provider_refresh_token}
   client_id={client_id}
   client_secret={client_secret}
   scope=openid profile email User.Read Mail.Read Calendars.ReadWrite
   ```
3. Store the new access token and expiry
4. If refresh fails (token revoked, password changed), return 401 to the app — the broker must re-authenticate

## Email Integration

### Scope

Brokers can:
- View their Exchange inbox from within the Broker App (filtered, paginated)
- Search emails by sender, subject, or keyword
- View email details (body, attachments list)
- Attach an email to an opportunity record (stores a snapshot in CDL)
- View all emails attached to an opportunity

Brokers cannot:
- Send emails from the CRM (use Outlook directly)
- Access other brokers' mailboxes
- Modify or delete emails in Exchange

### Microsoft Graph Mail Endpoints

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|-----------|
| `/me/messages` | GET | List emails with `$filter`, `$search`, `$select`, `$top`, `$skip` | `Mail.Read` |
| `/me/messages/{id}` | GET | Get full email (body, headers, metadata) | `Mail.Read` |
| `/me/messages/{id}/attachments` | GET | List/download email attachments | `Mail.Read` |
| `/me/mailFolders/{id}/messages` | GET | List emails in a specific folder (Inbox, Sent, etc.) | `Mail.Read` |
| `/me/mailFolders` | GET | List mail folders | `Mail.Read` |

### Useful Query Patterns

**Search emails by contact email address:**
```
GET /me/messages?$filter=from/emailAddress/address eq 'client@example.com'
    &$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments
    &$top=25&$orderby=receivedDateTime desc
```

**Full-text search:**
```
GET /me/messages?$search="property viewing Limassol"
    &$select=id,subject,from,receivedDateTime,bodyPreview
    &$top=25
```

**Get email with full body for snapshot:**
```
GET /me/messages/{id}?$select=id,subject,from,toRecipients,ccRecipients,
    receivedDateTime,body,bodyPreview,hasAttachments,internetMessageId,
    conversationId,importance
```

### Edge Functions

#### `email-messages`

| Aspect | Detail |
|--------|--------|
| Path | `/email-messages` |
| Methods | GET |
| Auth | Bearer (SSO JWT) |
| Purpose | Proxy for reading broker's Exchange emails via Graph API |

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `folder` | string | Mail folder (default: `Inbox`) |
| `search` | string | Full-text search query |
| `from` | string | Filter by sender email address |
| `top` | number | Page size (default: 25, max: 100) |
| `skip` | number | Pagination offset |
| `id` | string | If provided, returns single email with full body |
| `attachments` | boolean | If true with `id`, also returns attachment metadata |

**Response (list):**
```json
{
  "emails": [
    {
      "id": "AAMkAGI2...",
      "subject": "Re: Property viewing - 3BR Villa Limassol",
      "from": { "name": "John Client", "email": "john@example.com" },
      "to": [{ "name": "Broker Name", "email": "broker@sharpsir.group" }],
      "receivedDateTime": "2026-03-10T14:30:00Z",
      "bodyPreview": "Thank you for arranging the viewing...",
      "hasAttachments": true,
      "importance": "normal"
    }
  ],
  "totalCount": 142,
  "nextSkip": 25
}
```

#### `email-attach`

| Aspect | Detail |
|--------|--------|
| Path | `/email-attach` |
| Methods | POST, GET, DELETE |
| Auth | Bearer (SSO JWT) |
| Purpose | Attach/detach email snapshots to/from opportunities |

**POST body (attach):**
```json
{
  "email_id": "AAMkAGI2...",
  "opportunity_id": "uuid-of-opportunity",
  "note": "Client confirmed budget and timeline"
}
```

The function fetches the full email from Graph API, creates a snapshot, and stores it in `opportunity_emails`.

**GET (list attached):**
```
GET /email-attach?opportunity_id={uuid}
```

**DELETE (detach):**
```json
{
  "opportunity_email_id": "uuid-of-link-record"
}
```

### Data Model: `opportunity_emails`

Stored in the App DB instance (CDL-Connected apps) or domain DB (Domain-Specific apps).

```sql
CREATE TABLE opportunity_emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  attached_by UUID NOT NULL,               -- SSO user ID of broker who attached
  attached_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Email snapshot (immutable once attached)
  exchange_message_id TEXT NOT NULL,        -- Graph API message ID
  internet_message_id TEXT,                 -- RFC 2822 Message-ID header
  conversation_id TEXT,                     -- Exchange conversation thread ID
  subject TEXT NOT NULL,
  from_name TEXT,
  from_email TEXT NOT NULL,
  to_recipients JSONB,                     -- [{name, email}]
  cc_recipients JSONB,                     -- [{name, email}]
  received_at TIMESTAMPTZ NOT NULL,
  body_preview TEXT,                        -- First ~255 chars
  body_html TEXT,                           -- Full HTML body (optional, configurable)
  has_attachments BOOLEAN DEFAULT false,
  attachment_names TEXT[],                  -- Array of attachment filenames
  importance TEXT DEFAULT 'normal',

  -- Broker note
  note TEXT,

  -- Platform fields
  x_sm_tenant_id UUID,
  x_sm_created_by UUID,
  x_sm_modified_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(opportunity_id, exchange_message_id)
);

-- RLS: broker sees only emails they attached or emails on opportunities they own
ALTER TABLE opportunity_emails ENABLE ROW LEVEL SECURITY;
```

## Calendar Management

### Scope

Brokers can:
- View their Outlook calendar within the CRM (day/week/month view)
- Create property viewings and meetings that auto-sync to Outlook (with attendee invitations)
- Update or cancel appointments (changes reflected in Outlook)
- Accept/decline meeting invitations from within the CRM
- See free/busy conflicts when scheduling new events

Managers can:
- View aggregated team calendar (read-only, pulled from broker calendars)

### Microsoft Graph Calendar Endpoints

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|-----------|
| `/me/calendarView` | GET | List events in a date range (`startDateTime`, `endDateTime`) | `Calendars.ReadWrite` |
| `/me/events/{id}` | GET | Get single event details | `Calendars.ReadWrite` |
| `/me/calendar/events` | POST | Create a new event (with attendees, location, reminders) | `Calendars.ReadWrite` |
| `/me/events/{id}` | PATCH | Update event (reschedule, change location/attendees) | `Calendars.ReadWrite` |
| `/me/events/{id}` | DELETE | Cancel/delete event | `Calendars.ReadWrite` |
| `/me/events/{id}/accept` | POST | Accept meeting invitation | `Calendars.ReadWrite` |
| `/me/events/{id}/decline` | POST | Decline meeting (with optional `proposedNewTime`) | `Calendars.ReadWrite` |
| `/me/events/{id}/tentativelyAccept` | POST | Tentatively accept | `Calendars.ReadWrite` |
| `/me/calendar/getSchedule` | POST | Check free/busy for one or more users | `Calendars.ReadWrite` |

### Event Creation Patterns

**Property viewing (with client + keyholder):**
```json
{
  "subject": "Property Viewing - 3BR Villa, Limassol Marina",
  "body": {
    "contentType": "HTML",
    "content": "<p>Property viewing arranged by Sharp SIR.</p><p>Address: ...</p>"
  },
  "start": { "dateTime": "2026-03-15T10:00:00", "timeZone": "Asia/Nicosia" },
  "end": { "dateTime": "2026-03-15T11:00:00", "timeZone": "Asia/Nicosia" },
  "location": { "displayName": "3BR Villa, Limassol Marina, Limassol" },
  "attendees": [
    { "emailAddress": { "address": "client@example.com", "name": "John Client" }, "type": "required" },
    { "emailAddress": { "address": "keyholder@example.com", "name": "Keyholder" }, "type": "optional" }
  ],
  "reminderMinutesBeforeStart": 30,
  "isOnlineMeeting": false
}
```

**Follow-up call (virtual):**
```json
{
  "subject": "Follow-up Call - John Client (Demand Research)",
  "start": { "dateTime": "2026-03-16T14:00:00", "timeZone": "Asia/Nicosia" },
  "end": { "dateTime": "2026-03-16T14:30:00", "timeZone": "Asia/Nicosia" },
  "attendees": [
    { "emailAddress": { "address": "client@example.com", "name": "John Client" }, "type": "required" }
  ],
  "isOnlineMeeting": true,
  "onlineMeetingProvider": "teamsForBusiness",
  "reminderMinutesBeforeStart": 15
}
```

### Edge Functions

#### `calendar-events`

| Aspect | Detail |
|--------|--------|
| Path | `/calendar-events` |
| Methods | GET, POST, PATCH, DELETE |
| Auth | Bearer (SSO JWT) |
| Purpose | CRUD operations on broker's Outlook calendar via Graph API |

**GET (list events in range):**

| Param | Type | Description |
|-------|------|-------------|
| `startDateTime` | ISO 8601 | Range start (required) |
| `endDateTime` | ISO 8601 | Range end (required) |
| `select` | string | Comma-separated fields to return |

**Response (list):**
```json
{
  "events": [
    {
      "id": "AAMkAGI2...",
      "subject": "Property Viewing - 3BR Villa",
      "start": { "dateTime": "2026-03-15T10:00:00", "timeZone": "Asia/Nicosia" },
      "end": { "dateTime": "2026-03-15T11:00:00", "timeZone": "Asia/Nicosia" },
      "location": { "displayName": "Limassol Marina" },
      "attendees": [...],
      "isAllDay": false,
      "isCancelled": false,
      "responseStatus": { "response": "organizer" },
      "onlineMeeting": null,
      "crm_link": {
        "type": "showing_appointment",
        "id": "uuid-of-showing"
      }
    }
  ]
}
```

The `crm_link` field is enriched by the Edge Function: it checks if the Outlook event ID matches a known `showing_appointment` or `broker_meeting` and adds the cross-reference.

**POST (create event):**
```json
{
  "subject": "Property Viewing - 3BR Villa",
  "start": "2026-03-15T10:00:00",
  "end": "2026-03-15T11:00:00",
  "timeZone": "Asia/Nicosia",
  "location": "Limassol Marina",
  "attendees": [
    { "email": "client@example.com", "name": "John Client", "type": "required" }
  ],
  "body": "Property viewing arranged by Sharp SIR.",
  "isOnlineMeeting": false,
  "reminderMinutes": 30,
  "crm_link": {
    "type": "showing_appointment",
    "id": "uuid-of-showing"
  }
}
```

The function creates the Outlook event via Graph API, then updates the linked CRM record with the Outlook event ID.

**PATCH (update event):** Same fields as POST, plus `id` of the existing event.

**DELETE:** Cancels the Outlook event and clears the `outlook_event_id` from the CRM record.

#### `calendar-sync`

| Aspect | Detail |
|--------|--------|
| Path | `/calendar-sync` |
| Methods | POST |
| Auth | Bearer (SSO JWT, admin or system) |
| Purpose | Bidirectional sync between CRM and Outlook for a broker |

**Actions:**

| Action | Description |
|--------|-------------|
| `push` | Push all CRM appointments without `outlook_event_id` to Outlook |
| `pull` | Read Outlook events and update CRM status (accepted, declined, rescheduled) |
| `reconcile` | Full bidirectional reconcile for a date range |

**POST body:**
```json
{
  "action": "reconcile",
  "user_id": "uuid-of-broker",
  "startDateTime": "2026-03-01T00:00:00Z",
  "endDateTime": "2026-03-31T23:59:59Z"
}
```

### Sync Strategy

**CRM is the system of record** for property-related appointments. Outlook is the delivery and notification mechanism.

| Direction | Trigger | Behavior |
|-----------|---------|----------|
| CRM → Outlook | Broker creates viewing/meeting in CRM | Edge Function creates Outlook event with attendees; stores `outlook_event_id` back in CRM |
| CRM → Outlook | Broker reschedules in CRM | Edge Function PATCHes the Outlook event |
| CRM → Outlook | Broker cancels in CRM | Edge Function DELETEs the Outlook event |
| Outlook → CRM | Attendee accepts/declines | Polling or webhook updates attendee status in CRM |
| Outlook → CRM | Broker creates event directly in Outlook | Not auto-synced to CRM (Outlook-only events remain Outlook-only) |

Events created directly in Outlook (not via CRM) are visible in the CRM calendar view but are **not** linked to CRM records unless the broker manually links them.

### Conflict Detection

Before creating a CRM event, the Edge Function checks the broker's free/busy status:

```
POST /me/calendar/getSchedule
{
  "schedules": ["broker@sharpsir.group"],
  "startTime": { "dateTime": "2026-03-15T10:00:00", "timeZone": "Asia/Nicosia" },
  "endTime": { "dateTime": "2026-03-15T11:00:00", "timeZone": "Asia/Nicosia" },
  "availabilityViewInterval": 30
}
```

If conflicts are detected, the API returns a warning (not a hard block) so the broker can decide whether to proceed.

### Data Model Extensions

#### `showing_appointment` — additional columns

```sql
ALTER TABLE showing_appointment
  ADD COLUMN outlook_event_id TEXT,            -- Graph API event ID
  ADD COLUMN outlook_ical_uid TEXT,            -- iCalendar UID for cross-platform reference
  ADD COLUMN outlook_sync_status TEXT          -- 'synced' | 'pending' | 'error' | 'not_linked'
    DEFAULT 'not_linked',
  ADD COLUMN outlook_last_synced_at TIMESTAMPTZ;
```

#### `broker_meetings` — new table

For non-showing meetings: follow-up calls, seller updates, team meetings, contract signings.

```sql
CREATE TABLE broker_meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_id UUID NOT NULL,                     -- SSO user ID
  meeting_type TEXT NOT NULL,                  -- 'follow_up_call' | 'seller_meeting' | 'team_meeting' | 'contract_signing' | 'other'

  -- Linked entities (optional, polymorphic)
  opportunity_id UUID,                         -- Link to opportunity/deal
  contact_id UUID,                             -- Link to contact/client
  property_id UUID,                            -- Link to property

  -- Meeting details
  subject TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  time_zone TEXT DEFAULT 'Asia/Nicosia',
  location TEXT,
  is_online BOOLEAN DEFAULT false,
  online_meeting_url TEXT,

  -- Attendees stored as JSONB array
  attendees JSONB DEFAULT '[]',               -- [{name, email, type, response_status}]

  -- Outlook sync
  outlook_event_id TEXT,
  outlook_ical_uid TEXT,
  outlook_sync_status TEXT DEFAULT 'not_linked',
  outlook_last_synced_at TIMESTAMPTZ,

  -- Status
  status TEXT DEFAULT 'scheduled',            -- 'scheduled' | 'completed' | 'cancelled' | 'no_show'
  outcome_notes TEXT,

  -- Platform fields
  x_sm_tenant_id UUID,
  x_sm_created_by UUID,
  x_sm_created_at TIMESTAMPTZ DEFAULT now(),
  x_sm_modified_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE broker_meetings ENABLE ROW LEVEL SECURITY;
```

### Use Cases Mapped to Sales Pipeline

| Pipeline Stage | Calendar Use Case | Outlook Event |
|---------------|-------------------|---------------|
| **Qualification** | Schedule initial client meeting | Event with client, 30-min discovery call |
| **Demand Research** | Follow-up calls to clarify needs | Recurring event or series of individual calls |
| **Solution / Viewing** | Property showings | Event with client + seller/keyholder + property address as location |
| **Decision Making** | Negotiation meetings with team | Event with client + broker + manager |
| **Deal Signing** | Contract signing appointment | Event with client + legal + broker at office |
| **Payment** | Payment follow-up reminders | Reminder-only events |

### Use Cases Mapped to Listing Checklist

| Checklist Step | Calendar Use Case |
|---------------|-------------------|
| #1 — Appointment with Seller | `broker_meetings` (type: seller_meeting) → Outlook event |
| #16 — Arrange photoshoot with Irina | `broker_meetings` (type: other, subject: Photoshoot) → Outlook event with photographer |
| #20 — Present at Listing meeting | Recurring team event (every second Wednesday) |
| #23-27 — Viewings | `showing_appointment` → Outlook event with client + seller confirmation |

## Shared Module Extension

Extend `_shared/microsoft-graph.ts` with new helpers:

```typescript
// New exports to add to _shared/microsoft-graph.ts

export interface GraphEmail {
  id: string;
  subject: string;
  from: { emailAddress: { name: string; address: string } };
  toRecipients: Array<{ emailAddress: { name: string; address: string } }>;
  ccRecipients: Array<{ emailAddress: { name: string; address: string } }>;
  receivedDateTime: string;
  bodyPreview: string;
  body?: { contentType: string; content: string };
  hasAttachments: boolean;
  importance: string;
  internetMessageId?: string;
  conversationId?: string;
}

export interface GraphEvent {
  id: string;
  iCalUId: string;
  subject: string;
  start: { dateTime: string; timeZone: string };
  end: { dateTime: string; timeZone: string };
  location?: { displayName: string };
  attendees: Array<{
    emailAddress: { name: string; address: string };
    type: string;
    status: { response: string };
  }>;
  isAllDay: boolean;
  isCancelled: boolean;
  isOnlineMeeting: boolean;
  onlineMeeting?: { joinUrl: string };
  responseStatus: { response: string };
}

/** Fetch emails from user's mailbox (delegated token) */
export async function fetchUserEmails(
  providerToken: string,
  params: { folder?: string; search?: string; from?: string; top?: number; skip?: number }
): Promise<{ value: GraphEmail[]; totalCount?: number } | null>;

/** Fetch a single email with full body (delegated token) */
export async function fetchEmailById(
  providerToken: string,
  messageId: string,
  includeBody?: boolean
): Promise<GraphEmail | null>;

/** Fetch email attachments metadata (delegated token) */
export async function fetchEmailAttachments(
  providerToken: string,
  messageId: string
): Promise<Array<{ id: string; name: string; contentType: string; size: number }> | null>;

/** List calendar events in a date range (delegated token) */
export async function fetchCalendarView(
  providerToken: string,
  startDateTime: string,
  endDateTime: string
): Promise<GraphEvent[] | null>;

/** Create a calendar event (delegated token) */
export async function createCalendarEvent(
  providerToken: string,
  event: Partial<GraphEvent> & { subject: string; start: any; end: any }
): Promise<GraphEvent | null>;

/** Update a calendar event (delegated token) */
export async function updateCalendarEvent(
  providerToken: string,
  eventId: string,
  updates: Partial<GraphEvent>
): Promise<GraphEvent | null>;

/** Delete a calendar event (delegated token) */
export async function deleteCalendarEvent(
  providerToken: string,
  eventId: string
): Promise<boolean>;

/** Respond to a calendar event (delegated token) */
export async function respondToCalendarEvent(
  providerToken: string,
  eventId: string,
  response: 'accept' | 'decline' | 'tentativelyAccept',
  comment?: string
): Promise<boolean>;

/** Check free/busy schedule (delegated token) */
export async function getSchedule(
  providerToken: string,
  schedules: string[],
  startDateTime: string,
  endDateTime: string
): Promise<Array<{ scheduleId: string; availabilityView: string }> | null>;

/** Refresh a Microsoft provider token */
export async function refreshMicrosoftToken(
  refreshToken: string,
  credentials: AzureAppCredentials
): Promise<{ access_token: string; refresh_token: string; expires_in: number } | null>;
```

## Security Considerations

### Permission Boundaries

| Principle | Implementation |
|-----------|---------------|
| **Least privilege** | `Mail.Read` (not `Mail.ReadWrite.All`), `Calendars.ReadWrite` (not `.All`) |
| **Delegated only** | No application-level mail/calendar access; each broker accesses only their own data |
| **Token isolation** | Provider tokens are per-user, encrypted at rest, never exposed to the client app |
| **RLS enforcement** | `opportunity_emails` and `broker_meetings` have RLS policies scoped by broker ID and team |
| **Snapshot immutability** | Once an email is attached, the snapshot cannot be modified (only detached) |
| **Audit trail** | All attach/detach operations logged with user ID and timestamp |

### Token Security

- Provider tokens are **never sent to the client** — they remain server-side (Edge Functions only)
- The client app sends only the Matrix SSO JWT; Edge Functions use it to look up the corresponding Microsoft provider token
- Tokens are encrypted at rest using Supabase Vault or application-level encryption
- Token refresh happens server-side; clients are unaware of the Microsoft token lifecycle

### Data Residency

- Email content stays in Exchange Online (Microsoft 365 tenant) — the CRM stores only metadata snapshots
- Calendar events live in Exchange Online — the CRM stores only sync reference IDs (`outlook_event_id`)
- Snapshots stored in Supabase follow the same data residency as other CDL data

## Cross-Reference

| For | See |
|-----|-----|
| SSO OAuth flow | [app-template.md](app-template.md) §Dual-Supabase Architecture |
| Security model and RLS patterns | [security-model.md](security-model.md) |
| Edge Function API catalog | [api-contracts.md](api-contracts.md) |
| Sales pipeline stages | [sales-pipeline.md](../business-processes/sales-pipeline.md) |
| Listing checklist appointments | [listing-checklist.md](../business-processes/listing-checklist.md) |
| Existing Microsoft Graph helpers | `matrix-platform-foundation/supabase/functions/_shared/microsoft-graph.ts` |
| Azure AD config | `admin-microsoft-auth` Edge Function |
| Qobrix email/meeting migration | [qobrix-data-model.md](../data-models/qobrix-data-model.md) |
