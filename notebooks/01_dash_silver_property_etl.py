# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Dash Bronze -> Silver Property ETL
# MAGIC 
# MAGIC **Purpose:** Transforms raw Dash/Sotheby's properties from bronze to normalized silver layer.
# MAGIC 
# MAGIC **Input:** `mls2.dash_bronze.properties`
# MAGIC 
# MAGIC **Output:** `mls2.dash_silver.property` with:
# MAGIC - Cleaned identifiers (qobrix_id, qobrix_ref) - using Dash listingGuid/listingId
# MAGIC - Normalized attributes (bedrooms, bathrooms, areas)
# MAGIC - Typed columns (INT, DECIMAL, TIMESTAMP)
# MAGIC - Location fields (country, city, street, coordinates)
# MAGIC - Pricing (list_selling_price_amount)
# MAGIC 
# MAGIC **Run After:** load_dash_bronze.py (local script)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("Using catalog:", catalog)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Check Bronze

# COMMAND ----------

try:
    bronze_count = spark.sql("SELECT COUNT(*) AS c FROM dash_bronze.properties").collect()[0]["c"]
    print(f"📊 Dash Bronze properties: {bronze_count}")
    if bronze_count == 0:
        print("⚠️ Dash Bronze empty, aborting silver ETL.")
        dbutils.notebook.exit("No data to process")
