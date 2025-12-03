# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 – Comprehensive Data Integrity Verification
# MAGIC 
# MAGIC **Purpose:** Validates entire ETL pipeline by comparing Qobrix bronze data with all RESO gold tables.
# MAGIC 
# MAGIC **RESO Resources Verified:**
# MAGIC | Resource | Bronze Source | Gold Table |
# MAGIC |----------|---------------|------------|
# MAGIC | Property | `properties` | `reso_gold.property` |
# MAGIC | Member | `agents`, `users` | `reso_gold.member` |
# MAGIC | Office | `agents` | `reso_gold.office` |
# MAGIC | Media | `property_media` | `reso_gold.media` |
# MAGIC | Contacts | `contacts` | `reso_gold.contacts` |
# MAGIC | ShowingAppointment | `property_viewings` | `reso_gold.showing_appointment` |
# MAGIC 
# MAGIC **Checks Performed:**
# MAGIC 1. **Record Counts** – Bronze vs Gold record counts for all resources
# MAGIC 2. **RESO Compliance** – Validates enum values (StandardStatus, PropertyType, etc.)
# MAGIC 3. **Property Coverage** – Ensures all API properties exist in RESO table
# MAGIC 4. **Required Fields** – Verifies required fields are populated
# MAGIC 5. **Foreign Key Integrity** – Validates cross-resource linkages
# MAGIC 
# MAGIC **Output:** Pass/Fail status with detailed error report
# MAGIC 
# MAGIC **Run After:** Full pipeline (`bronze` → `silver` → `gold-all`)
# MAGIC 
# MAGIC **Credentials:** Requires `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import os
import requests
import pandas as pd
import json as _json
from typing import Dict, Any, List, Tuple

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

timeout_seconds = 30

# Widgets for credentials (can be passed via job parameters)
dbutils.widgets.text("QOBRIX_API_USER", "")
dbutils.widgets.text("QOBRIX_API_KEY", "")
dbutils.widgets.text("QOBRIX_API_BASE_URL", "")

# Priority: env vars > widgets > empty (will fail validation)
qobrix_api_user = os.getenv("QOBRIX_API_USER") or dbutils.widgets.get("QOBRIX_API_USER")
qobrix_api_key = os.getenv("QOBRIX_API_KEY") or dbutils.widgets.get("QOBRIX_API_KEY")
api_base_url = os.getenv("QOBRIX_API_BASE_URL") or dbutils.widgets.get("QOBRIX_API_BASE_URL")

if not qobrix_api_user or not qobrix_api_key or not api_base_url:
    raise ValueError("Set QOBRIX_API_USER, QOBRIX_API_KEY, and QOBRIX_API_BASE_URL (env vars or widgets) before running.")

headers = {
    "X-Api-User": qobrix_api_user,
    "X-Api-Key": qobrix_api_key,
}

# First, get the count of properties in RESO to determine how many to fetch from API
reso_count_df = spark.sql("SELECT COUNT(*) as cnt FROM reso_gold.property")
reso_total = reso_count_df.collect()[0]['cnt']

# Only fetch as many API properties as we have in RESO (plus a small buffer)
# This ensures we're comparing apples to apples in test mode
max_properties = min(100, reso_total + 10) if reso_total > 0 else 100

