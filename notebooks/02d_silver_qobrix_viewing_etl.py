# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 - Bronze → Silver Viewing ETL
# MAGIC 
# MAGIC **Purpose:** Normalizes and cleans property viewing/appointment data from bronze layer.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.property_viewings`
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.viewing` with normalized fields:
# MAGIC - Cleaned date/time handling
# MAGIC - Normalized status values
# MAGIC - Assessment/feedback normalization
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
# MAGIC ## Transform Bronze Viewings to Silver

# COMMAND ----------

# Check source table
try:
    viewings_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.property_viewings").collect()[0]["c"]
    print(f"📊 Bronze property_viewings: {viewings_count}")
except:
    viewings_count = 0
    print("⚠️ Bronze property_viewings table not found")

# COMMAND ----------

transform_sql = """
CREATE OR REPLACE TABLE qobrix_silver.viewing AS

SELECT
    CAST(v.id AS STRING) AS viewing_id,
    CAST(v.property_id AS STRING) AS property_id,
    
    -- Participants (may not exist in bronze, use viewing_id as reference)
    CAST(v.viewing_id AS STRING) AS viewing_ref,
    CAST(NULL AS STRING) AS contact_id,
    CAST(NULL AS STRING) AS agent_id,
    CAST(v.created_by AS STRING) AS user_id,
    
    -- Scheduling (use created as viewing date)
    TRY_CAST(v.created AS DATE) AS viewing_date,
    CAST(NULL AS STRING) AS viewing_time,
    CAST(NULL AS INT) AS duration_minutes,
    
    -- Status (infer from trashed and viewing_outcome)
    CASE 
        WHEN LOWER(COALESCE(v.trashed, '')) = 'true' THEN 'cancelled'
        WHEN v.viewing_outcome IS NOT NULL AND v.viewing_outcome != '' THEN 'completed'
        ELSE 'scheduled'
    END AS status,
    
    -- Assessment/Feedback (from bronze columns)
    NULLIF(TRIM(v.price_assessment), '') AS assessment_price,
    NULLIF(TRIM(v.location_assessment), '') AS assessment_location,
    NULLIF(TRIM(v.exterior_appeal_assessment), '') AS assessment_condition,
    NULLIF(TRIM(v.views_assessment), '') AS assessment_overall,
    NULLIF(TRIM(v.further_feedback), '') AS notes,
    NULLIF(TRIM(v.viewing_outcome), '') AS feedback,
    
    -- Interest level (not available in bronze)
    CAST(NULL AS STRING) AS interest_level,
    
    -- Timestamps
    TRY_CAST(v.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(v.modified AS TIMESTAMP) AS modified_ts,
    NULLIF(TRIM(v.created_by), '') AS created_by,
    NULLIF(TRIM(v.modified_by), '') AS modified_by,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_viewing_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.property_viewings v
WHERE v.id IS NOT NULL AND v.id != ''
"""

print("📊 Creating silver viewing table...")
spark.sql(transform_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.viewing").collect()[0]["c"]
print(f"✅ Silver viewing records: {silver_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n📋 Silver Viewing Summary by Status:")
spark.sql("""
    SELECT 
        status,
        COUNT(*) as count
    FROM qobrix_silver.viewing
    GROUP BY status
    ORDER BY count DESC
""").show()

print("\n📋 Sample Silver Viewings:")
spark.sql("""
    SELECT viewing_id, property_id, contact_id, viewing_date, status, interest_level
    FROM qobrix_silver.viewing
    LIMIT 10
""").show(truncate=False)

