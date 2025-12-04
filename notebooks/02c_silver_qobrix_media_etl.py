# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 - Bronze → Silver Media ETL
# MAGIC 
# MAGIC **Purpose:** Normalizes and cleans property media data from bronze layer.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.property_media`
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.media` with normalized fields:
# MAGIC - Cleaned URLs and file paths
# MAGIC - Normalized media types
# MAGIC - Order/sequence handling
# MAGIC - Type casting and null handling
# MAGIC 
# MAGIC **Run After:** `00_full_refresh_qobrix_bronze.py`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS qobrix_silver")

print("Using catalog:", catalog)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Bronze Media to Silver

# COMMAND ----------

# Check source table
try:
    media_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.property_media").collect()[0]["c"]
    print(f"📊 Bronze property_media: {media_count}")
except:
    media_count = 0
    print("⚠️ Bronze property_media table not found")

# COMMAND ----------

transform_sql = """
CREATE OR REPLACE TABLE qobrix_silver.media AS

SELECT
    CAST(m.id AS STRING) AS media_id,
    CAST(m.property_id AS STRING) AS property_id,
    
    -- URL (cleaned)
    NULLIF(TRIM(m.file_href), '') AS media_url,
    
    -- Media type classification
    CASE 
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%image%' THEN 'image'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%video%' THEN 'video'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%pdf%' THEN 'document'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%audio%' THEN 'audio'
        ELSE 'other'
    END AS media_category,
    
    -- MIME type (cleaned)
    NULLIF(TRIM(LOWER(m.file_mime_type)), '') AS mime_type,
    
    -- File info (use file_filename, file_filesize from bronze)
    NULLIF(TRIM(m.file_filename), '') AS file_name,
    TRY_CAST(m.file_filesize AS BIGINT) AS file_size_bytes,
    
    -- Order/sequence (use display_order from bronze)
    TRY_CAST(m.display_order AS INT) AS display_order,
    
    -- Description/caption (may not exist in bronze)
    CAST(NULL AS STRING) AS description,
    CAST(NULL AS STRING) AS title,
    
    -- Media category from Qobrix (use media_category or category_name)
    COALESCE(NULLIF(TRIM(m.media_category), ''), NULLIF(TRIM(m.category_name), '')) AS qobrix_category,
    
    -- Primary flag (may not exist in bronze)
    FALSE AS is_primary,
    
    -- Timestamps
    TRY_CAST(m.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(m.modified AS TIMESTAMP) AS modified_ts,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_media_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.property_media m
WHERE m.id IS NOT NULL AND m.id != ''
"""

print("📊 Creating silver media table...")
spark.sql(transform_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.media").collect()[0]["c"]
print(f"✅ Silver media records: {silver_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n📋 Silver Media Summary by Category:")
spark.sql("""
    SELECT 
        media_category,
        COUNT(*) as count,
        COUNT(DISTINCT property_id) as properties
    FROM qobrix_silver.media
    GROUP BY media_category
    ORDER BY count DESC
""").show()

print("\n📋 Sample Silver Media:")
spark.sql("""
    SELECT media_id, property_id, media_category, mime_type, display_order, is_primary
    FROM qobrix_silver.media
    LIMIT 10
""").show(truncate=False)

