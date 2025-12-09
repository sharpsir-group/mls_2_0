# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Bronze -> Silver Media ETL
# MAGIC 
# MAGIC **Purpose:** Normalizes and cleans property media data from bronze layer.
# MAGIC Includes both direct property media and project media linked to properties.
# MAGIC 
# MAGIC **Input:** 
# MAGIC - `mls2.qobrix_bronze.property_media` (direct property media)
# MAGIC - `mls2.qobrix_bronze.properties` (to link properties to projects)
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.media` with normalized fields:
# MAGIC - Cleaned URLs and file paths
# MAGIC - Normalized media types
# MAGIC - Order/sequence handling
# MAGIC - Type casting and null handling
# MAGIC - Includes project media linked to properties via property.project field
# MAGIC 
# MAGIC **Run After:** 00_full_refresh_qobrix_bronze.py

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

-- Part 1: Direct property media (property_media with property_id)
SELECT
    CAST(m.id AS STRING) AS media_id,
    CAST(m.property_id AS STRING) AS property_id,
    
    -- URL (cleaned) - use file_href (should be full URL or relative path from Qobrix)
    -- If relative, it will be handled in Gold ETL or API layer
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
    
    -- File info
    NULLIF(TRIM(m.file_filename), '') AS file_name,
    TRY_CAST(m.file_filesize AS BIGINT) AS file_size_bytes,
    
    -- Order/sequence
    TRY_CAST(m.display_order AS INT) AS display_order,
    
    -- Description/caption
    CAST(NULL AS STRING) AS description,
    CAST(NULL AS STRING) AS title,
    
    -- Media category from Qobrix
    COALESCE(NULLIF(TRIM(m.media_category), ''), NULLIF(TRIM(m.category_name), '')) AS qobrix_category,
    
    -- Primary flag
    FALSE AS is_primary,
    
    -- Timestamps
    TRY_CAST(m.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(m.modified AS TIMESTAMP) AS modified_ts,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_media_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.property_media m
WHERE m.id IS NOT NULL AND m.id != ''
  AND m.property_id IS NOT NULL AND m.property_id != ''
  -- Exclude project media (related_model='Projects') from direct property media
  AND (m.related_model IS NULL OR m.related_model = '' OR m.related_model != 'Projects')

UNION ALL

-- Part 2: Project media linked to properties (property_media with related_model='Projects')
SELECT
    CAST(m.id AS STRING) AS media_id,
    CAST(p.id AS STRING) AS property_id,  -- Link via property.project = project media related_id
    
    -- URL (cleaned) - same logic as Part 1
    NULLIF(TRIM(m.file_href), '') AS media_url,
    
    -- Media type classification
    CASE 
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%image%' THEN 'image'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%video%' THEN 'video'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%pdf%' THEN 'document'
        WHEN LOWER(COALESCE(m.file_mime_type, '')) LIKE '%audio%' THEN 'audio'
        ELSE 'other'
    END AS media_category,
    
    -- MIME type
    NULLIF(TRIM(LOWER(m.file_mime_type)), '') AS mime_type,
    
    -- File info
    NULLIF(TRIM(m.file_filename), '') AS file_name,
    TRY_CAST(m.file_filesize AS BIGINT) AS file_size_bytes,
    
    -- Order/sequence
    TRY_CAST(m.display_order AS INT) AS display_order,
    
    -- Description
    CAST(NULL AS STRING) AS description,
    CAST(NULL AS STRING) AS title,
    
    -- Media category from Qobrix
    COALESCE(NULLIF(TRIM(m.media_category), ''), NULLIF(TRIM(m.category_name), '')) AS qobrix_category,
    
    -- Primary flag
    FALSE AS is_primary,
    
    -- Timestamps
    TRY_CAST(m.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(m.modified AS TIMESTAMP) AS modified_ts,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_media_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.property_media m
INNER JOIN qobrix_bronze.properties p
    ON CAST(m.related_id AS STRING) = CAST(p.project AS STRING)
WHERE m.id IS NOT NULL AND m.id != ''
  AND m.related_model = 'Projects'
  AND m.related_id IS NOT NULL AND m.related_id != ''
  AND p.project IS NOT NULL AND p.project != ''
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

