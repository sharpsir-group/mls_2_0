# Contact Center — Product Specification

> **For Lovable**: This spec defines the lead processing and routing system.
> RESO Resources: Contacts, Member, Property

---

## Overview

Centralized lead intake, qualification, and routing for all markets (Cyprus, Hungary, Kazakhstan). Single interface for agents to process leads from web forms, phone, email, and portal.

## User Persona

**Contact Center Agent**: Processes 50+ leads/day across markets. Needs fast qualification workflow, minimal clicks, clear routing rules.

## Key User Flows

1. **Lead Capture**: Lead arrives (web form, phone, email, portal) → auto-capture in CDL
2. **Qualification**: Agent qualifies using BANT criteria → MQL/SQL classification
3. **Routing**: Qualified lead → auto-route to broker (by market, property type, language)
4. **Nurture**: Unqualified lead → nurture campaign assignment

## RESO Resources Used

| Resource | Access | Purpose |
|----------|--------|---------|
| Contacts | crud | Lead records, qualification data |
| Member | r | Broker lookup for routing |
| Property | r | Property context for lead |

## Lead Routing Rules

| Rule | Logic |
|------|-------|
| Market match | Assign to broker in same market |
| Language match | Prefer broker with client language |
| Property type expertise | Match broker specialty |
| Current workload | Balance distribution |

## SLA

Lead response within **15 minutes** during business hours.

## Success Metrics

| Metric | Target |
|--------|--------|
| Lead response within SLA | 90% |
| MQL → SQL conversion | 40% |
| SQL → deal conversion | 20% |

## Cross-Reference

| For | See |
|-----|-----|
| BANT qualification, MQL/SQL stages | [lead-qualification.md](../business-processes/lead-qualification.md) |
| Buyer pipeline stages | [sales-pipeline.md](../business-processes/sales-pipeline.md) |
