# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Silver -> Gold RESO Media ETL
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant Media resource from normalized Qobrix media data.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.media`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.media` with RESO standard fields:
# MAGIC - `MediaKey` - Unique identifier (QOBRIX_MEDIA_{id})
# MAGIC - `ResourceRecordKey` - Link to Property (ListingKey)
# MAGIC - `ResourceName` - "Property" (resource type)
# MAGIC - `MediaCategory` - Photo, Document, FloorPlan, etc.
# MAGIC - `MediaURL` - URL to the media file
# MAGIC - `MediaType` - MIME type (image/jpeg, application/pdf, etc.)
# MAGIC - `Order` - Display order
# MAGIC - `ShortDescription`, `LongDescription`
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Media+Resource
# MAGIC 
# MAGIC **Run After:** 02c_silver_qobrix_media_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS reso_gold")

# Widget for OriginatingSystemOfficeKey (passed via job parameters)
dbutils.widgets.text("ORIGINATING_SYSTEM_OFFICE_KEY", "CSIR")
originating_office_key = os.getenv("ORIGINATING_SYSTEM_OFFICE_KEY") or dbutils.widgets.get("ORIGINATING_SYSTEM_OFFICE_KEY") or "CSIR"

print("Using catalog:", catalog)
print("OriginatingSystemOfficeKey:", originating_office_key)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create RESO Media from Silver Media

# COMMAND ----------

# Check if silver media table exists and has data
try:
    media_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.media").collect()[0]["c"]
    print(f"📊 Silver media records: {media_count}")
    
    if media_count == 0:
        print("⚠️ No media records in silver layer. Creating empty table.")
except Exception as e:
    print(f"⚠️ Silver media table not found: {e}")
    media_count = 0

# COMMAND ----------

if media_count > 0:
    create_media_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.media AS
    
    SELECT
        -- RESO core identifiers
        CONCAT('QOBRIX_MEDIA_', m.media_id)              AS MediaKey,
        CONCAT('QOBRIX_', m.property_id)                 AS ResourceRecordKey,
        'Property'                                       AS ResourceName,
        
        -- Media category mapping (already categorized in silver)
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
        
        -- Image dimensions (not available)
        CAST(NULL AS INT)                                AS ImageWidth,
        CAST(NULL AS INT)                                AS ImageHeight,
        m.file_size_bytes                                AS ImageSizeBytes,
        
        -- Primary flag (RESO extension)
        m.is_primary                                     AS X_IsPrimary,
        
        -- Qobrix extension fields (X_ prefix)
        m.media_id                                       AS X_QobrixMediaId,
        m.property_id                                    AS X_QobrixPropertyId,
        m.qobrix_category                                AS X_QobrixMediaCategory,
        CAST(NULL AS STRING)                             AS X_QobrixFileId,
        CAST(NULL AS STRING)                             AS X_QobrixThumbnailUrl,
        CAST(NULL AS STRING)                             AS X_QobrixFilesystem,
        CAST(NULL AS STRING)                             AS X_QobrixCategoryId,
        CAST(m.created_ts AS STRING)                     AS X_QobrixCreated,
        CAST(m.modified_ts AS STRING)                    AS X_QobrixModified,
        
        -- Multi-tenant access control: Data source office
        -- CSIR = Cyprus SIR (Qobrix data source)
        -- HSIR = Hungary SIR (JSON loader data source)
        '{originating_office_key}'                       AS OriginatingSystemOfficeKey,
        
        -- ETL metadata
        CURRENT_TIMESTAMP()                              AS etl_timestamp,
        CONCAT('media_batch_', CURRENT_DATE())           AS etl_batch_id
    
    FROM qobrix_silver.media m
    """
    
    print("📊 Creating gold RESO Media table...")
    spark.sql(create_media_sql)
else:
    # Create empty table with correct schema
    print("📊 Creating empty RESO Media table (no source data)...")
    spark.sql("""
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
        etl_timestamp TIMESTAMP,
        etl_batch_id STRING
    )
    """)

gold_media_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.media").collect()[0]["c"]
print(f"✅ Gold RESO Media records: {gold_media_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if gold_media_count > 0:
    # Show sample data
    print("\n📋 Sample RESO Media:")
    spark.sql("""
        SELECT MediaKey, ResourceRecordKey, MediaCategory, MediaType, ShortDescription
        FROM reso_gold.media
        LIMIT 10
    """).show(truncate=False)
    
    # Count by category
    print("\n📊 Media by Category:")
    spark.sql("""
        SELECT MediaCategory, COUNT(*) as count
        FROM reso_gold.media
        GROUP BY MediaCategory
        ORDER BY count DESC
    """).show()
else:
    print("\n⚠️ No media records to display")

