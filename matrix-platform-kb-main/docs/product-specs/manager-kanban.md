# Manager Kanban & Pipeline View Specification

> Source: Vision deck slides 6-9

## Purpose

The manager sees the complete picture: where clients are stuck, which brokers are overloaded, which deals are at risk. Two parallel Kanban boards (seller-side and buyer-side) plus analytics and forecasting.

## Manager View Components

### 1. Kanban Board (Main View)

Two parallel boards visible simultaneously:

**Seller-Side (Listings)**
```
PROSPECT → CONTACTED → AGREEMENT SIGNED → ACTIVE LISTING → SOLD → COMMISSION → CLOSED WON
                                                                                    ↘ WITHDRAWN
```

**Buyer-Side (Sales)**
```
QUALIFICATION → DEMAND RESEARCH → SOLUTION/VIEWING → DECISION → DEAL SIGNING → PAYMENT → CLOSED WON
                                                                                           ↘ CLOSED LOST
```

Each card shows: Client name, property/budget, broker assigned, days in stage, probability.

### 2. Listing Pipeline View (Seller-Side Detail)

| Feature | Description |
|---------|-------------|
| All listings in one place | Visual overview of all properties by stage with broker filtering |
| Days on Market monitoring | Auto-detect properties with long DOM for intervention |
| Sales forecast | Calculate expected sales based on active listings |
| Broker productivity | Metrics per broker: new listings, DOM, listing→sale conversion |

### 3. Sales Pipeline View (Buyer-Side Detail)

| Feature | Description |
|---------|-------------|
| All deals in one place | Visual overview of all buyers by stage with broker filtering |
| Trouble spots | Auto-detect stages with low conversion or stalled deals |
| Revenue forecast | Expected revenue based on stages and probability |
| Team productivity | Metrics per broker: deals, conversions, average cycle |

### 4. Matching Control

| Trigger | Action |
|---------|--------|
| New listing in system | Manager sees all buyers in pipeline whose criteria match. Brokers get notifications. |
| New buyer in system | System shows matching listings from portfolio. Broker sees what to offer at first meeting. |

## Manager Analytics Panel

### Weekly Review Metrics
| Metric | Description |
|--------|-------------|
| Target vs Actual Revenue | Commission revenue tracking |
| Forecast accuracy | Predicted vs actual closings |
| Listing status summary | New, Active, DOM averages |
| Appointment count & quality | Volume and conversion rates |

### Daily Standup Metrics
| Metric | Description |
|--------|-------------|
| Missed follow-ups (overdue) | Critical — potential lost deals |
| New leads | Requiring assignment and first contact |
| Hot potentials | Ready for conversion |
| Critical actions today | Appointments, deadlines, expirations |

## Manager Intervention Capabilities

| # | Action | Description |
|---|--------|-------------|
| 1 | Real-time control | Instant visibility when brokers act, alerts on critical events |
| 2 | Analytics & reports | Conversion by stage, time per stage, broker comparisons |
| 3 | Interventions | Reassign client to another broker, add tasks, leave comments |

## Forecast Calculation

```
Expected Revenue = Σ (Deal Value × Stage Probability × Close Probability)
```

| Pipeline Stage | Base Probability |
|---------------|-----------------|
| Qualification | 10% |
| Demand Research | 20% |
| Solution/Viewing | 35% |
| Decision Making | 50% |
| Deal Signing | 75% |
| Payment Process | 90% |
| Closed Won | 100% |
| Closed Lost | 0% |

Rule: Long-term leads (>12 months) are excluded from active forecast and moved to nurturing pool.
