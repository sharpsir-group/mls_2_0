# Personalization & Recommendation Engine

> **For Lovable**: This spec defines how personalized property recommendations work.
> Phase 4 feature (BI + AI Launch, Jul-Oct 2026). Spec it now to guide data collection decisions.

---

## Visitor Profiling (Anonymous, Pre-Auth)

| Category | Attributes |
|----------|------------|
| **System** | IP geolocation (country, city), device type, OS/browser, datetime/timezone, referral source |
| **Behavioral** | Pages visited, listings viewed, search queries, time-on-page, scroll depth, click patterns |

**Storage**: Supabase `visitor_sessions` table with anonymous session ID (cookie), linked to user on login. Session merges on login: anonymous events attach to user record for preference building.

**Privacy**: GDPR consent required before tracking (cookie banner). Retention: 90 days anonymous; linked to user for authenticated. See [compliance.md](../platform/compliance.md) for DSAR and retention rules. No behavioral tracking before consent.

## Semantic Ranking (Listing Personalization)

| Component | Implementation |
|-----------|-----------------|
| **Embeddings** | Vector embeddings for listing descriptions using pgvector (Supabase extension) |
| **User preference vector** | Built from: viewed listings, saved favorites, search filters, explicit preferences |
| **Ranking formula** | `score = α × semantic_similarity + β × recency + γ × price_fit + δ × location_proximity` |
| **Cold-start fallback** | Popularity-based ranking by market, then property type |

Alpha/beta/gamma/delta weights tuned per market (Cyprus, Hungary, Kazakhstan).

## Recommendation Engine

| Type | Method | Use Case |
|------|--------|----------|
| Similar listings | Embedding cosine similarity | "More like this" on listing detail |
| You might also like | Collaborative filtering | Cross-user preference patterns |
| New matches | Saved search criteria | Push notifications when new listings match |

**Integration points**: Client Portal (auth), Website (anon + auth), Broker App (client recs). See [ecosystem-architecture.md](../platform/ecosystem-architecture.md) for channel diagram.

**Cold-start**: New visitors get popularity-based ranking. After 3+ listing views or 1 saved search, switch to semantic + collaborative signals.

## Data Collection Architecture

```
Client-side event tracker → Edge Function `track-visitor-event` → CDL tables
```

| CDL Table | Purpose |
|-----------|---------|
| `visitor_sessions` | Anonymous session, system attributes, linked user on login |
| `visitor_events` | Behavioral events (view, search, click) |
| `user_preferences` | Explicit + inferred preferences (price range, location, property type) |
| `listing_embeddings` | pgvector embeddings for semantic search (description + features) |

**Sync**: CDL → Databricks for model training and analytics. Embeddings generated in Databricks or via Edge Function; stored in CDL for real-time ranking. Batch refresh for embeddings: nightly or on listing publish.

## Success Metrics

| Metric | Target |
|--------|--------|
| CTR on recommended | 2× vs non-recommended |
| Time-to-inquiry | 30% faster |
| Listing coverage | % of inventory surfaced in recommendations |

## Implementation Phasing

| Phase | Scope |
|-------|-------|
| P0 | CDL tables (`visitor_sessions`, `visitor_events`), cookie consent, `track-visitor-event` Edge Function |
| P1 | `user_preferences`, `listing_embeddings`, semantic ranking, "Similar listings" block |
| P2 | Collaborative filtering, "You might also like", push notifications for saved searches |

## Cross-Reference

| For | See |
|-----|-----|
| Ecosystem channels and AI/ML layer | [ecosystem-architecture.md](../platform/ecosystem-architecture.md) |
| GDPR consent, cookie banner, retention | [compliance.md](../platform/compliance.md) |
| CDL schema and RESO tables | [dash-data-model.md](../data-models/dash-data-model.md) |
| Phase 4 roadmap and BI+AI launch | [digital-strategy-2026-2028.md](../vision/digital-strategy-2026-2028.md) |
