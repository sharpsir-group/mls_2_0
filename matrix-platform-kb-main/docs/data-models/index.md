# Chapter 3: Data Models — Index

> Dash/Anywhere.com provides the practical field definitions for app development.
> RESO DD 2.0 is the interoperability standard for syndication and external APIs.
> Qobrix is a legacy CRM migration source.

## The Data Model Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Dash/Anywhere.com (PRACTICAL CORE)                │
│  50+ concrete fields, 30+ feature groups, media metadata    │
│  Derived from the SIR global listing platform brokers use   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Platform Extensions (x_sm_*)                      │
│  Fields Sharp Matrix needs that Dash does not provide       │
│  Prefixed, governed, and tracked per app                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: RESO DD 2.0 (INTEROP STANDARD)                    │
│  Industry standard names for syndication, RESO Web API,     │
│  MLS feeds, and portal exports                              │
├─────────────────────────────────────────────────────────────┤
│  Reference: Qobrix CRM (migration source)                   │
│  Legacy CRM schema — maps to Dash/RESO for data migration   │
└─────────────────────────────────────────────────────────────┘
```

**Why this order matters:** Dash/Anywhere.com is what SIR brokers actually use. Its fields are concrete and map directly to brokerage workflows. When Lovable builds a CDL-Connected app, it uses Dash-derived field names (e.g., `list_price`, `bedrooms`, `city`). RESO DD names (`ListPrice`, `BedroomsTotal`, `City`) are used for outbound syndication and the RESO Web API.

## Documents

| Document | What It Contains |
|----------|-----------------|
| [dash-data-model.md](dash-data-model.md) | **Start here** — Dash/Anywhere.com practical field reference: 50+ fields, 30+ feature groups, media, agent/office |
| [reso-dd-overview.md](reso-dd-overview.md) | RESO DD 2.0 interop standard: resources, fields, lookups |
| [reso-canonical-schema.md](reso-canonical-schema.md) | Which RESO resources Sharp Matrix uses, with Dash field mappings |
| [platform-extensions.md](platform-extensions.md) | All `x_sm_*` fields not in Dash or RESO DD |
| [mls-cdl-schema.md](mls-cdl-schema.md) | **MLS CDL Schema** — 18 tables, 422 columns deployed to CDL for Listing Management |
| [etl-pipeline.md](etl-pipeline.md) | Bronze/Silver/Gold ETL pipeline: how Dash data reaches Supabase |
| [data-contracts.md](data-contracts.md) | ETL schema contracts: layer boundaries, JSON Schema format, validation |
| [reso-web-api.md](reso-web-api.md) | RESO Web API (OData 4.0): syndication and external integrations |
| [qobrix-data-model.md](qobrix-data-model.md) | Qobrix CRM reference: legacy migration source |
| [property-field-mapping.md](property-field-mapping.md) | Cross-reference: Dash ↔ RESO ↔ Qobrix ↔ SIR field mapping |

## Key Entities Across All Layers

| Business Concept | RESO Resource (canonical) | Qobrix Entity (reference) | Sharp Matrix Apps |
|-----------------|--------------------------|---------------------------|-------------------|
| Property listing | Property | Property | Broker, Manager, Client Portal, Marketing |
| Client (buyer/seller) | Contacts | Contact | Broker, Manager, Client Portal |
| Broker/Agent | Member | Agent / User | Broker, Manager, SSO Console |
| Team/Office | Teams, Offices | Groups | Manager |
| Showing | ShowingAppointment | Property Viewing | Broker, Client Portal |
| Deal/Transaction | HistoryTransactional | Opportunity | Broker, Manager, Finance |
| Media | Media | Media | Broker, Marketing |
| Open house event | OpenHouse | — | Broker, Marketing |
| Lead/Prospect | Prospecting | Contact (with status) | Broker, AI Copilot |

## How Apps Use the Data Layer

```
Broker App ──┐
Manager App ─┤
Client Portal┤── All read/write through ──→ RESO DD Canonical Schema
Marketing App┤                              + Platform Extensions (x_sm_*)
Finance App ─┤
AI Copilot ──┘
```

When building any new feature:
1. **Start with Dash data model** — find the practical field name in [dash-data-model.md](dash-data-model.md)
2. **Check platform extensions** — if no Dash field exists, check [platform-extensions.md](platform-extensions.md)
3. **If neither exists** — propose a new `x_sm_*` extension following the governance in [reso-canonical-schema.md](reso-canonical-schema.md)
4. **For syndication** — use the RESO mapping column in dash-data-model.md to find the interop name
