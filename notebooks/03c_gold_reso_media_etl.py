# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Silver -> Gold RESO Media ETL (Unified)
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant Media resource from multiple data sources.
# MAGIC 
# MAGIC **Input Sources:**
# MAGIC - `mls2.qobrix_silver.media` - Cyprus SIR (Qobrix) media
# MAGIC - `mls2.dash_silver.media` - Hungary SIR (Dash/Sotheby's) media
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.media` (UNION of all sources) with RESO standard fields:
# MAGIC - `MediaKey` - Unique identifier
# MAGIC - `ResourceRecordKey` - Link to Property (ListingKey)
# MAGIC - `ResourceName` - "Property" (resource type)
# MAGIC - `MediaCategory` - Photo, Document, FloorPlan, etc.
# MAGIC - `MediaURL` - URL to the media file
# MAGIC - `MediaType` - MIME type (image/jpeg, application/pdf, etc.)
# MAGIC - `Order` - Display order
# MAGIC 
# MAGIC **Multi-Tenant Access Control:**
# MAGIC - `OriginatingSystemOfficeKey` = SHARPSIR-CY-001 for Qobrix (Cyprus)
# MAGIC - `OriginatingSystemOfficeKey` = SHARPSIR-HU-001 for Dash (Hungary)
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Media+Resource
# MAGIC 
# MAGIC **Run After:** 02c_silver_qobrix_media_etl.py, 01_dash_silver_media_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS reso_gold")

# Widget for Qobrix OriginatingSystemOfficeKey (Cyprus)
dbutils.widgets.text("QOBRIX_OFFICE_KEY", "SHARPSIR-CY-001")
qobrix_office_key = os.getenv("SRC_1_OFFICE_KEY") or dbutils.widgets.get("QOBRIX_OFFICE_KEY") or "SHARPSIR-CY-001"

# Widget for Dash OriginatingSystemOfficeKey (Hungary)
dbutils.widgets.text("DASH_HU_OFFICE_KEY", "SHARPSIR-HU-001")
dash_hu_office_key = os.getenv("SRC_2_OFFICE_KEY") or dbutils.widgets.get("DASH_HU_OFFICE_KEY") or "SHARPSIR-HU-001"

# Widget for Dash API OriginatingSystemOfficeKey (Kazakhstan)
dbutils.widgets.text("DASH_KZ_OFFICE_KEY", "SHARPSIR-KZ-001")
dash_kz_office_key = os.getenv("SRC_3_OFFICE_KEY") or dbutils.widgets.get("DASH_KZ_OFFICE_KEY") or "SHARPSIR-KZ-001"

print("Using catalog:", catalog)
print("Qobrix OriginatingSystemOfficeKey:", qobrix_office_key)
print("Dash OriginatingSystemOfficeKey (HU):", dash_hu_office_key)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Available Data Sources

# COMMAND ----------

# Check if silver media tables exist and have data
qobrix_available = False
dash_available = False

try:
    qobrix_media_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.media").collect()[0]["c"]
    print(f"📊 Qobrix Silver media records: {qobrix_media_count}")
    qobrix_available = qobrix_media_count > 0
except Exception as e:
    print(f"⚠️ Qobrix Silver media not available: {e}")
    qobrix_media_count = 0

try:
    dash_media_count = spark.sql("SELECT COUNT(*) AS c FROM dash_silver.media").collect()[0]["c"]
    print(f"📊 Dash Silver media records: {dash_media_count}")
    dash_available = dash_media_count > 0
except Exception as e:
    print(f"⚠️ Dash Silver media not available: {e}")
    dash_media_count = 0

total_media = qobrix_media_count + dash_media_count
print(f"\n📊 Total media records to process: {total_media}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create RESO Media from Silver Media Sources

# COMMAND ----------

# Qobrix media transform SQL
qobrix_select_sql = f"""
SELECT
    -- RESO core identifiers
    CONCAT('QOBRIX_MEDIA_', m.media_id)              AS MediaKey,
    CONCAT('QOBRIX_', m.property_id)                 AS ResourceRecordKey,
    'Property'                                       AS ResourceName,
    
    -- Media category mapping
    CASE m.media_category
        WHEN 'image'    THEN 'Photo'
        WHEN 'video'    THEN 'Video'
        WHEN 'document' THEN 'Document'
        WHEN 'audio'    THEN 'Audio'
        ELSE 'Photo'
    END                                              AS MediaCategory,
    
    -- URL
    COALESCE(m.media_url, '')                        AS MediaURL,
    
    -- Media type (MIME type)
    COALESCE(m.mime_type, 'application/octet-stream') AS MediaType,
    
    -- Order/sequence
    COALESCE(m.display_order, 0)                     AS `Order`,
    
    -- Descriptions
    COALESCE(m.file_name, m.title, '')               AS ShortDescription,
    COALESCE(m.description, m.qobrix_category, '')   AS LongDescription,
    
    -- Image dimensions
    CAST(NULL AS INT)                                AS ImageWidth,
    CAST(NULL AS INT)                                AS ImageHeight,
    m.file_size_bytes                                AS ImageSizeBytes,
    
    -- Primary flag (RESO extension)
    m.is_primary                                     AS X_IsPrimary,
    
    -- Extension fields
    m.media_id                                       AS X_QobrixMediaId,
    m.property_id                                    AS X_QobrixPropertyId,
    m.qobrix_category                                AS X_QobrixMediaCategory,
    CAST(NULL AS STRING)                             AS X_QobrixFileId,
    CAST(NULL AS STRING)                             AS X_QobrixThumbnailUrl,
    CAST(NULL AS STRING)                             AS X_QobrixFilesystem,
    CAST(NULL AS STRING)                             AS X_QobrixCategoryId,
    CAST(m.created_ts AS STRING)                     AS X_QobrixCreated,
    CAST(m.modified_ts AS STRING)                    AS X_QobrixModified,
    
    -- Multi-tenant access control
    '{qobrix_office_key}'                            AS OriginatingSystemOfficeKey,
    'qobrix'                                         AS X_DataSource,
    
    -- ETL metadata
    CURRENT_TIMESTAMP()                              AS etl_timestamp,
    CONCAT('media_batch_', CURRENT_DATE())           AS etl_batch_id

FROM qobrix_silver.media m
"""

# Dash media transform SQL - Enhanced with image dimensions
dash_select_sql = f"""
SELECT
    -- RESO core identifiers
    CONCAT('DASH_MEDIA_', m.media_id)                AS MediaKey,
    CONCAT('DASH_', m.property_id)                   AS ResourceRecordKey,
    'Property'                                       AS ResourceName,
    
    -- Media category mapping
    CASE m.media_category
        WHEN 'image'    THEN 'Photo'
        WHEN 'video'    THEN 'Video'
        WHEN 'document' THEN 'Document'
        WHEN 'audio'    THEN 'Audio'
        ELSE 'Photo'
    END                                              AS MediaCategory,
    
    -- URL (Dash provides full URLs)
    COALESCE(m.media_url, '')                        AS MediaURL,
    
    -- Media type (MIME type)
    COALESCE(m.mime_type, 'image/jpeg')              AS MediaType,
    
    -- Order/sequence
    COALESCE(m.display_order, 0)                     AS `Order`,
    
    -- Descriptions
    COALESCE(m.file_name, m.title, '')               AS ShortDescription,
    COALESCE(m.description, m.dash_category, '')     AS LongDescription,
    
    -- Image dimensions (NOW available from Dash bronze)
    m.image_width                                    AS ImageWidth,
    m.image_height                                   AS ImageHeight,
    -- Dash silver may not always expose file_size_bytes reliably across runtimes; keep NULL
    CAST(NULL AS BIGINT)                             AS ImageSizeBytes,
    
    -- Primary flag
    m.is_primary                                     AS X_IsPrimary,
    
    -- Extension fields (using X_Qobrix* for schema compatibility)
    m.media_id                                       AS X_QobrixMediaId,
    m.property_id                                    AS X_QobrixPropertyId,
    m.dash_category                                  AS X_QobrixMediaCategory,
    CAST(NULL AS STRING)                             AS X_QobrixFileId,
    CAST(NULL AS STRING)                             AS X_QobrixThumbnailUrl,
    CAST(NULL AS STRING)                             AS X_QobrixFilesystem,
    CAST(NULL AS STRING)                             AS X_QobrixCategoryId,
    CAST(m.created_ts AS STRING)                     AS X_QobrixCreated,
    CAST(m.modified_ts AS STRING)                    AS X_QobrixModified,
    
    -- Multi-tenant access control
    '{dash_hu_office_key}'                           AS OriginatingSystemOfficeKey,
    'dash_sothebys'                                  AS X_DataSource,
    
    -- ETL metadata
    CURRENT_TIMESTAMP()                              AS etl_timestamp,
    CONCAT('media_batch_', CURRENT_DATE())           AS etl_batch_id

FROM dash_silver.media m
"""

# COMMAND ----------

# Build the UNION query based on available sources
print("📊 Building unified gold media table...")

if qobrix_available and dash_available:
    # Both sources available - UNION ALL
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.media AS
    {qobrix_select_sql}
    UNION ALL
    {dash_select_sql}
    """
    print("🔗 Using UNION ALL: Qobrix + Dash media")
elif qobrix_available:
    # Only Qobrix
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.media AS
    {qobrix_select_sql}
    """
    print("📦 Using Qobrix media only")
elif dash_available:
    # Only Dash
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.media AS
    {dash_select_sql}
    """
    print("📦 Using Dash media only")
else:
    # No data - create empty table
    print("📊 Creating empty RESO Media table (no source data)...")
    full_sql = """
    CREATE OR REPLACE TABLE reso_gold.media (
        MediaKey STRING,
        ResourceRecordKey STRING,
        ResourceName STRING,
        MediaCategory STRING,
        MediaURL STRING,
        MediaType STRING,
        `Order` INT,
        ShortDescription STRING,
        LongDescription STRING,
        ImageWidth INT,
        ImageHeight INT,
        ImageSizeBytes BIGINT,
        X_IsPrimary BOOLEAN,
        X_QobrixMediaId STRING,
        X_QobrixPropertyId STRING,
        X_QobrixMediaCategory STRING,
        X_QobrixFileId STRING,
        X_QobrixThumbnailUrl STRING,
        X_QobrixFilesystem STRING,
        X_QobrixCategoryId STRING,
        X_QobrixCreated STRING,
        X_QobrixModified STRING,
        OriginatingSystemOfficeKey STRING,
        X_DataSource STRING,
        etl_timestamp TIMESTAMP,
        etl_batch_id STRING
    )
    """

spark.sql(full_sql)

# COMMAND ----------

# Verify results
gold_media_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.media").collect()[0]["c"]
print(f"✅ Gold RESO Media records: {gold_media_count}")

# Show data source breakdown
print("\n📊 Media records by data source:")
spark.sql("""
    SELECT X_DataSource, OriginatingSystemOfficeKey, COUNT(*) as count
    FROM reso_gold.media
    GROUP BY X_DataSource, OriginatingSystemOfficeKey
    ORDER BY X_DataSource
""").show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if gold_media_count > 0:
    # Show sample data
    print("\n📋 Sample RESO Media:")
    spark.sql("""
        SELECT MediaKey, ResourceRecordKey, MediaCategory, MediaType, 
               ShortDescription, OriginatingSystemOfficeKey, X_DataSource
        FROM reso_gold.media
        LIMIT 10
    """).show(truncate=False)
    
    # Count by category
    print("\n📊 Media by Category:")
    spark.sql("""
        SELECT MediaCategory, X_DataSource, COUNT(*) as count
        FROM reso_gold.media
        GROUP BY MediaCategory, X_DataSource
        ORDER BY count DESC
    """).show()
else:
    print("\n⚠️ No media records to display")
