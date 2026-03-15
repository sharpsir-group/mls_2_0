# Buyer-Side Pipeline (Sales Pipeline)

> 8-stage Kanban workflow for managing buyer deals from qualification to close

## Pipeline Overview

```
QUALIFICATION → DEMAND RESEARCH → SOLUTION/VIEWING → DECISION MAKING → DEAL SIGNING → PAYMENT → CLOSED WON
                                                                                                    ↘ CLOSED LOST
```

## What the Manager Sees (Pipeline View)

- **All deals in one place**: Visual overview of all clients by stage with broker filtering
- **Trouble spots**: Automatic detection of stages with low conversion or stalled deals
- **Revenue forecast**: Calculated expected revenue based on stages and close probability
- **Team productivity**: Metrics per broker — deal count, conversions, average cycle

## Stage Definitions

### Stage 1: QUALIFICATION

**Goal**: Initial assessment of the lead, create opportunity, assign broker.

| Aspect | Details |
|--------|---------|
| Broker tasks | Initial client assessment, create opportunity, assign responsible broker |
| AI Copilot tasks | Auto-suggest optimal meeting time, select properties for showing (Curated List), optimize showing routes |
| O365 integration | Schedule initial meeting → synced to Outlook as event with client. Attach relevant inbound emails (inquiry, referral) to opportunity. |
| Artifacts | Lead context (chat, viewing history), contact info, interest in property, estimated deal value, attached emails, Outlook-synced meeting |
| Exit criteria | BANT criteria assessed, lead accepted or rejected |

### Stage 2: DEMAND RESEARCH

**Goal**: Deep understanding of client requirements, preferences, and budget.

| Aspect | Details |
|--------|---------|
| Broker tasks | Discovery calls to identify needs, budget analysis, preliminary property selection |
| AI Copilot tasks | Suggest questions for need identification, remind about preparation for meeting, track appointment→deal conversion |
| O365 integration | Follow-up call scheduled → Outlook event with client. Email correspondence (budget discussions, preference refinement) attached to opportunity for context continuity. |
| Artifacts | Activity history, engagement metrics, budget analysis, auto-selected properties, attached emails, calendar-synced follow-up calls |
| Exit criteria | Client needs clearly defined, initial property shortlist ready |

### Stage 3: SOLUTION / VIEWING

**Goal**: Present properties, conduct showings, curate the best options.

| Aspect | Details |
|--------|---------|
| Broker tasks | Conduct professional showings, reveal objections, collect detailed feedback |
| AI Copilot tasks | Generate Curated List, plan showings schedule, generate PDF brochures, optimize routes |
| O365 integration | Property viewings created in CRM → Outlook events with client + seller/keyholder + property address as location. Free/busy conflict detection before booking. Post-viewing follow-up emails attached to opportunity. |
| Artifacts | Curated property list, showing schedule, showing logs, PDF brochures, calendar-synced viewings, attached follow-up emails |
| Exit criteria | Client identifies 1-3 preferred properties |

### Stage 4: DECISION MAKING

**Goal**: Help the client evaluate final options and move toward a decision.

| Aspect | Details |
|--------|---------|
| Broker tasks | Discuss final variants, address objections, involve team for support |
| AI Copilot tasks | Track engagement, predict probability, suggest discussion points |
| O365 integration | Negotiation meetings scheduled → Outlook events with client + broker + manager. Offer/counter-offer emails attached to opportunity for deal history. |
| Artifacts | Updated notes, team assignments, full activity history, attached negotiation emails, calendar-synced meetings |
| Exit criteria | Client ready to make an offer |

### Stage 5: DEAL SIGNING

**Goal**: Formalize the agreement and sign the contract.

| Aspect | Details |
|--------|---------|
| Broker tasks | Prepare contract, coordinate legal services, plan signing |
| O365 integration | Contract signing appointment → Outlook event with client + legal + broker at office. Legal correspondence emails attached to opportunity. |
| Artifacts | Document activity, service recommendations (Legal, Property Management, Interior Design), calendar-synced signing appointment, attached legal emails |
| Exit criteria | Contract signed by all parties |

### Stage 6: PAYMENT PROCESS

**Goal**: Financial processing and final closing steps.

| Aspect | Details |
|--------|---------|
| Broker tasks | Control financial transactions, final price corrections, coordinate closing |
| O365 integration | Payment follow-up reminders → Outlook reminder events. Payment confirmation emails attached to opportunity. |
| Artifacts | Final price corrections, closing date records, attached payment emails |
| Exit criteria | Payment completed |

### Stage 7: CLOSED WON

**Goal**: Deal successfully completed.

| Aspect | Details |
|--------|---------|
| Artifacts | Final deal value, closing notes, success record |
| Post-close | Request referral, maintain relationship for future deals |

### Stage 8: CLOSED LOST

**Goal**: Document the loss, preserve learning.

| Aspect | Details |
|--------|---------|
| Broker tasks | Analyze loss reason, document competitor, plan potential re-contact |
| Required fields | Loss reason (no budget, wrong location, unrealistic timeline, competitor won, etc.) |
| Next steps | Feedback to marketing for campaign optimization, possible return to nurturing |

## Pipeline Quality Rule

> Long-term leads (timeline >12 months) do NOT sit for years in Decision Making. They move to a separate **nurturing pool** but remain in CRM and follow-up planning. This preserves forecast accuracy and team focus on "hot" deals.

## Bidirectional Matching in Pipeline

| Trigger | Action |
|---------|--------|
| New listing enters system | Manager sees all buyers in pipeline whose criteria match the new property. Brokers get notifications for fast reaction. |
| New buyer enters system | System shows matching listings from portfolio. Broker immediately sees what to offer at the first meeting. |

## Key Manager Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| 1 | Real-time control | Instant updates when brokers act, notifications on critical events |
| 2 | Analytics & reports | Conversion by stage, time in each stage, broker comparison |
| 3 | Interventions | Reassign client, add task, leave comment |
| 4 | Team calendar | Aggregated view of all broker Outlook calendars (viewings, meetings) |
| 5 | Email audit | View emails attached to any opportunity for context during pipeline reviews |

## O365 Integration Summary

Every opportunity record has two O365-linked artifact types:

| Artifact | Source | Storage |
|----------|--------|---------|
| **Attached Emails** | Broker selects emails from their Exchange inbox and attaches them to the opportunity | `opportunity_emails` table (metadata snapshot; full email remains in Exchange) |
| **Calendar Events** | Viewings, meetings, and follow-ups created in CRM auto-sync to Outlook | `showing_appointment` and `broker_meetings` tables with `outlook_event_id` |

See [o365-exchange-integration.md](../platform/o365-exchange-integration.md) for technical details.
