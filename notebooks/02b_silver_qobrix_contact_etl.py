# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Bronze -> Silver Contact ETL
# MAGIC 
# MAGIC **Purpose:** Normalizes and cleans contact data from bronze layer.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.contacts`
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.contact` with normalized fields:
# MAGIC - Cleaned and validated contact information
# MAGIC - Normalized role/type values
# MAGIC - Company vs individual classification
# MAGIC - Type casting and null handling
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
# MAGIC ## Transform Bronze Contacts to Silver

# COMMAND ----------

# Check source table
try:
    contacts_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.contacts").collect()[0]["c"]
    print(f"📊 Bronze contacts: {contacts_count}")
except:
    contacts_count = 0
    print("⚠️ Bronze contacts table not found")

# COMMAND ----------

transform_sql = """
CREATE OR REPLACE TABLE qobrix_silver.contact AS

SELECT
    CAST(c.id AS STRING) AS contact_id,
    CAST(c.ref AS STRING) AS contact_ref,
    
    -- Name handling (individual vs company)
    CASE 
        WHEN LOWER(COALESCE(c.is_company, '')) = 'true' THEN NULLIF(TRIM(c.name), '')
        ELSE CONCAT_WS(' ', 
            NULLIF(TRIM(c.first_name), ''),
            NULLIF(TRIM(c.last_name), '')
        )
    END AS full_name,
    NULLIF(TRIM(c.first_name), '') AS first_name,
    NULLIF(TRIM(c.last_name), '') AS last_name,
    NULLIF(TRIM(c.title), '') AS title,
    
    -- Company info
    CASE LOWER(COALESCE(c.is_company, ''))
        WHEN 'true' THEN TRUE
        ELSE FALSE
    END AS is_company,
    CASE 
        WHEN LOWER(COALESCE(c.is_company, '')) = 'true' THEN NULLIF(TRIM(c.name), '')
        ELSE NULL
    END AS company_name,
    NULLIF(TRIM(c.registration_number), '') AS registration_number,
    
    -- Contact info (cleaned and validated)
    NULLIF(TRIM(LOWER(c.email)), '') AS email,
    NULLIF(TRIM(LOWER(c.email_2)), '') AS email_2,
    NULLIF(TRIM(c.phone), '') AS phone,
    NULLIF(TRIM(c.phone_2), '') AS phone_2,
    NULLIF(TRIM(c.website), '') AS website,
    
    -- Role/Type (normalized)
    NULLIF(TRIM(LOWER(c.role)), '') AS role,
    
    -- Demographics
    NULLIF(TRIM(c.nationality), '') AS nationality,
    TRY_CAST(c.birthdate AS DATE) AS birthdate,
    NULLIF(TRIM(c.preferred_language), '') AS preferred_language,
    
    -- Address
    NULLIF(TRIM(c.street), '') AS street,
    NULLIF(TRIM(c.city), '') AS city,
    NULLIF(TRIM(c.state), '') AS state,
    NULLIF(TRIM(c.post_code), '') AS post_code,
    NULLIF(TRIM(c.country), '') AS country,
    
    -- Assignment
    NULLIF(TRIM(c.assigned_to), '') AS assigned_to,
    
    -- Description
    NULLIF(TRIM(c.description), '') AS description,
    
    -- Timestamps
    TRY_CAST(c.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(c.modified AS TIMESTAMP) AS modified_ts,
    NULLIF(TRIM(c.created_by), '') AS created_by,
    NULLIF(TRIM(c.modified_by), '') AS modified_by,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_contact_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.contacts c
WHERE c.id IS NOT NULL AND c.id != ''
"""

print("📊 Creating silver contact table...")
spark.sql(transform_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.contact").collect()[0]["c"]
print(f"✅ Silver contact records: {silver_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n📋 Silver Contact Summary:")
spark.sql("""
    SELECT 
        is_company,
        role,
        COUNT(*) as count
    FROM qobrix_silver.contact
    GROUP BY is_company, role
    ORDER BY is_company, role
""").show()

print("\n📋 Sample Silver Contacts:")
spark.sql("""
    SELECT contact_id, contact_ref, full_name, email, role, is_company, city, country
    FROM qobrix_silver.contact
    LIMIT 10
""").show(truncate=False)

