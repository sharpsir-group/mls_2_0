# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 - Bronze → Silver Agent ETL
# MAGIC 
# MAGIC **Purpose:** Normalizes and cleans agent data from bronze layer.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_bronze.agents`, `mls2.qobrix_bronze.users`
# MAGIC 
# MAGIC **Output:** `mls2.qobrix_silver.agent` with normalized fields:
# MAGIC - Unified agent/user records
# MAGIC - Cleaned contact information
# MAGIC - Normalized status values
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
# MAGIC ## Transform Bronze Agents to Silver

# COMMAND ----------

# Check source tables
try:
    agents_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.agents").collect()[0]["c"]
    print(f"📊 Bronze agents: {agents_count}")
except:
    agents_count = 0
    print("⚠️ Bronze agents table not found")

try:
    users_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_bronze.users").collect()[0]["c"]
    print(f"📊 Bronze users: {users_count}")
except:
    users_count = 0
    print("⚠️ Bronze users table not found")

# COMMAND ----------

transform_sql = """
CREATE OR REPLACE TABLE qobrix_silver.agent AS

-- Agents
SELECT
    'agent' AS source_type,
    CAST(a.id AS STRING) AS agent_id,
    CAST(a.ref AS STRING) AS agent_ref,
    
    -- Name (from agent or primary contact)
    COALESCE(
        NULLIF(TRIM(a.name), ''),
        CONCAT_WS(' ', 
            NULLIF(TRIM(a.primary_contact_contact_first_name), ''),
            NULLIF(TRIM(a.primary_contact_contact_last_name), '')
        )
    ) AS full_name,
    NULLIF(TRIM(a.primary_contact_contact_first_name), '') AS first_name,
    NULLIF(TRIM(a.primary_contact_contact_last_name), '') AS last_name,
    
    -- Contact info (cleaned)
    NULLIF(TRIM(LOWER(a.primary_contact_contact_email)), '') AS email,
    NULLIF(TRIM(a.primary_contact_contact_email_2), '') AS email_2,
    NULLIF(TRIM(a.primary_contact_contact_phone), '') AS phone,
    NULLIF(TRIM(a.primary_contact_contact_phone_2), '') AS phone_2,
    
    -- Status (normalized)
    CASE LOWER(COALESCE(a.status, ''))
        WHEN 'active' THEN 'active'
        WHEN 'inactive' THEN 'inactive'
        WHEN '' THEN 'active'
        ELSE LOWER(a.status)
    END AS status,
    
    -- Type
    NULLIF(TRIM(LOWER(a.agent_type)), '') AS agent_type,
    
    -- Organization
    NULLIF(TRIM(a.sub_agent_of), '') AS parent_agent_id,
    NULLIF(TRIM(a.owner), '') AS owner_id,
    
    -- Address
    NULLIF(TRIM(a.primary_contact_contact_street), '') AS street,
    NULLIF(TRIM(a.primary_contact_contact_city), '') AS city,
    NULLIF(TRIM(a.primary_contact_contact_state), '') AS state,
    NULLIF(TRIM(a.primary_contact_contact_post_code), '') AS post_code,
    NULLIF(TRIM(a.primary_contact_contact_country), '') AS country,
    
    -- Commission
    TRY_CAST(a.commission_1 AS DECIMAL(10,2)) AS commission_rate,
    
    -- Timestamps
    TRY_CAST(a.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(a.modified AS TIMESTAMP) AS modified_ts,
    NULLIF(TRIM(a.created_by), '') AS created_by,
    NULLIF(TRIM(a.modified_by), '') AS modified_by,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_agent_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.agents a
WHERE a.id IS NOT NULL AND a.id != ''

UNION ALL

-- Users (as agents)
SELECT
    'user' AS source_type,
    CAST(u.id AS STRING) AS agent_id,
    CAST(u.username AS STRING) AS agent_ref,
    
    -- Name
    COALESCE(
        NULLIF(TRIM(u.name), ''),
        NULLIF(TRIM(u.extra_first_name), '')
    ) AS full_name,
    NULLIF(TRIM(u.extra_first_name), '') AS first_name,
    CASE 
        WHEN u.name IS NOT NULL AND u.name != '' AND INSTR(u.name, ' ') > 0
        THEN TRIM(SUBSTR(u.name, INSTR(u.name, ' ') + 1))
        ELSE NULL
    END AS last_name,
    
    -- Contact info
    NULLIF(TRIM(LOWER(u.extra_email)), '') AS email,
    NULL AS email_2,
    NULLIF(TRIM(u.extra_phone_mobile), '') AS phone,
    NULLIF(TRIM(u.phone_extension), '') AS phone_2,
    
    -- Status
    CASE 
        WHEN LOWER(COALESCE(u.active, '')) = 'true' THEN 'active'
        ELSE 'inactive'
    END AS status,
    
    -- Type
    CASE 
        WHEN LOWER(COALESCE(u.is_admin, '')) = 'true' THEN 'admin'
        WHEN LOWER(COALESCE(u.is_supervisor, '')) = 'true' THEN 'supervisor'
        ELSE 'staff'
    END AS agent_type,
    
    -- Organization
    NULLIF(TRIM(u.reports_to), '') AS parent_agent_id,
    NULL AS owner_id,
    
    -- Address (users don't have address in bronze)
    NULL AS street,
    NULL AS city,
    NULL AS state,
    NULL AS post_code,
    NULL AS country,
    
    -- Commission (users don't have commission)
    NULL AS commission_rate,
    
    -- Timestamps
    TRY_CAST(u.created AS TIMESTAMP) AS created_ts,
    TRY_CAST(u.modified AS TIMESTAMP) AS modified_ts,
    NULLIF(TRIM(u.created_by), '') AS created_by,
    NULLIF(TRIM(u.modified_by), '') AS modified_by,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('silver_agent_batch_', CURRENT_DATE()) AS etl_batch_id

FROM qobrix_bronze.users u
WHERE u.id IS NOT NULL AND u.id != ''
"""

print("📊 Creating silver agent table...")
spark.sql(transform_sql)

silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.agent").collect()[0]["c"]
print(f"✅ Silver agent records: {silver_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n📋 Silver Agent Summary:")
spark.sql("""
    SELECT source_type, status, COUNT(*) as count
    FROM qobrix_silver.agent
    GROUP BY source_type, status
    ORDER BY source_type, status
""").show()

print("\n📋 Sample Silver Agents:")
spark.sql("""
    SELECT agent_id, agent_ref, full_name, email, status, agent_type, source_type
    FROM qobrix_silver.agent
    LIMIT 10
""").show(truncate=False)

