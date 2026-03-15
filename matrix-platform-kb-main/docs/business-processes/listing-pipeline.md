# Seller-Side Pipeline (Listing Pipeline)

> 8-stage Kanban workflow for managing property listings from prospect to close

## Pipeline Overview

```
PROSPECT → CONTACTED → AGREEMENT SIGNED → ACTIVE LISTING → SOLD → AGENT COMMISSION → CLOSED WON
                                                                                          ↘ LISTING WITHDRAWN
```

## Stage Definitions

### Stage 1: PROSPECT

**Goal**: Identify potential property sellers and make first contact.

| Aspect | Details |
|--------|---------|
| Broker tasks | Find potential sellers (prospecting), make first contact, present services |
| AI Copilot tasks | Auto-publish on portals, analyze DOM and suggest corrections, match listings with active buyers |
| Artifacts | Contact information, initial property assessment |
| Exit criteria | Seller expresses interest in listing |

### Stage 2: CONTACTED

**Goal**: Detailed market consultation, demonstrate expertise and case studies.

| Aspect | Details |
|--------|---------|
| Broker tasks | Conduct detailed consultation, demonstrate expertise, provide comparative market analysis |
| AI Copilot tasks | Generate Curated Lists for clients, track engagement (opens, clicks) |
| Artifacts | Service presentation, comparative market analysis |
| Exit criteria | Seller agrees to sign listing agreement |

### Stage 3: AGREEMENT SIGNED

**Goal**: Prepare the listing with professional materials and legal documentation.

| Aspect | Details |
|--------|---------|
| Broker tasks | Prepare listing agreement, arrange professional photoshoot, conduct legal review |
| AI Copilot tasks | Predict sale probability, identify deals at risk, recommend actions for faster closing |
| Artifacts | Signed agreement, listing with photos and description |
| Exit criteria | Listing is published and active |

### Stage 4: ACTIVE LISTING

**Goal**: Market the property, organize showings, collect feedback, adjust strategy.

| Aspect | Details |
|--------|---------|
| Broker tasks | Organize showings, collect buyer feedback, adjust price/strategy if needed |
| AI Copilot tasks | Match listings with active buyers, generate Curated Lists, track interest and views, predict sale probability |
| Artifacts | Showing reports, buyer feedback, change history |
| Exit criteria | Accepted offer from a buyer |
| Key metrics | Days on Market (DOM), View→Showing conversion, Showing→Offer conversion |

### Stage 5: SOLD

**Goal**: Negotiate final price, coordinate with lawyers, close the deal.

| Aspect | Details |
|--------|---------|
| Broker tasks | Negotiate final price, coordinate with lawyers, close deal |
| Artifacts | Signed purchase contract, payment confirmation |
| Exit criteria | Contract signed and payment confirmed |

### Stage 6: AGENT COMMISSION PAYMENT

**Goal**: Complete work documentation, confirm commission receipt.

| Aspect | Details |
|--------|---------|
| Broker tasks | Complete work act, confirm payment receipt, calculate and transfer commission |
| Artifacts | Completed work act, commission payment confirmation, final calculation |
| Exit criteria | Commission paid to broker |

### Stage 7: CLOSED WON

**Goal**: Final deal closure, archive, record success.

| Aspect | Details |
|--------|---------|
| Broker tasks | Final deal closure, archive documents, record successful result |
| Artifacts | Full document package, final report, entry in success history |
| Exit criteria | Deal fully archived |

### Stage 8: LISTING WITHDRAWN

**Goal**: Document withdrawal reason and plan potential reactivation.

| Aspect | Details |
|--------|---------|
| Triggers | Seller changed mind, sold independently, unsatisfied with service |
| Broker tasks | Document withdrawal reason, analyze failure cause |
| Artifacts | Reason documentation, date, reactivation possibility assessment |
| Next steps | Possible return to PROSPECT stage for re-listing |

## Listing Quality Metrics

| Metric | Target | Review |
|--------|--------|--------|
| Days on Market (DOM) | Minimize | Weekly |
| Active listings count | Steady growth | Weekly |
| New listings per period | Track trend | Weekly |
| View → Showing conversion | Maximize | Weekly |
| Showing → Offer conversion | Maximize | Weekly |
| Listing → Sale conversion | Track | Monthly |
| Matching quality (% suitable Curated Lists) | Improve over time | Monthly |

## Listing Syndication Channels

| Channel | Method | Timing |
|---------|--------|--------|
| SIR Global Portal | Automated feed | On publish |
| Cyprus Website | Real-time sync | On publish |
| MLS Systems | Feed integration | On publish |
| Facebook / Instagram / LinkedIn | Auto-publish with optimized content | Scheduled |
| PDF Brochures | Auto-generation | On request |
| Email Campaigns | Automated to matching clients | On new listing |
| Calendar of Showings | Calendar integration | On scheduling |
