# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 - CDC Silver Property ETL (Incremental)
# MAGIC 
# MAGIC **Purpose:** Transforms changed Qobrix properties from bronze to silver using MERGE.
# MAGIC 
# MAGIC **How it works:**
# MAGIC 1. Identifies properties changed since last silver ETL (using `_cdc_updated_at`)
# MAGIC 2. MERGEs only changed records into silver (insert/update)
# MAGIC 3. Much faster than full refresh for incremental updates
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.properties` (with `_cdc_updated_at` column)
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.property`
# MAGIC 
# MAGIC **When to use:**
# MAGIC - After CDC bronze sync: Run this notebook
# MAGIC - After full refresh bronze: Run `02_silver_qobrix_property_etl.py` (full refresh)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

from datetime import datetime, timedelta

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("=" * 80)
print("🔄 CDC MODE - Silver Property ETL")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Changed Records

# COMMAND ----------

# Check if silver table exists and get last ETL timestamp
try:
    last_etl = spark.sql("""
        SELECT MAX(etl_timestamp) as last_etl 
        FROM qobrix_silver.property
    """).collect()[0]["last_etl"]
    
    if last_etl:
        print(f"📊 Last silver ETL: {last_etl}")
    else:
        last_etl = datetime(2000, 1, 1)
        print("⚠️ Silver table is empty, will process all records")
except:
    last_etl = datetime(2000, 1, 1)
    print("⚠️ Silver table doesn't exist, will create from scratch")

# Count changed records in bronze
try:
    # Check if _cdc_updated_at exists
    bronze_cols = [c.lower() for c in spark.table("qobrix_bronze.properties").columns]
    
    if "_cdc_updated_at" in bronze_cols:
        changed_count = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM qobrix_bronze.properties 
            WHERE _cdc_updated_at > '{last_etl}'
        """).collect()[0]["cnt"]
        print(f"📊 Changed properties since last ETL: {changed_count}")
        use_cdc = changed_count > 0
    else:
        print("⚠️ No _cdc_updated_at column in bronze, running full refresh")
        use_cdc = False
        changed_count = spark.sql("SELECT COUNT(*) as cnt FROM qobrix_bronze.properties").collect()[0]["cnt"]
        
except Exception as e:
    print(f"❌ Error checking bronze: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## MERGE Changed Records

# COMMAND ----------

# First, let's see what columns are actually available in bronze
bronze_cols_set = set([c.lower() for c in spark.table("qobrix_bronze.properties").columns])

def col_or_null(col_name, alias=None):
    """Return column reference if exists, else NULL"""
    alias = alias or col_name
    if col_name.lower() in bronze_cols_set:
        return f"p.{col_name} AS {alias}"
    else:
        return f"NULL AS {alias}"

# Define the transformation SELECT
transform_select = f"""
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

    -- Bedrooms / bathrooms
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

    -- Boolean flags
    TRY_CAST(p.air_condition  AS BOOLEAN) AS air_condition,
    TRY_CAST(p.storage_space  AS BOOLEAN) AS storage_space,
    TRY_CAST(p.beach_front    AS BOOLEAN) AS beach_front,

    -- ETL metadata
    CURRENT_TIMESTAMP()              AS etl_timestamp,
    CONCAT('silver_cdc_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.properties p
"""

# Check if silver table exists
tables = [t.name for t in spark.catalog.listTables("qobrix_silver")]

if "property" not in tables:
    # First run - create table with full data
    print("📊 Creating silver.property table (first run)...")
    spark.sql(f"CREATE OR REPLACE TABLE qobrix_silver.property AS {transform_select}")
    
elif not use_cdc:
    # Full refresh mode
    print("📊 Running full refresh (no CDC data available)...")
    spark.sql(f"CREATE OR REPLACE TABLE qobrix_silver.property AS {transform_select}")
    
else:
    # CDC mode - MERGE only changed records
    print(f"📊 Merging {changed_count} changed records...")
    
    # Create temp view with only changed records
    cdc_filter = f"WHERE p._cdc_updated_at > '{last_etl}'"
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _cdc_silver_property AS
        {transform_select}
        {cdc_filter}
    """)
    
    # MERGE into silver
    merge_sql = """
        MERGE INTO qobrix_silver.property AS target
        USING _cdc_silver_property AS source
        ON target.qobrix_id = source.qobrix_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """
    
    spark.sql(merge_sql)
    print(f"✅ Merged {changed_count} records into silver.property")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.property").collect()[0]["c"]
print(f"\n📊 Silver property total records: {silver_count}")

# Show recent changes
print("\nRecent modifications:")
spark.sql("""
    SELECT qobrix_id, name, status, modified_ts, etl_timestamp
    FROM qobrix_silver.property
    ORDER BY etl_timestamp DESC
    LIMIT 5
""").show(truncate=False)

print("\n" + "=" * 80)
print("✅ CDC Silver Property ETL Complete")
print("=" * 80)

