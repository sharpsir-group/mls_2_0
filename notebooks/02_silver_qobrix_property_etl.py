# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 – Bronze → Silver Property ETL
# MAGIC 
# MAGIC **Purpose:** Transforms raw Qobrix properties from bronze to normalized silver layer.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.properties`
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.property` with:
# MAGIC - Cleaned identifiers (qobrix_id, qobrix_ref)
# MAGIC - Normalized attributes (bedrooms, bathrooms, areas)
# MAGIC - Typed columns (INT, DECIMAL, TIMESTAMP)
# MAGIC - Location fields (country, city, street, coordinates)
# MAGIC - Pricing (list_selling_price_amount)
# MAGIC 
# MAGIC **Run After:** `00_full_refresh_qobrix_bronze.py`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("Using catalog:", catalog)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 – Check Bronze

# COMMAND ----------

try:
    bronze_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.properties").collect()[0]["c"]
    print(f"📊 Bronze properties: {bronze_count}")
    if bronze_count == 0:
        print("⚠️ Bronze empty, aborting silver ETL.")
except Exception as e:
    print(f"❌ Error reading bronze properties: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 – Create Silver Table `property_silver`

# COMMAND ----------

# First, let's see what columns are actually available in bronze
bronze_cols = set([c.lower() for c in spark.table("qobrix_bronze.properties").columns])
print(f"📋 Bronze table has {len(bronze_cols)} columns")
print(f"Sample columns: {sorted(bronze_cols)[:30]}")

# Build dynamic SQL based on available columns
def col_or_null(col_name, alias=None):
    """Return column reference if exists, else NULL"""
    alias = alias or col_name
    if col_name.lower() in bronze_cols:
        return f"p.{col_name} AS {alias}"
    else:
        return f"NULL AS {alias}"

transform_qobrix_to_silver_sql = f"""
CREATE OR REPLACE TABLE qobrix_silver.property AS
SELECT
    -- Identifiers
    {col_or_null('id', 'qobrix_id')},
    {col_or_null('ref', 'qobrix_ref')},
    {col_or_null('legacy_id', 'qobrix_legacy_id')},
    {col_or_null('source', 'qobrix_source')},

    -- Core attributes
    {col_or_null('name')},
    {col_or_null('description')},
    {col_or_null('status')},
    {col_or_null('sale_rent')},
    {col_or_null('property_type')},
    {col_or_null('property_subtype', 'property_subtype_id')},
    {col_or_null('construction_stage')},

    -- Bedrooms / bathrooms (cast via DOUBLE since bronze stores as "2.0" string)
    TRY_CAST(TRY_CAST(p.bedrooms AS DOUBLE) AS INT)   AS bedrooms,
    TRY_CAST(TRY_CAST(p.bathrooms AS DOUBLE) AS INT)  AS bathrooms,

    -- Location
    {col_or_null('country')},
    {col_or_null('state')},
    {col_or_null('city')},
    {col_or_null('municipality')},
    {col_or_null('post_code')},
    {col_or_null('street')},
    {col_or_null('coordinates')},

    -- Size / area
    TRY_CAST(p.internal_area_amount       AS DECIMAL(18, 2)) AS internal_area_amount,
    TRY_CAST(p.covered_area_amount        AS DECIMAL(18, 2)) AS covered_area_amount,
    TRY_CAST(p.covered_verandas_amount    AS DECIMAL(18, 2)) AS covered_verandas_amount,
    TRY_CAST(p.uncovered_verandas_amount  AS DECIMAL(18, 2)) AS uncovered_verandas_amount,
    TRY_CAST(p.plot_area_amount           AS DECIMAL(18, 2)) AS plot_area_amount,
    TRY_CAST(p.roof_garden_area_amount    AS DECIMAL(18, 2)) AS roof_garden_area_amount,

    -- Pricing
    TRY_CAST(p.list_selling_price_amount  AS DECIMAL(18, 2)) AS list_selling_price_amount,
    TRY_CAST(p.price_per_square           AS DECIMAL(18, 2)) AS price_per_square,
    {col_or_null('website_status')},
    {col_or_null('listing_date')},

    -- Timestamps
    TRY_CAST(p.created  AS TIMESTAMP) AS created_ts,
    TRY_CAST(p.modified AS TIMESTAMP) AS modified_ts,

    -- Relationships
    {col_or_null('seller', 'seller_id')},
    {col_or_null('project', 'project_id')},

    -- A few key boolean flags (extend later as needed)
    TRY_CAST(p.air_condition  AS BOOLEAN) AS air_condition,
    TRY_CAST(p.storage_space  AS BOOLEAN) AS storage_space,
    TRY_CAST(p.beach_front    AS BOOLEAN) AS beach_front,

    -- ETL metadata
    CURRENT_TIMESTAMP()              AS etl_timestamp,
    CONCAT('silver_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.properties p
"""

print("📊 Creating silver table from bronze...")
spark.sql(transform_qobrix_to_silver_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.property").collect()[0]["c"]
print(f"✅ Silver property records: {silver_count}")