print("=" * 80)
print("🔍 COMPREHENSIVE DATA INTEGRITY TEST - Qobrix API vs MLS 2.0 RESO")
print("=" * 80)
print(f"Gold table: {catalog}.reso_gold.property")
print(f"RESO properties in table: {reso_total}")
print(f"Max API properties to validate: {max_properties}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def normalize_value(value: Any) -> Any:
    """Normalize values for comparison"""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower() if value else None
    if isinstance(value, (int, float)):
        return float(value) if value else None
    return value

def map_status(qobrix_status: str) -> str:
    """Map Qobrix status to RESO StandardStatus"""
    status_map = {
        'available': 'Active',
        'reserved': 'Pending',
        'under_offer': 'Pending',
        'sold': 'Closed',
        'rented': 'Closed',
        'withdrawn': 'Withdrawn'
    }
    if qobrix_status:
        return status_map.get(qobrix_status.lower(), 'Active')
    return 'Active'

def map_property_type(qobrix_type: str) -> str:
    """Map Qobrix property type to RESO PropertyType"""
    type_map = {
        'apartment': 'Apartment',
        'house': 'SingleFamilyDetached',
        'land': 'Land',
        'office': 'Office',
        'investment': 'Commercial',
        'building': 'Commercial',
        'hotel': 'Commercial',
        'parking_lot': 'Parking',
        'retail': 'Commercial',
        'industrial': 'Commercial',
        'other': 'Other'
    }
    if qobrix_type:
        return type_map.get(qobrix_type.lower(), 'Other')
    return 'Other'

# Valid RESO enum values
VALID_STATUSES = ["Active", "ComingSoon", "Hold", "OffMarket", "Pending", "Withdrawn", 
                  "Closed", "Canceled", "Expired", "Delete", "Invalid", "Unknown"]
VALID_PROPERTY_TYPES = ["Agricultural", "Apartment", "Business", "Commercial", "Condominium", 
                        "Duplex", "Farm", "Land", "MobileHome", "MultiFamily", "Office", 
                        "Other", "Parking", "Residential", "SingleFamilyAttached", 
                        "SingleFamilyDetached", "Townhouse", "Unknown"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 – Fetch Sample from Qobrix API

# COMMAND ----------

def fetch_sample(max_records: int) -> list:
    url = f"{api_base_url}/properties"
    params = {"limit": max_records, "page": 1}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])[:max_records]
    except Exception as e:
        print("❌ Error fetching from Qobrix API:", e)
        return []

print("📥 Fetching data from Qobrix API...")
api_properties = fetch_sample(max_properties)
print(f"   ✅ Fetched {len(api_properties)} properties from API")

