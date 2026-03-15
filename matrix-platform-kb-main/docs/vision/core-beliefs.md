# Core Beliefs & Design Philosophy

> Operating principles for the Sharp Matrix Platform

## Fundamental Principle

> **The broker works with the client. The system works with the process.**

AI Copilot exists to free the broker from routine so they can focus on what only humans do well: build trust, negotiate, and close deals. The system handles data, timing, matching, and forecasting.

## Three Key Ideas

### 1. Two Representations of the Sales Process
- **Kanban board** for managers: control pipeline, forecast revenue, analyze team performance
- **AI Brokerage Copilot** for brokers: client card + Next Best Action, automated matching, document generation

### 2. Clear Boundary Between Follow-up and Active Sales
- Follow-up (nurturing): before the first meeting/showing — weekly/monthly cadence
- Active Sales: after the first meeting/showing — daily cadence toward closing
- The **first personal meeting or showing** is the trigger that moves a lead from nurturing into active sales

### 3. AI Copilot at the Heart of the System
- Analyzes context and determines stage automatically
- Suggests Next Best Action with success probability
- Frees the broker from routine tasks
- Learns from successful deals to improve recommendations

## Sharp Matrix Platform Principles

### RESO DD 2.0 is the Canonical Data Layer
- All apps in the platform read and write using RESO standard field names
- Qobrix and SIR/Anywhere.com are **reference sources**, not the system of record
- Fields not in RESO DD get platform extensions with `x_sm_` prefix
- This ensures data consistency across every app and every market (Cyprus, Hungary, Kazakhstan)

### Multi-App, Single Data Truth
- Sharp Matrix consists of many interconnected apps (Broker, Manager, Client Portal, Marketing, etc.)
- Every app operates on the same RESO-based schema — no translation layers between apps
- One canonical field name everywhere: if RESO calls it `ListPrice`, every app calls it `ListPrice`
- The RESO Resource Usage Matrix (see `docs/platform/app-catalog.md`) defines which apps read/write which resources

### Regional Customization on a Unified Core
- Cyprus, Hungary, and Kazakhstan share the same platform and data model
- Regional differences are handled through configuration, not code forks
- Channel priorities differ by market but the underlying data layer is identical

## Design Principles for Implementation

### Data First
- Every business concept must have a clear data model
- RESO DD 2.0 standard names as the canonical schema for all platform apps
- Fields not in RESO DD are documented as platform extensions (`x_sm_*` prefix)
- No data lives only in people's heads or chat threads

### Pipeline Integrity
- Every lead has exactly one active stage at any time
- Stage transitions have explicit triggers and artifacts
- Long-term leads (>12 months) go to nurturing pool, not active forecast
- Disqualified leads must have documented reasons

### Matching is Bidirectional
- New listing → find matching buyers automatically
- New buyer → find matching listings automatically
- Matching criteria: location, budget, property type, timeline, specific features
- Output: **Curated Lists** — personalized shortlists for each client

### Zero Tolerance for Missed Follow-ups
- The system must surface every overdue follow-up immediately
- Missed follow-ups are the highest priority notification
- Auto-scheduling of next follow-up after every contact
- Prioritization: missed (critical) → today → hot potentials → tomorrow → new leads

### Metrics Drive Decisions
- Weekly review: results vs plan, forecast accuracy
- Daily standup: prevent losses, surface risks
- Every metric has an owner (broker, manager, system)
- Metrics are visible in dashboards, not buried in reports

## Agent-First Operating Principles

These principles guide how AI agents (LLMs) should work within this codebase:

1. **Repository knowledge is the system of record** — if it's not in `docs/`, it doesn't exist for agents
2. **Progressive disclosure** — start with AGENTS.md → Chapter 0 (Platform) → relevant chapter
3. **RESO DD is canonical** — always use RESO standard names when building any app; check `docs/data-models/` before writing code that touches data
4. **Business processes define behavior** — pipeline stages, qualification rules, and metrics are not suggestions; they are requirements
5. **Vision documents define intent** — when ambiguity arises, the digital strategy 2026-2028 and AI-driven sales model are the tiebreakers
6. **Platform consistency** — every app in Sharp Matrix must use the same field names, same data types, same lookup values from the RESO common data layer
