# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Dash Bronze -> Silver Media ETL
# MAGIC 
# MAGIC **Purpose:** Transforms raw Dash media from bronze to normalized silver layer.
# MAGIC 
# MAGIC **Input:** `mls2.dash_bronze.media`
# MAGIC 
# MAGIC **Output:** `mls2.dash_silver.media` with:
# MAGIC - Media URLs and metadata
# MAGIC - Property linkage
# MAGIC - Media categories and types
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
    media_count = spark.sql("SELECT COUNT(*) AS c FROM dash_bronze.media").collect()[0]["c"]
    print(f"📊 Dash Bronze media: {media_count}")
    if media_count == 0:
        print("⚠️ Dash Bronze media empty, creating empty silver table.")
except Exception as e:
    print(f"❌ Error reading dash bronze media: {e}")
    media_count = 0

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Create Silver Table `dash_silver.media`

# COMMAND ----------

# Ensure dash_silver schema exists
spark.sql("CREATE SCHEMA IF NOT EXISTS dash_silver")

if media_count > 0:
    transform_dash_to_silver_media_sql = """
    CREATE OR REPLACE TABLE dash_silver.media AS
    SELECT DISTINCT
        CAST(m.id AS STRING) AS media_id,
        CAST(m.property_id AS STRING) AS property_id,
        
        -- URL (Dash provides full URLs)
        NULLIF(TRIM(m.url), '') AS media_url,
        
        -- Media type classification
        CASE 
            WHEN LOWER(COALESCE(m.format_description, '')) LIKE '%image%' OR m.format_code = 'IM' THEN 'image'
            WHEN LOWER(COALESCE(m.format_description, '')) LIKE '%video%' OR m.format_code = 'VI' THEN 'video'
            WHEN LOWER(COALESCE(m.format_description, '')) LIKE '%pdf%' OR m.format_code = 'DO' THEN 'document'
            WHEN LOWER(COALESCE(m.format_description, '')) LIKE '%audio%' THEN 'audio'
            ELSE 'other'
        END AS media_category,
        
        -- MIME type (infer from format)
        CASE 
            WHEN m.format_code = 'IM' THEN 'image/jpeg'
            WHEN m.format_code = 'VI' THEN 'video/mp4'
            WHEN m.format_code = 'DO' THEN 'application/pdf'
            ELSE ''
        END AS mime_type,
        
        -- File info
        NULLIF(TRIM(m.caption), '') AS file_name,
        NULL AS file_size_bytes,  -- Dash doesn't provide file size
        
        -- Order/sequence
        TRY_CAST(m.sequence_number AS INT) AS display_order,
        
        -- Description/caption
        COALESCE(NULLIF(TRIM(m.description), ''), NULLIF(TRIM(m.caption), '')) AS description,
        NULLIF(TRIM(m.caption), '') AS title,
        
        -- Image dimensions (NEW - from bronze)
        TRY_CAST(m.width AS INT) AS image_width,
        TRY_CAST(m.height AS INT) AS image_height,
        CASE WHEN LOWER(COALESCE(m.is_landscape, '')) = 'true' THEN TRUE ELSE FALSE END AS is_landscape,
        CASE WHEN LOWER(COALESCE(m.is_distributable, '')) = 'true' THEN TRUE ELSE FALSE END AS is_distributable,
        
        -- Media category from Dash
        NULLIF(TRIM(m.category), '') AS dash_category,
        
        -- Media tags (JSON string)
        m.media_tags AS media_tags_json,
        
        -- Primary flag (isDefault)
        CASE 
            WHEN LOWER(COALESCE(m.is_default, '')) = 'true' THEN TRUE
            ELSE FALSE
        END AS is_primary,
        
        -- Timestamps (Dash doesn't provide these, use current time)
        CURRENT_TIMESTAMP() AS created_ts,
        CURRENT_TIMESTAMP() AS modified_ts,
        
        -- ETL metadata
        CURRENT_TIMESTAMP() AS etl_timestamp,
        CONCAT('dash_silver_media_batch_', CURRENT_DATE()) AS etl_batch_id

    FROM dash_bronze.media m
    WHERE m.id IS NOT NULL AND m.id != ''
      AND m.property_id IS NOT NULL AND m.property_id != ''
    """
    
    print("📊 Creating Dash silver media table from bronze...")
    spark.sql(transform_dash_to_silver_media_sql)
    
    silver_media_count = spark.sql("SELECT COUNT(*) AS c FROM dash_silver.media").collect()[0]["c"]
    print(f"✅ Dash Silver media records: {silver_media_count}")
else:
    print("📊 Creating empty RESO Media table (no source data)...")
    spark.sql("""
        CREATE OR REPLACE TABLE dash_silver.media (
            media_id STRING,
            property_id STRING,
            media_url STRING,
            media_category STRING,
            mime_type STRING,
            file_name STRING,
            file_size_bytes BIGINT,
            display_order INT,
            description STRING,
            title STRING,
            image_width INT,
            image_height INT,
            is_landscape BOOLEAN,
            is_distributable BOOLEAN,
            dash_category STRING,
            media_tags_json STRING,
            is_primary BOOLEAN,
            created_ts TIMESTAMP,
            modified_ts TIMESTAMP,
            etl_timestamp TIMESTAMP,
            etl_batch_id STRING
        )
    """)
    print("✅ Empty Dash Silver media table created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if media_count > 0:
    print("\n📋 Sample Dash Silver Media:")
    spark.sql("""
        SELECT media_id, property_id, media_category, media_url, display_order, is_primary
        FROM dash_silver.media
        ORDER BY property_id, display_order
        LIMIT 10
    """).show(truncate=False)

