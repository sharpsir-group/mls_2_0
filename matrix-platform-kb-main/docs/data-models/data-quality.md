# Data Quality — Verification, Validation, and Reporting

> Source: `mls_2_0/scripts/`, `mls_2_0/notebooks/`
>
> **For Lovable**: This document describes how data quality is verified in the MLS pipeline.
> You don't interact with these scripts directly — they ensure the data arriving in your
> Supabase CDL tables is correct and RESO-compliant.

## Overview

The MLS 2.0 pipeline includes four verification tools that validate data at multiple levels:
source-to-target record counts, RESO compliance, field coverage, type correctness, and
cross-resource foreign key integrity. Results are delivered via HTML email reports.

## Verification Scripts

### 1. `verify_data_integrity.sh` — Qobrix API vs RESO Gold

The primary integrity test. Compares Qobrix source API data against the RESO gold layer in Databricks.

**Checks performed:**
- Record counts: bronze vs gold for all 6 RESO resources (Property, Member, Office, Media, Contacts, ShowingAppointment)
- RESO compliance: validates `StandardStatus` enum values (Active, Pending, Closed, etc.)
- RESO compliance: validates `PropertyType` enum values (Apartment, SingleFamilyDetached, etc.)
- Required fields: presence of `ListingKey`, `StandardStatus`, `PropertyType` in every record
- Field coverage: 48 RESO standard fields + 120+ extension fields
- Export pipeline: HomeOverseas XML feed generation and record count

**Run from**: `mls_2_0/` directory
**Command**: `./scripts/verify_data_integrity.sh`

### 2. `verify_api_integrity.sh` — Qobrix ↔ RESO API Two-Way

End-to-end comparison between the Qobrix source API and the RESO Web API output.

**Checks performed:**
- Property count verification (source vs API output)
- Sample property data comparison (price, city, bedrooms)
- Media/photo counts including project media
- Agent/Member verification
- Contact verification
- Field transformation correctness (Qobrix field → RESO field)
- RESO type compliance (numeric, string, date types)
- Media URL validation (full paths, accessibility)
- HomeOverseas XML feed validation

### 3. `verify_dash_api_integrity.sh` — DASH JSON ↔ RESO API

Validates the DASH (Anywhere.com) data source integration for Hungary and Kazakhstan.

**Checks performed:**
- Property count and data verification (DASH source vs RESO API)
- Media count verification
- Features mapping validation (View, Flooring, Cooling, Heating)
- Agent/Office data verification
- Data source and office key verification (`SHARPSIR-HU-001`, `SHARPSIR-KZ-001`)
- RESO type compliance
- Media URL and dimensions validation
- Agent and geolocation completeness

### 4. `10_verify_data_integrity_qobrix_vs_reso.py` — Databricks Notebook

A Databricks notebook that performs deep cross-layer integrity checks within the ETL pipeline.

**Checks performed:**
- Bidirectional property matching (every source record has a gold record and vice versa)
- Field-level integrity checks (value-by-value comparison for key fields)
- RESO enum validation against the Data Dictionary standard
- Foreign key integrity: Property → Member (`ListAgentKey`), Media → Property (`ResourceRecordKey`), ShowingAppointment → Property (`ListingKey`), Contacts → Member (`ContactAssignedToKey`)
- Cross-resource linkage validation (every media record links to a valid property)

## Validation Rules

### RESO Enum Compliance

| Field | Valid Values |
|-------|------------|
| `StandardStatus` | Active, ActiveUnderContract, Pending, Hold, Withdrawn, Closed, Expired, Cancelled, Delete, Incomplete, ComingSoon |
| `PropertyType` | Apartment, SingleFamilyDetached, Townhouse, Land, CommercialSale, ResidentialIncome |

### Required Fields

Every property record must have: `ListingKey`, `StandardStatus`, `PropertyType`.

### Type Validation

| Category | Fields | Expected Type |
|----------|--------|---------------|
| Numeric | `ListPrice`, `BedroomsTotal`, `BathroomsTotalInteger`, `LivingArea` | INT or DECIMAL |
| String | `City`, `ListingKey`, `StandardStatus` | STRING |
| Optional | Nullable fields validated for correct NULL handling | NULL or typed |
| Datetime | `ModificationTimestamp`, `ListingContractDate` | TIMESTAMP |

### Data Type Progression

| Layer | Column Types | Validation |
|-------|-------------|------------|
| Bronze | All STRING (raw API data) | Schema presence only |
| Silver | INT, DECIMAL, TIMESTAMP, BOOLEAN | Type casting validated |
| Gold | RESO-typed (standard + extension fields) | Full RESO compliance |

### Foreign Key Integrity

| Relationship | FK Field | Parent Table |
|-------------|----------|-------------|
| Property → Member | `ListAgentKey` | `reso_gold.member` |
| Media → Property | `ResourceRecordKey` | `reso_gold.property` |
| ShowingAppointment → Property | `ListingKey` | `reso_gold.property` |
| Contacts → Member | `ContactAssignedToKey` | `reso_gold.member` |

## Reporting

### Email Reports

After each pipeline run, an HTML email report is sent to the pipeline owner.

**Report contents:**
- Pipeline status: SUCCESS / FAILED / WARNING
- Duration and timing
- Data summary: record counts and changes per entity (inserts, updates, deletes)
- ETL job success/failure counts per notebook
- API integration test results (if run)
- Full log content (collapsible section)
- Multi-source status tracking (Cyprus, Hungary, Kazakhstan)

**Recipient**: Pipeline owner (configurable via environment variable)

### Pipeline Duration Tracking

Each CDC run records:
- Start and end timestamps
- Per-entity change counts (via `cdc_metadata` table)
- Total API calls made
- Success/failure status per ETL notebook

## Current Gaps

The following capabilities are planned but not yet implemented:

| Gap | Impact | Planned Solution |
|-----|--------|-----------------|
| No continuous monitoring | Quality issues only detected on next scheduled run | `data_quality_runs` table + scheduled verification |
| No alerting beyond email | Failures may be missed | Telegram alerts on quality check failures |
| No historical trend tracking | Cannot detect gradual data degradation | DQ results stored in Supabase for trend analysis |
| No schema contract enforcement | Bronze/Silver/Gold transitions not formally validated | Great Expectations or JSON Schema contracts |

## Cross-Reference

| For | See |
|-----|-----|
| ETL pipeline architecture | [etl-pipeline.md](etl-pipeline.md) |
| MLS pipeline overview | [mls-datamart.md](../platform/mls-datamart.md) |
| RESO canonical schema | [reso-canonical-schema.md](reso-canonical-schema.md) |
| Operations and monitoring | [operations.md](../platform/operations.md) |
