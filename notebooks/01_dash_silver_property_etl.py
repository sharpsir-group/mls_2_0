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
# MAGIC - Cleaned identifiers (dash_id, dash_ref) - using Dash listingGuid/listingId
# MAGIC - Normalized attributes (bedrooms, bathrooms, areas)
# MAGIC - Typed columns (INT, DECIMAL, TIMESTAMP)
# MAGIC - Location fields (country, city, street, coordinates)
# MAGIC - Pricing (list_price)
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

# Use ROW_NUMBER to deduplicate by property id (same listing may appear in multiple source files)
transform_dash_to_silver_sql = """
CREATE OR REPLACE TABLE dash_silver.property AS
WITH ranked AS (
SELECT
    -- ═══════════════════════════════════════════════════════════════════════════
    -- IDENTIFIERS (Dash-specific naming)
    -- ═══════════════════════════════════════════════════════════════════════════
    p.id                                    AS dash_id,           -- listingGuid
    p.ref                                   AS dash_ref,          -- listingId
    p.source                                AS dash_source,       -- "dash_sothebys"
    p.office_key                            AS office_key,        -- "HSIR"

    -- ═══════════════════════════════════════════════════════════════════════════
    -- CORE ATTRIBUTES
    -- ═══════════════════════════════════════════════════════════════════════════
    NULLIF(TRIM(p.property_name), '')       AS name,
    NULLIF(TRIM(p.property_name), '')       AS description,       -- Will be enhanced with remarks
    p.status                                AS status,            -- AC, PS, CL, WD
    p.status_description                    AS status_description,
    
    -- Sale/Rent determination (Dash doesn't have explicit field)
    CASE 
        WHEN LOWER(p.property_type) LIKE '%rent%' THEN 'for_rent'
        ELSE 'for_sale'
    END                                     AS sale_rent,
    
    -- Property type normalization
    CASE 
        WHEN LOWER(p.property_type) LIKE '%residential%' THEN
            CASE 
                WHEN LOWER(p.property_subtype) LIKE '%single%family%' OR 
                     LOWER(p.property_subtype) LIKE '%detached%' OR
                     LOWER(p.property_subtype) LIKE '%villa%' THEN 'house'
                WHEN LOWER(p.property_subtype) LIKE '%apartment%' OR 
                     LOWER(p.property_subtype) LIKE '%condo%' OR
                     LOWER(p.property_subtype) LIKE '%flat%' THEN 'apartment'
                WHEN LOWER(p.property_subtype) LIKE '%townhouse%' THEN 'townhouse'
                ELSE 'house'
            END
        WHEN LOWER(p.property_type) LIKE '%commercial%' THEN 'office'
        WHEN LOWER(p.property_type) LIKE '%land%' THEN 'land'
        ELSE 'other'
    END                                     AS property_type,
    
    NULLIF(TRIM(p.property_subtype), '')    AS property_subtype,
    p.property_type_code                    AS property_type_code,
    p.property_subtype_code                 AS property_subtype_code,
    p.style_code                            AS style_code,
    p.style_description                     AS style_description,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- BEDROOMS / BATHROOMS
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(TRY_CAST(p.bedrooms AS DOUBLE) AS INT)   AS bedrooms,
    TRY_CAST(TRY_CAST(p.bathrooms AS DOUBLE) AS INT)  AS bathrooms,
    TRY_CAST(TRY_CAST(p.half_bath AS DOUBLE) AS INT)  AS half_bath,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- LOCATION
    -- ═══════════════════════════════════════════════════════════════════════════
    NULLIF(TRIM(p.country), '')             AS country,
    NULLIF(TRIM(p.country_name), '')        AS country_name,
    NULLIF(TRIM(p.state), '')               AS state,
    NULLIF(TRIM(p.state_name), '')          AS state_name,
    NULLIF(TRIM(p.city), '')                AS city,
    NULLIF(TRIM(p.district), '')            AS district,
    NULLIF(TRIM(p.post_code), '')           AS post_code,
    NULLIF(TRIM(p.street), '')              AS street,
    
    -- Coordinates as string "lat,lng" for consistency
    CASE 
        WHEN p.latitude IS NOT NULL AND p.latitude != '' 
         AND p.longitude IS NOT NULL AND p.longitude != ''
        THEN CONCAT(TRIM(p.latitude), ',', TRIM(p.longitude))
        ELSE NULL
    END                                     AS coordinates,
    
    -- Also keep separate lat/lng for direct access
    TRY_CAST(p.latitude AS DOUBLE)          AS latitude,
    TRY_CAST(p.longitude AS DOUBLE)         AS longitude,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- SIZE / AREA (convert to square meters)
    -- ═══════════════════════════════════════════════════════════════════════════
    CASE 
        WHEN p.living_area_unit = 'SM' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2))
        WHEN p.living_area_unit = 'SF' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2)) * 0.092903
        WHEN p.living_area_unit = 'AC' THEN TRY_CAST(p.living_area AS DECIMAL(18, 2)) * 4046.86
        ELSE TRY_CAST(p.living_area AS DECIMAL(18, 2))
    END                                     AS living_area,
    p.living_area_unit                      AS living_area_unit,
    
    CASE 
        WHEN p.building_area_unit = 'SM' THEN TRY_CAST(p.building_area AS DECIMAL(18, 2))
        WHEN p.building_area_unit = 'SF' THEN TRY_CAST(p.building_area AS DECIMAL(18, 2)) * 0.092903
        ELSE TRY_CAST(p.building_area AS DECIMAL(18, 2))
    END                                     AS building_area,
    p.building_area_unit                    AS building_area_unit,
    
    CASE 
        WHEN p.lot_size_unit = 'SM' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2))
        WHEN p.lot_size_unit = 'SF' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2)) * 0.092903
        WHEN p.lot_size_unit = 'AC' THEN TRY_CAST(p.lot_size AS DECIMAL(18, 2)) * 4046.86
        ELSE TRY_CAST(p.lot_size AS DECIMAL(18, 2))
    END                                     AS lot_size,
    p.lot_size_unit                         AS lot_size_unit,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- PRICING
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(p.list_selling_price_amount AS DECIMAL(18, 2)) AS list_price,
    TRY_CAST(p.list_price_usd AS DECIMAL(18, 2))            AS list_price_usd,
    NULLIF(TRIM(p.currency_code), '')       AS currency_code,
    NULLIF(TRIM(p.currency_name), '')       AS currency_name,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- DATES
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(NULLIF(TRIM(p.listed_date), '') AS DATE)      AS listing_date,
    TRY_CAST(NULLIF(TRIM(p.listed_date), '') AS TIMESTAMP) AS created_ts,
    TRY_CAST(NULLIF(TRIM(p.last_update_on), '') AS TIMESTAMP) AS modified_ts,
    TRY_CAST(TRY_CAST(p.days_on_market AS DOUBLE) AS INT)  AS days_on_market,
    TRY_CAST(NULLIF(TRIM(p.expires_on), '') AS DATE)       AS expiration_date,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- YEAR BUILT
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(TRY_CAST(p.year_built AS DOUBLE) AS INT)      AS year_built,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- FLAGS
    -- ═══════════════════════════════════════════════════════════════════════════
    CASE WHEN LOWER(p.is_off_market) = 'true' THEN TRUE ELSE FALSE END AS is_off_market,
    CASE WHEN LOWER(p.is_for_auction) = 'true' THEN TRUE ELSE FALSE END AS is_for_auction,
    CASE WHEN LOWER(p.is_new_construction) = 'true' THEN TRUE ELSE FALSE END AS is_new_construction,
    CASE WHEN LOWER(p.is_price_upon_request) = 'true' THEN TRUE ELSE FALSE END AS is_price_upon_request,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- FEATURES (parse from JSON for key RESO fields)
    -- ═══════════════════════════════════════════════════════════════════════════
    CASE WHEN p.features LIKE '%A/C%' OR p.features LIKE '%Air Condition%' THEN TRUE ELSE FALSE END AS has_ac,
    CASE WHEN p.features LIKE '%Pool%' THEN TRUE ELSE FALSE END AS has_pool,
    CASE WHEN p.features LIKE '%Fireplace%' THEN TRUE ELSE FALSE END AS has_fireplace,
    CASE WHEN p.features LIKE '%Garage%' THEN TRUE ELSE FALSE END AS has_garage,
    CASE WHEN p.features LIKE '%Security%' THEN TRUE ELSE FALSE END AS has_security,
    
    -- Raw features JSON for detailed parsing if needed
    p.features                              AS features_json,
    p.remarks                               AS remarks_json,
    p.additional_details                    AS additional_details_json,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- REMARKS (Parse from JSON to get PublicRemarks)
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Extract first remark text from remarks JSON array
    COALESCE(
        GET_JSON_OBJECT(
            GET_JSON_OBJECT(p.remarks, '$[0]'),
            '$.remark'
        ),
        NULLIF(TRIM(p.property_name), '')
    )                                       AS public_remarks,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- URLS
    -- ═══════════════════════════════════════════════════════════════════════════
    NULLIF(TRIM(p.listing_url), '')         AS listing_url,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- AGENT / OFFICE (From Bronze)
    -- ═══════════════════════════════════════════════════════════════════════════
    NULLIF(TRIM(p.agent_id), '')            AS agent_id,
    NULLIF(TRIM(p.agent_first_name), '')    AS agent_first_name,
    NULLIF(TRIM(p.agent_last_name), '')     AS agent_last_name,
    NULLIF(TRIM(p.agent_email), '')         AS agent_email,
    NULLIF(TRIM(p.agent_vanity_email), '')  AS agent_vanity_email,
    NULLIF(TRIM(p.agent_photo_url), '')     AS agent_photo_url,
    NULLIF(TRIM(p.company_id), '')          AS company_id,
    NULLIF(TRIM(p.company_name), '')        AS company_name,
    NULLIF(TRIM(p.company_code), '')        AS company_code,
    NULLIF(TRIM(p.agent_office_id), '')     AS agent_office_id,
    NULLIF(TRIM(p.agent_office_code), '')   AS agent_office_code,
    NULLIF(TRIM(p.listing_office_id), '')   AS listing_office_id,
    NULLIF(TRIM(p.listing_office_code), '') AS listing_office_code,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- DEDUPLICATION: keep one row per listing (prefer newer records)
    -- ═══════════════════════════════════════════════════════════════════════════
    ROW_NUMBER() OVER (
        PARTITION BY p.id 
        ORDER BY p.last_update_on DESC NULLS LAST, p.id
    ) AS rn

FROM dash_bronze.properties p
WHERE p.id IS NOT NULL AND p.id != ''
)
SELECT
    dash_id, dash_ref, dash_source, office_key,
    name, description, status, status_description, sale_rent,
    property_type, property_subtype, property_type_code, property_subtype_code, style_code, style_description,
    bedrooms, bathrooms, half_bath,
    country, country_name, state, state_name, city, district, post_code, street,
    coordinates, latitude, longitude,
    living_area, living_area_unit, building_area, building_area_unit, lot_size, lot_size_unit,
    list_price, list_price_usd, currency_code, currency_name,
    listing_date, created_ts, modified_ts, days_on_market, expiration_date,
    year_built,
    is_off_market, is_for_auction, is_new_construction, is_price_upon_request,
    has_ac, has_pool, has_fireplace, has_garage, has_security,
    features_json, remarks_json, additional_details_json, public_remarks,
    listing_url,
    agent_id, agent_first_name, agent_last_name, agent_email, agent_vanity_email, agent_photo_url,
    company_id, company_name, company_code,
    agent_office_id, agent_office_code, listing_office_id, listing_office_code,
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('dash_silver_batch_', CURRENT_DATE()) AS etl_batch_id
FROM ranked
WHERE rn = 1
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
    SELECT dash_id, dash_ref, name, status, property_type, 
           bedrooms, bathrooms, city, country, list_price, office_key
    FROM dash_silver.property
    LIMIT 5
""").show(truncate=False)

# Show column count
cols = spark.table("dash_silver.property").columns
print(f"\n📊 Dash Silver property columns: {len(cols)}")
