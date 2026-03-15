# Data Contracts — ETL Schema Validation

> Source: `mls_2_0/` pipeline
>
> **For Lovable**: This document describes how data contracts enforce schema
> correctness between ETL layers. You don't interact with contracts directly —
> they ensure the data in your CDL tables is structurally sound.

## Overview

Data contracts formalize the expected schema at each ETL layer boundary. They catch schema drift, type mismatches, and missing required fields before bad data reaches the CDL.

## Contract Boundaries

Three transition points:

| Boundary | What Is Validated |
|----------|-------------------|
| **Source → Bronze** | Raw data lands correctly (column presence, no truncation) |
| **Bronze → Silver** | Type casting succeeds (STRING → INT, TIMESTAMP, etc.), normalization rules applied |
| **Silver → Gold** | RESO DD compliance (standard field names, valid enum values, FK integrity) |

## Contract Format

JSON Schema is the recommended approach. Each contract defines:

- **Table name**, layer, version
- **Required columns** (name, type, nullable)
- **Enum constraints** (valid values for StandardStatus, PropertyType, etc.)
- **FK constraints** (which columns reference which parent tables)
- **Row-level rules** (e.g., ListPrice must be > 0 when StandardStatus = Active)

### Example: Gold Property Contract

```json
{
  "table": "reso_gold.property",
  "version": "2.1.0",
  "required_columns": [
    {"name": "ListingKey", "type": "STRING", "nullable": false},
    {"name": "StandardStatus", "type": "STRING", "nullable": false, "enum": ["Active", "Pending", "Closed", "Withdrawn", "Expired"]},
    {"name": "PropertyType", "type": "STRING", "nullable": false},
    {"name": "ListPrice", "type": "DECIMAL", "nullable": true},
    {"name": "ListAgentKey", "type": "STRING", "nullable": true, "fk": "reso_gold.member.MemberKey"}
  ]
}
```

## Validation Approach

Pipeline step before each layer transition. On violation: log warning + continue (soft mode) or fail pipeline (strict mode). Configuration per contract.

## Implementation Status

Currently done via verification scripts (see [data-quality.md](data-quality.md)). Formal JSON Schema contracts are a planned enhancement.

## Planned Tooling

- **Great Expectations** (Python) — declarative expectations, profiling, documentation
- **Custom JSON Schema validator** — integrated into Databricks notebooks

## Cross-Reference

| For | See |
|-----|-----|
| ETL pipeline architecture | [etl-pipeline.md](etl-pipeline.md) |
| Data quality verification | [data-quality.md](data-quality.md) |
| MLS pipeline overview | [mls-datamart.md](../platform/mls-datamart.md) |
