# Broker Dashboard Specification

> AI-powered personal daily view with automatic prioritization
> Source: Vision deck slides 11-12

## Dashboard Purpose

The broker sees their personal overview for the day with tasks automatically grouped and prioritized. AI Copilot analyzes all contacts and surfaces priorities based on: missed follow-ups (highest priority), hot potentials (ready for deal), scheduled actions, and new leads.

## Dashboard Layout

### Header Metrics (Summary Cards)

| Card | Value | Description |
|------|-------|-------------|
| NEW LEADS | Count | Requiring first contact (within 24 hours) |
| FOLLOW-UP TODAY | Count | Scheduled for today |
| MISSED FOLLOW-UPS | Count (critical!) | Overdue — highest priority indicator |
| FOLLOW-UP TOMORROW | Count | Preparation for tomorrow |
| HOT POTENTIALS | Count | Ready for appointment |
| PIPELINE VALUE | Currency (€) | Total active deals value |

### Top Actions (Auto-Prioritized List)

AI Copilot automatically builds a prioritized action list. Priority order:

| Priority | Type | Example |
|----------|------|---------|
| CRITICAL | Missed follow-up | "Ivan Petrov: missed follow-up 2 days ago. Call immediately!" |
| HIGH | Hot potential | "Maria Sidorova: Hot Potential, ready for showing. Schedule appointment today." |
| MEDIUM | Scheduled action | "Alexey Kozlov: send Curated List (promised for today)" |
| LOW | New lead | "John Smith: first contact, qualification (within 24 hours)" |

### Working Principle

AI Copilot analyzes all contacts and automatically surfaces priorities based on:
1. **Missed follow-ups** (highest priority — these are potential lost deals)
2. **Hot potentials** (readiness for deal — highest revenue impact)
3. **Scheduled actions** (committed promises to clients)
4. **New leads** (time-sensitive first contact)

### Quick Actions from Dashboard

| Action | Trigger |
|--------|---------|
| Email | One-click compose with context |
| Call | Click-to-call with auto-logging |
| Schedule appointment | Calendar integration |

## Broker Dashboard Metrics

| Metric | Source | Update |
|--------|--------|--------|
| Revenue (actual vs plan) | Closed deals | Real-time |
| Average commission check | Closed deals | Weekly |
| Active pipeline value | Open opportunities | Real-time |
| Deals in progress | Pipeline stages | Real-time |
| Conversion rates by stage | Pipeline analytics | Weekly |
| Follow-up completion rate | Task system | Daily |
| Appointments this week | Calendar | Real-time |

## AI Copilot Client Card View

When a broker opens a specific client, the AI Copilot card shows:

```
┌─────────────────────────────────────────────────┐
│ CLIENT: Ivan Petrov                              │
│ Budget: €500K | Location: Limassol | Timeline: 3-6 months │
│                                                  │
│ ┌─ NEXT BEST ACTION ──────────────────────────┐ │
│ │ Schedule showing: 2 suitable properties found│ │
│ │ Deal probability: 15% → 35%                  │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ PIPELINE: Contact ✓ → Needs (in process) → Showings → Decision → Close │
│                                                  │
│ ACTIVITY HISTORY:                                │
│ 02.02.2026 — Contact registered in system        │
│ 03.02.2026 — First call (5 min)                  │
│ 03.02.2026 — Email sent                          │
│ 04.02.2026 — Follow-up scheduled                 │
│ 05.02.2026 — Awaiting response                   │
│                                                  │
│ MATCHING PROPERTIES:                             │
│ 🏠 Villa in Paphos — €480K [Details]             │
│ 🏢 Apartment Limassol — €520K [Details]          │
│ [+ Add Property]                                 │
│                                                  │
│ QUICK ACTIONS:                                   │
│ [Email] [Call] [Schedule Appointment]            │
└─────────────────────────────────────────────────┘
```

## Result for the Broker

- Manage listings and buyers in one interface
- Automatic matching between listings and buyers
- 40% time savings through AI automation
- 25% increase in conversion rates