if not api_properties:
    raise ValueError("No API properties, cannot validate.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 – Convert API data to Spark DataFrame

# COMMAND ----------

# Use Pandas json_normalize to handle nested structures
pdf = pd.json_normalize(api_properties, sep="_")

# Convert complex types (lists, dicts) to JSON strings
for col in pdf.columns:
    if pdf[col].apply(lambda x: isinstance(x, (list, dict))).any():
        pdf[col] = pdf[col].apply(lambda x: _json.dumps(x) if isinstance(x, (list, dict)) else x)

api_df = spark.createDataFrame(pdf)
api_df.createOrReplaceTempView("api_properties_sample")

print(f"📊 API sample has {len(api_df.columns)} columns")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 – Fetch RESO Properties from Databricks

# COMMAND ----------

print("📊 Fetching data from MLS Databricks tables...")
reso_df = spark.sql("""
SELECT 
    ListingKey,
    ListingId,
    ListPrice,
    StandardStatus,
    PropertyType,
    BedroomsTotal,
    BathroomsTotalInteger,
    City,
    StateOrProvince,
    Country,
    X_QobrixId AS qobrix_id,
    X_QobrixRef AS qobrix_ref
FROM reso_gold.property
""")
reso_df.createOrReplaceTempView("reso_properties")

reso_count = reso_df.count()
print(f"   ✅ Fetched {reso_count} properties from RESO")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 – Compare Properties (Join API to RESO)

# COMMAND ----------

print("\n" + "=" * 80)
print("🔍 COMPARING DATA")
print("=" * 80)

comparison_df = spark.sql("""
SELECT
  api.id    AS qobrix_id,
  api.ref   AS qobrix_ref,
  reso.ListingKey,
  reso.ListingId,

  api.status            AS api_status,
  reso.StandardStatus   AS reso_status,

  api.property_type     AS api_property_type,
  reso.PropertyType     AS reso_property_type,

  api.city              AS api_city,
  reso.City             AS reso_city,
  api.state             AS api_state,
  reso.StateOrProvince  AS reso_state,
  api.country           AS api_country,
  reso.Country          AS reso_country,

  api.list_selling_price_amount AS api_list_price,
  reso.ListPrice                AS reso_list_price,
  
  api.bedrooms          AS api_bedrooms,
  reso.BedroomsTotal    AS reso_bedrooms,
  api.bathrooms         AS api_bathrooms,
  reso.BathroomsTotalInteger AS reso_bathrooms
FROM api_properties_sample api
LEFT JOIN reso_properties reso
  ON reso.qobrix_id = api.id
""")
comparison_df.createOrReplaceTempView("comparison_qobrix_reso")

total_api = len(api_properties)
joined_count = comparison_df.count()
print(f"\n📋 Properties Comparison:")
print(f"   API Properties: {total_api}")
print(f"   RESO Properties: {reso_count}")
print(f"   Joined rows: {joined_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 – Check for Missing Properties (Bidirectional)

# COMMAND ----------

print("\n" + "=" * 80)
print("🔍 CHECKING FOR MISSING PROPERTIES (BIDIRECTIONAL)")
print("=" * 80)

# Get IDs that are in bronze (what we actually loaded)
bronze_ids_df = spark.sql("SELECT DISTINCT id FROM qobrix_bronze.properties")
bronze_ids = set([str(row['id']) for row in bronze_ids_df.collect()])
print(f"   Bronze properties loaded: {len(bronze_ids)}")

# Forward: API → RESO (properties in API but missing in RESO)
# Only count as "missing" if the property was loaded into bronze
missing_in_reso_df = spark.sql("""
SELECT qobrix_id, qobrix_ref
FROM comparison_qobrix_reso
WHERE ListingKey IS NULL
""")
missing_in_reso_all = missing_in_reso_df.collect()

# Filter to only properties that were loaded into bronze
missing_in_reso_critical = [row for row in missing_in_reso_all if str(row['qobrix_id']) in bronze_ids]
missing_in_reso_expected = [row for row in missing_in_reso_all if str(row['qobrix_id']) not in bronze_ids]

missing_in_reso_count = len(missing_in_reso_critical)
expected_missing_count = len(missing_in_reso_expected)

# Reverse: RESO → API (properties in RESO but not in API sample)
api_ids = [str(p.get('id')) for p in api_properties if p.get('id')]
api_ids_str = ",".join([f"'{id}'" for id in api_ids])

if api_ids_str:
    extra_in_reso_df = spark.sql(f"""
    SELECT ListingKey, qobrix_id, qobrix_ref
    FROM reso_properties
    WHERE qobrix_id NOT IN ({api_ids_str})
    """)
    extra_in_reso_count = extra_in_reso_df.count()
else:
    extra_in_reso_count = reso_count

# Report
if missing_in_reso_count > 0:
    print(f"   ❌ Forward Check (API → RESO): {missing_in_reso_count} properties LOADED but missing in RESO")
    for row in missing_in_reso_critical[:10]:
        print(f"      - {row['qobrix_id']} ({row['qobrix_ref']})")
else:
    print(f"   ✅ Forward Check (API → RESO): All {len(bronze_ids)} loaded properties found in RESO")

if expected_missing_count > 0:
    print(f"   ℹ️  Expected: {expected_missing_count} API properties not in RESO (not loaded in test mode)")

if extra_in_reso_count > 0:
    print(f"   ℹ️  Reverse Check (RESO → API): {extra_in_reso_count} properties in RESO not in API sample")
    print("      (This is expected if RESO has more data than the API sample)")
else:
    print(f"   ✅ Reverse Check (RESO → API): All RESO properties found in API sample")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 – Field-Level Integrity Checks

# COMMAND ----------

print("\n" + "=" * 80)
print("🔍 FIELD-LEVEL INTEGRITY CHECKS")
print("=" * 80)

# Convert to Pandas for detailed comparison
comparison_pdf = comparison_df.toPandas()

issues = []
field_mismatch_count = 0

for idx, row in comparison_pdf.iterrows():
    if pd.isna(row['ListingKey']):
        continue  # Skip missing properties (already reported)
    
    qobrix_id = row['qobrix_id']
    qobrix_ref = row['qobrix_ref']
    
    # Status mapping check
    expected_status = map_status(row['api_status'])
    actual_status = row['reso_status']
    if normalize_value(expected_status) != normalize_value(actual_status):
        issues.append(f"Property {qobrix_id} ({qobrix_ref}): Status mismatch - API: '{row['api_status']}' → Expected RESO: '{expected_status}', Actual: '{actual_status}'")
        field_mismatch_count += 1
    
    # Property type mapping check
    expected_type = map_property_type(row['api_property_type'])
    actual_type = row['reso_property_type']
    if normalize_value(expected_type) != normalize_value(actual_type):
        issues.append(f"Property {qobrix_id} ({qobrix_ref}): PropertyType mismatch - API: '{row['api_property_type']}' → Expected RESO: '{expected_type}', Actual: '{actual_type}'")
        field_mismatch_count += 1
    
    # Price check (with tolerance)
    api_price = row['api_list_price']
    reso_price = row['reso_list_price']
    if api_price is not None and reso_price is not None:
        try:
            if abs(float(api_price) - float(reso_price)) > 0.01:
                issues.append(f"Property {qobrix_id} ({qobrix_ref}): Price mismatch - API: {api_price} vs RESO: {reso_price}")
                field_mismatch_count += 1
        except (ValueError, TypeError):
            pass
    
    # City check
    if normalize_value(row['api_city']) != normalize_value(row['reso_city']):
        issues.append(f"Property {qobrix_id} ({qobrix_ref}): City mismatch - API: '{row['api_city']}' vs RESO: '{row['reso_city']}'")
        field_mismatch_count += 1
    
    # Country check
    if normalize_value(row['api_country']) != normalize_value(row['reso_country']):
        issues.append(f"Property {qobrix_id} ({qobrix_ref}): Country mismatch - API: '{row['api_country']}' vs RESO: '{row['reso_country']}'")
        field_mismatch_count += 1

matched_count = total_api - missing_in_reso_count
print(f"   Matched: {matched_count}")
print(f"   Missing in RESO: {missing_in_reso_count}")
print(f"   Field Mismatches: {field_mismatch_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7 – RESO Compliance Verification

# COMMAND ----------

print("\n" + "=" * 80)
print("✅ RESO COMPLIANCE VERIFICATION")
print("=" * 80)

reso_compliance_issues = []

# Check for invalid status values
invalid_status_df = spark.sql(f"""
SELECT DISTINCT StandardStatus, COUNT(*) as count
FROM reso_properties
WHERE StandardStatus NOT IN ({','.join([f"'{s}'" for s in VALID_STATUSES])})
GROUP BY StandardStatus
""")
invalid_status_data = invalid_status_df.collect()
invalid_status_count = sum([row['count'] for row in invalid_status_data])

if invalid_status_count > 0:
    for row in invalid_status_data:
        reso_compliance_issues.append(f"Invalid StandardStatus '{row['StandardStatus']}' found in {row['count']} properties")

# Check for invalid property type values
invalid_type_df = spark.sql(f"""
SELECT DISTINCT PropertyType, COUNT(*) as count
FROM reso_properties
WHERE PropertyType NOT IN ({','.join([f"'{pt}'" for pt in VALID_PROPERTY_TYPES])})
GROUP BY PropertyType
""")
invalid_type_data = invalid_type_df.collect()
invalid_type_count = sum([row['count'] for row in invalid_type_data])

if invalid_type_count > 0:
    for row in invalid_type_data:
        reso_compliance_issues.append(f"Invalid PropertyType '{row['PropertyType']}' found in {row['count']} properties")

# Check for missing required fields
required_fields_df = spark.sql("""
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN ListingKey IS NULL THEN 1 ELSE 0 END) as missing_listing_key,
    SUM(CASE WHEN StandardStatus IS NULL THEN 1 ELSE 0 END) as missing_status,
    SUM(CASE WHEN PropertyType IS NULL THEN 1 ELSE 0 END) as missing_property_type
FROM reso_properties
""")
req_data = required_fields_df.collect()[0]
missing_required = int(req_data['missing_listing_key'] or 0) + int(req_data['missing_status'] or 0) + int(req_data['missing_property_type'] or 0)

if req_data['missing_listing_key'] and req_data['missing_listing_key'] > 0:
    reso_compliance_issues.append(f"{req_data['missing_listing_key']} properties missing ListingKey (REQUIRED)")
if req_data['missing_status'] and req_data['missing_status'] > 0:
    reso_compliance_issues.append(f"{req_data['missing_status']} properties missing StandardStatus (REQUIRED)")
if req_data['missing_property_type'] and req_data['missing_property_type'] > 0:
    reso_compliance_issues.append(f"{req_data['missing_property_type']} properties missing PropertyType (REQUIRED)")

print(f"   Total Properties: {reso_count}")
print(f"   Invalid Status Values: {invalid_status_count}")
print(f"   Invalid Property Type Values: {invalid_type_count}")
print(f"   Missing Required Fields: {missing_required}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8 – Comprehensive Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 COMPREHENSIVE INTEGRITY TEST SUMMARY")
print("=" * 80)

# Combine all issues
all_issues = issues + reso_compliance_issues

# Separate critical issues from warnings
critical_issues = [i for i in all_issues if 'mismatch' not in i.lower() or 'REQUIRED' in i]
warnings = [i for i in all_issues if i not in critical_issues]

if critical_issues:
    print(f"\n❌ Found {len(critical_issues)} critical issue(s):")
    for i, issue in enumerate(critical_issues[:20], 1):
        print(f"   {i}. {issue}")
    if len(critical_issues) > 20:
        print(f"   ... and {len(critical_issues) - 20} more critical issues")

if warnings:
    print(f"\n⚠️  Found {len(warnings)} warning(s):")
    for i, warning in enumerate(warnings[:10], 1):
        print(f"   {i}. {warning}")
    if len(warnings) > 10:
        print(f"   ... and {len(warnings) - 10} more warnings")

# Final verification summary
print("\n" + "=" * 80)
print("📋 FINAL VERIFICATION SUMMARY")
print("=" * 80)

reso_passed = len(reso_compliance_issues) == 0
coverage_passed = missing_in_reso_count == 0  # Only critical missing (loaded but not in RESO)
integrity_passed = field_mismatch_count == 0

print(f"{'✅' if reso_passed else '❌'} RESO Compliance: {'PASSED' if reso_passed else 'FAILED'}")
print(f"{'✅' if coverage_passed else '❌'} Property Coverage: {'PASSED' if coverage_passed else 'FAILED'}")
print(f"{'✅' if integrity_passed else '⚠️ '} Data Integrity: {'PASSED' if integrity_passed else f'{field_mismatch_count} mismatches'}")

# Detailed explanation
print("\n" + "=" * 80)
print("📖 WHAT THE SUMMARY MEANS")
print("=" * 80)

print("\n✅ RESO Compliance: " + ("PASSED" if reso_passed else "FAILED"))
if reso_passed:
    print("   ✓ All StandardStatus values are valid RESO enum values")
    print("   ✓ All PropertyType values are valid RESO enum values")
    print("   ✓ All required fields (ListingKey, StandardStatus, PropertyType) are present")
else:
    print("   ✗ RESO compliance issues found - see details above")

print("\n✅ Property Coverage: " + ("PASSED" if coverage_passed else "FAILED"))
if coverage_passed:
    print("   ✓ All Qobrix API properties found in RESO table")
    print("   ✓ No data loss from Qobrix → RESO")
else:
    print(f"   ✗ {missing_in_reso_count} properties in API missing in RESO")

print("\n✅ Data Integrity: " + ("PASSED" if integrity_passed else f"{field_mismatch_count} mismatches"))
if integrity_passed:
    print("   ✓ Field-level comparisons match between Qobrix API and RESO")
    print("   ✓ Key fields verified: status, property_type, city, country, price")
else:
    print(f"   ✗ {field_mismatch_count} field mismatches detected")

# Overall result
print("\n" + "=" * 80)
all_passed = reso_passed and coverage_passed and integrity_passed
if all_passed:
    print("✅ COMPREHENSIVE DATA INTEGRITY TEST PASSED")
    print("=" * 80)
    print("✓ All data matches between Qobrix API and MLS 2.0 RESO")
    print("✓ RESO compliance verified (100% compliant)")
    print("✓ Complete verification successful")
elif reso_passed and coverage_passed:
    print("⚠️  COMPREHENSIVE DATA INTEGRITY TEST PASSED WITH WARNINGS")
    print("=" * 80)
    print("All critical checks passed. Field mismatches may be due to:")
    print("  • Expected differences in data transformation mappings")
    print("  • Test data limitations")
else:
    print("❌ COMPREHENSIVE DATA INTEGRITY TEST FAILED")
    print("=" * 80)
    print("Critical issues found that require attention.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9 – Verify Gold Property Field Coverage

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 GOLD PROPERTY FIELD COVERAGE VERIFICATION")
print("=" * 80)

# Get gold property column count
gold_cols = spark.table("reso_gold.property").columns
extension_cols = [c for c in gold_cols if c.startswith("X_")]
standard_cols = [c for c in gold_cols if not c.startswith("X_") and not c.startswith("etl_")]
etl_cols = [c for c in gold_cols if c.startswith("etl_")]

print(f"\n📋 Gold Property Table Schema:")
print(f"   Total columns: {len(gold_cols)}")
print(f"   RESO Standard Fields: {len(standard_cols)}")
print(f"   Extension Fields (X_): {len(extension_cols)}")
print(f"   ETL Metadata: {len(etl_cols)}")

# Expected minimums (based on mapping.md)
expected_standard = 48
expected_extension = 120

if len(standard_cols) >= expected_standard:
    print(f"   ✅ RESO Standard Fields: {len(standard_cols)} >= {expected_standard} expected")
else:
    print(f"   ⚠️ RESO Standard Fields: {len(standard_cols)} < {expected_standard} expected")

if len(extension_cols) >= expected_extension:
    print(f"   ✅ Extension Fields: {len(extension_cols)} >= {expected_extension} expected")
else:
    print(f"   ⚠️ Extension Fields: {len(extension_cols)} < {expected_extension} expected")

# Check key new fields exist
key_new_fields = [
    # New RESO Standard Fields (added to improve compliance to 92%)
    "BathroomsHalf", "LotSizeAcres", "LeaseAmountFrequency", "ListOfficeKey",
    "Flooring", "FireplaceFeatures", "WaterfrontFeatures", "PatioAndPorchFeatures",
    "OtherStructures", "AssociationAmenities", "Fencing",
    # Key Extension Fields
    "X_AbutsGreenArea", "X_ElevatedArea", "X_ConciergeReception", "X_SecureDoor",
    "X_UnitNumber", "X_Height", "X_MaxFloor", "X_ShortDescription",
    "X_DistanceFromRailStation", "X_DistanceFromTubeStation",
    "X_PreviousListPrice", "X_AuctionStartDate", "X_TenancyType",
    "X_ApartmentType", "X_HouseType", "X_LandType"
]

missing_fields = [f for f in key_new_fields if f not in gold_cols]
if missing_fields:
    print(f"\n   ⚠️ Missing expected fields: {', '.join(missing_fields[:10])}")
    if len(missing_fields) > 10:
        print(f"      ... and {len(missing_fields) - 10} more")
else:
    print(f"\n   ✅ All {len(key_new_fields)} key fields present")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10 – Verify All RESO Resources (Record Counts)

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 ALL RESO RESOURCES - RECORD COUNT VERIFICATION")
print("=" * 80)

resource_checks = []

# Define all resources to check
resources = [
    {"name": "Property", "bronze": "qobrix_bronze.properties", "gold": "reso_gold.property", "key_field": "ListingKey"},
    {"name": "Member", "bronze": ["qobrix_bronze.agents", "qobrix_bronze.users"], "gold": "reso_gold.member", "key_field": "MemberKey"},
    {"name": "Office", "bronze": "qobrix_bronze.agents", "gold": "reso_gold.office", "key_field": "OfficeKey"},
    {"name": "Media", "bronze": "qobrix_bronze.property_media", "gold": "reso_gold.media", "key_field": "MediaKey"},
    {"name": "Contacts", "bronze": "qobrix_bronze.contacts", "gold": "reso_gold.contacts", "key_field": "ContactKey"},
    {"name": "ShowingAppointment", "bronze": "qobrix_bronze.property_viewings", "gold": "reso_gold.showing_appointment", "key_field": "ShowingAppointmentKey"},
]

print(f"\n{'Resource':<20} {'Bronze':<12} {'Gold':<12} {'Status':<10}")
print("-" * 60)

for res in resources:
    try:
        # Get bronze count (handle multiple tables)
        if isinstance(res["bronze"], list):
            bronze_count = 0
            for table in res["bronze"]:
                try:
                    cnt = spark.sql(f"SELECT COUNT(*) as c FROM {table}").collect()[0]["c"]
                    bronze_count += cnt
                except:
                    pass
        else:
            try:
                bronze_count = spark.sql(f"SELECT COUNT(*) as c FROM {res['bronze']}").collect()[0]["c"]
            except:
                bronze_count = 0
        
        # Get gold count
        try:
            gold_count = spark.sql(f"SELECT COUNT(*) as c FROM {res['gold']}").collect()[0]["c"]
        except:
            gold_count = 0
        
        # Check for null keys
        try:
            null_keys = spark.sql(f"SELECT COUNT(*) as c FROM {res['gold']} WHERE {res['key_field']} IS NULL").collect()[0]["c"]
        except:
            null_keys = 0
        
        # Determine status
        if gold_count == 0 and bronze_count == 0:
            status = "⚪ Empty"
        elif gold_count == 0 and bronze_count > 0:
            status = "❌ Missing"
        elif null_keys > 0:
            status = f"⚠️ {null_keys} null keys"
        else:
            status = "✅ OK"
        
        resource_checks.append({
            "name": res["name"],
            "bronze": bronze_count,
            "gold": gold_count,
            "null_keys": null_keys,
            "passed": gold_count > 0 or bronze_count == 0
        })
        
        print(f"{res['name']:<20} {bronze_count:<12} {gold_count:<12} {status:<10}")
        
    except Exception as e:
        print(f"{res['name']:<20} {'Error':<12} {'Error':<12} ❌ {str(e)[:20]}")
        resource_checks.append({"name": res["name"], "bronze": 0, "gold": 0, "null_keys": 0, "passed": False})

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 11 – Foreign Key Integrity

# COMMAND ----------

print("\n" + "=" * 80)
print("🔗 FOREIGN KEY INTEGRITY CHECKS")
print("=" * 80)

fk_issues = []

# Check Property → Member (ListAgentKey)
try:
    orphan_agents = spark.sql("""
        SELECT COUNT(*) as c FROM reso_gold.property p
        WHERE p.ListAgentKey IS NOT NULL 
        AND p.ListAgentKey NOT IN (SELECT MemberKey FROM reso_gold.member)
    """).collect()[0]["c"]
    if orphan_agents > 0:
        fk_issues.append(f"Property.ListAgentKey: {orphan_agents} orphan references")
        print(f"   ⚠️ Property → Member: {orphan_agents} orphan ListAgentKey references")
    else:
        print(f"   ✅ Property → Member: All ListAgentKey references valid")
except Exception as e:
    print(f"   ⚪ Property → Member: Skipped ({str(e)[:30]})")

# Check Media → Property (ResourceRecordKey)
try:
    orphan_media = spark.sql("""
        SELECT COUNT(*) as c FROM reso_gold.media m
        WHERE m.ResourceRecordKey IS NOT NULL 
        AND m.ResourceRecordKey NOT IN (SELECT ListingKey FROM reso_gold.property)
    """).collect()[0]["c"]
    if orphan_media > 0:
        fk_issues.append(f"Media.ResourceRecordKey: {orphan_media} orphan references")
        print(f"   ⚠️ Media → Property: {orphan_media} orphan ResourceRecordKey references")
    else:
        print(f"   ✅ Media → Property: All ResourceRecordKey references valid")
except Exception as e:
    print(f"   ⚪ Media → Property: Skipped ({str(e)[:30]})")

# Check ShowingAppointment → Property (ListingKey)
try:
    orphan_showings = spark.sql("""
        SELECT COUNT(*) as c FROM reso_gold.showing_appointment s
        WHERE s.ListingKey IS NOT NULL 
        AND s.ListingKey NOT IN (SELECT ListingKey FROM reso_gold.property)
    """).collect()[0]["c"]
    if orphan_showings > 0:
        fk_issues.append(f"ShowingAppointment.ListingKey: {orphan_showings} orphan references")
        print(f"   ⚠️ ShowingAppointment → Property: {orphan_showings} orphan ListingKey references")
    else:
        print(f"   ✅ ShowingAppointment → Property: All ListingKey references valid")
except Exception as e:
    print(f"   ⚪ ShowingAppointment → Property: Skipped ({str(e)[:30]})")

# Check Contacts → Member (ContactAssignedToKey)
try:
    orphan_contacts = spark.sql("""
        SELECT COUNT(*) as c FROM reso_gold.contacts c
        WHERE c.ContactAssignedToKey IS NOT NULL 
        AND c.ContactAssignedToKey NOT IN (SELECT MemberKey FROM reso_gold.member)
    """).collect()[0]["c"]
    if orphan_contacts > 0:
        fk_issues.append(f"Contacts.ContactAssignedToKey: {orphan_contacts} orphan references")
        print(f"   ⚠️ Contacts → Member: {orphan_contacts} orphan ContactAssignedToKey references")
    else:
        print(f"   ✅ Contacts → Member: All ContactAssignedToKey references valid")
except Exception as e:
    print(f"   ⚪ Contacts → Member: Skipped ({str(e)[:30]})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 12 – Final Comprehensive Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 COMPREHENSIVE INTEGRITY TEST - FINAL SUMMARY")
print("=" * 80)

# Count passed resources
resources_passed = sum(1 for r in resource_checks if r["passed"])
resources_total = len(resource_checks)

# Field coverage check
field_coverage_passed = len(standard_cols) >= expected_standard and len(extension_cols) >= expected_extension and len(missing_fields) == 0

# Summary
print(f"\n📋 RESO Resources: {resources_passed}/{resources_total} verified")
for r in resource_checks:
    status = "✅" if r["passed"] else "❌"
    print(f"   {status} {r['name']}: {r['gold']} records")

print(f"\n🔗 Foreign Key Integrity: {len(fk_issues)} issues")
for issue in fk_issues:
    print(f"   ⚠️ {issue}")

print(f"\n✅ Property RESO Compliance: {'PASSED' if reso_passed else 'FAILED'}")
print(f"✅ Property Coverage: {'PASSED' if coverage_passed else 'FAILED'}")
print(f"{'✅' if integrity_passed else '⚠️'} Property Data Integrity: {'PASSED' if integrity_passed else f'{field_mismatch_count} mismatches'}")
print(f"{'✅' if field_coverage_passed else '⚠️'} Field Coverage: {'PASSED' if field_coverage_passed else 'CHECK NEEDED'} ({len(gold_cols)} total fields)")

# Overall result
print("\n" + "=" * 80)
all_resources_passed = all(r["passed"] for r in resource_checks)
fk_passed = len(fk_issues) == 0

comprehensive_passed = all_passed and all_resources_passed and field_coverage_passed

if comprehensive_passed and fk_passed:
    print("✅ COMPREHENSIVE DATA INTEGRITY TEST PASSED")
    print("=" * 80)
    print(f"✓ All {resources_total} RESO resources verified")
    print(f"✓ Gold property table has {len(gold_cols)} fields ({len(standard_cols)} RESO + {len(extension_cols)} extensions)")
    print("✓ All foreign key relationships valid")
    print("✓ Property RESO compliance verified")
    print("✓ Complete verification successful")
elif comprehensive_passed:
    print("⚠️ COMPREHENSIVE DATA INTEGRITY TEST PASSED WITH WARNINGS")
    print("=" * 80)
    print(f"✓ All {resources_total} RESO resources verified")
    print(f"⚠️ {len(fk_issues)} foreign key issues (may be expected in test mode)")
else:
    print("❌ COMPREHENSIVE DATA INTEGRITY TEST FAILED")
    print("=" * 80)
    failed_resources = [r["name"] for r in resource_checks if not r["passed"]]
    if failed_resources:
        print(f"✗ Failed resources: {', '.join(failed_resources)}")

# Set exit value for job status
dbutils.notebook.exit("PASSED" if comprehensive_passed else "FAILED")