except Exception as e:
    print(f"❌ Error reading dash bronze properties: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Create Silver Table `dash_silver.property`

# COMMAND ----------

# Ensure dash_silver schema exists
spark.sql("CREATE SCHEMA IF NOT EXISTS dash_silver")

# Check available columns in bronze
bronze_cols = set([c.lower() for c in spark.table("dash_bronze.properties").columns])
print(f"📋 Dash Bronze table has {len(bronze_cols)} columns")

# Build dynamic SQL based on available columns
def col_or_null(col_name, alias=None):
    """Return column reference if exists, else NULL"""
    alias = alias or col_name
    if col_name.lower() in bronze_cols:
        return f"p.{col_name} AS {alias}"
    else:
        return f"NULL AS {alias}"

transform_dash_to_silver_sql = f"""
CREATE OR REPLACE TABLE dash_silver.property AS
SELECT
    -- Identifiers (map Dash fields to Qobrix-style names for consistency)
    p.id                                    AS qobrix_id,
    p.ref                                   AS qobrix_ref,
    NULL                                    AS qobrix_legacy_id,
    p.source                                AS qobrix_source,

    -- Core attributes
    NULLIF(TRIM(p.property_name), '')       AS name,
    -- Description: Store remarks JSON as-is, will be parsed in Gold layer if needed
    -- For now, use property_name as description fallback
    COALESCE(
        NULLIF(TRIM(p.property_name), ''),
        ''
    )                                       AS description,
    p.status                                AS status,
    -- Dash doesn't have sale_rent field, infer from listing type
    CASE 
        WHEN LOWER(p.property_type) LIKE '%rent%' THEN 'for_rent'
        ELSE 'for_sale'
    END                                     AS sale_rent,
    -- Map Dash property types to Qobrix-style types
    CASE 
        WHEN LOWER(p.property_type) LIKE '%residential%' THEN
            CASE 
                WHEN LOWER(p.property_subtype) LIKE '%single%family%' OR LOWER(p.property_subtype) LIKE '%detached%' THEN 'house'
                WHEN LOWER(p.property_subtype) LIKE '%apartment%' OR LOWER(p.property_subtype) LIKE '%condo%' THEN 'apartment'
                ELSE 'house'
            END
        WHEN LOWER(p.property_type) LIKE '%commercial%' THEN 'office'
        WHEN LOWER(p.property_type) LIKE '%land%' THEN 'land'
        ELSE 'other'
    END                                     AS property_type,
    NULLIF(TRIM(p.property_subtype), '')   AS property_subtype_id,
    NULL                                    AS construction_stage,

    -- Bedrooms / bathrooms (cast via DOUBLE since bronze stores as strings)
    TRY_CAST(TRY_CAST(p.bedrooms AS DOUBLE) AS INT)   AS bedrooms,
    TRY_CAST(TRY_CAST(p.bathrooms AS DOUBLE) AS INT)  AS bathrooms,

    -- Location
    NULLIF(TRIM(p.country), '')             AS country,
    NULLIF(TRIM(p.state), '')               AS state,
    NULLIF(TRIM(p.city), '')                AS city,
    NULLIF(TRIM(p.district), '')           AS municipality,
    NULLIF(TRIM(p.post_code), '')          AS post_code,
    NULLIF(TRIM(p.street), '')             AS street,
    -- Build coordinates string from latitude/longitude
    CASE 
        WHEN p.latitude != '' AND p.longitude != '' 
        THEN CONCAT(TRIM(p.latitude), ',', TRIM(p.longitude))
        ELSE NULL
    END                                     AS coordinates,

    -- Size / area (convert to square meters if needed)
    -- Dash uses livingArea in various units, convert to square meters
    CASE 
        WHEN p.living_area_unit = 'SM' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2))
        WHEN p.living_area_unit = 'SF' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2)) * 0.092903
        WHEN p.living_area_unit = 'AC' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2)) * 4046.86
        ELSE TRY_CAST(p.living_area AS DECIMAL(18, 2))
    END                                     AS internal_area_amount,
    NULL                                    AS covered_area_amount,
    NULL                                    AS covered_verandas_amount,
    NULL                                    AS uncovered_verandas_amount,
    -- Lot size conversion
    CASE 
        WHEN p.lot_size_unit = 'SM' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2))
        WHEN p.lot_size_unit = 'SF' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2)) * 0.092903
        WHEN p.lot_size_unit = 'AC' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2)) * 4046.86
        ELSE TRY_CAST(p.lot_size AS DECIMAL(18, 2))
    END                                     AS plot_area_amount,
    NULL                                    AS roof_garden_area_amount,

    -- Pricing (use listPrice, convert currency if needed)
    TRY_CAST(p.list_selling_price_amount AS DECIMAL(18, 2)) AS list_selling_price_amount,
    NULL                                    AS price_per_square,
    NULL                                    AS website_status,
    TRY_CAST(NULLIF(TRIM(p.listed_date), '') AS DATE) AS listing_date,

    -- Timestamps (handle empty strings)
    TRY_CAST(NULLIF(TRIM(p.listed_date), '') AS TIMESTAMP) AS created_ts,
    TRY_CAST(NULLIF(TRIM(p.last_update_on), '') AS TIMESTAMP) AS modified_ts,

    -- Relationships (Dash doesn't have these)
    NULL                                    AS seller_id,
    NULL                                    AS project_id,

    -- Boolean flags
    -- Check features JSON for air conditioning
    CASE 
        WHEN p.features LIKE '%A/C%' OR p.features LIKE '%Air Conditioning%' THEN TRUE
        ELSE FALSE
    END                                     AS air_condition,
    FALSE                                   AS storage_space,
    FALSE                                   AS beach_front,

    -- ETL metadata
    CURRENT_TIMESTAMP()                     AS etl_timestamp,
    CONCAT('dash_silver_batch_', CURRENT_DATE()) AS etl_batch_id

FROM dash_bronze.properties p
WHERE p.id IS NOT NULL AND p.id != ''
"""

print("📊 Creating Dash silver table from bronze...")
spark.sql(transform_dash_to_silver_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM dash_silver.property").collect()[0]["c"]
print(f"✅ Dash Silver property records: {silver_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show sample data
print("\n📋 Sample Dash Silver Properties:")
spark.sql("""
    SELECT qobrix_id, qobrix_ref, name, status, property_type, 
           bedrooms, bathrooms, city, country, list_selling_price_amount
    FROM dash_silver.property
    LIMIT 5
""").show(truncate=False)

