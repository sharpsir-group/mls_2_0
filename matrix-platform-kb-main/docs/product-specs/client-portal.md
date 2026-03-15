# Client Portal — Product Specification

> **For Lovable**: This spec defines the buyer/seller self-service portal.
> RESO Resources: Property, Media, ShowingAppointment, OpenHouse, Contacts

---

## Overview

Self-service portal for authenticated buyers and sellers to browse curated property lists, schedule showings, exchange documents, and track transactions. Replaces broker-mediated back-and-forth for routine tasks.

## User Personas

| Persona | Profile | Expectations |
|---------|----------|---------------|
| **UHNWI Buyer** | High-net-worth, €2M+ budget | Luxury UX, minimal friction, white-glove digital experience |
| **Developer Landlord** | Portfolio of 30+ units | Data and analytics, market insights, tenant metrics |

## Key User Flows

1. **Login → Dashboard**: Matrix SSO login → personalized dashboard with curated listings
2. **Browse → Request Showing**: Curated lists → listing detail → request showing
3. **Showing → Transaction**: Showing confirmed → document exchange → transaction tracker
4. **Saved Searches**: Save criteria → "New matches" push notifications

## RESO Resources Used

| Resource | Access | Purpose |
|----------|--------|---------|
| Property | r | Browse listings, detail view |
| Media | r | Images, virtual tours |
| ShowingAppointment | cr | Request and manage showings |
| OpenHouse | r | View open house schedule |
| Contacts | ru | Profile, preferences, document exchange |

## Acceptance Criteria

| Criterion | Target |
|----------|--------|
| Login (SSO redirect + session) | <3s |
| Listing detail load | <1s |
| Showing request confirmation | <5s |

## Success Metrics

| Metric | Target |
|--------|--------|
| Clients logging in monthly | 50% |
| Showings scheduled via portal | 30% |
| Broker admin time reduction | 25% |

## Phase 4 Features

- Personalized recommendations based on viewing history
- Semantic matching for curated lists (see [personalization.md](personalization.md))

## Cross-Reference

| For | See |
|-----|-----|
| Personalization and recommendations | [personalization.md](personalization.md) |
| App build patterns, auth, RLS | [app-template.md](../platform/app-template.md) |
| Buyer-side pipeline stages | [sales-pipeline.md](../business-processes/sales-pipeline.md) |
