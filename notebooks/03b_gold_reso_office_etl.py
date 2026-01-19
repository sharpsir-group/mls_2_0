# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Silver -> Gold RESO Office ETL
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant Office resource from normalized Qobrix agent data.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.agent` (offices = agents with sub-agents or top-level)
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.office` with RESO standard fields:
# MAGIC - `OfficeKey` - Unique identifier (QOBRIX_OFFICE_{id})
# MAGIC - `OfficeMlsId` - MLS ID (Qobrix ref)
# MAGIC - `OfficeName` - Office/agency name
# MAGIC - `OfficeEmail`, `OfficePhone`
# MAGIC - `OfficeStatus` - Active, Inactive
# MAGIC - `OfficeType` - MLS, Broker, etc.
# MAGIC - `OfficeAddress1`, `OfficeCity`, etc.
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Office+Resource
# MAGIC 
# MAGIC **Note:** In Qobrix, "agencies" are represented as agents that have sub-agents.
# MAGIC 
# MAGIC **Run After:** 02a_silver_qobrix_agent_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS reso_gold")

# Widget for OriginatingSystemOfficeKey (passed via job parameters)
dbutils.widgets.text("ORIGINATING_SYSTEM_OFFICE_KEY", "SHARPSIR-CY-001")
originating_office_key = os.getenv("SRC_1_OFFICE_KEY") or dbutils.widgets.get("ORIGINATING_SYSTEM_OFFICE_KEY") or "SHARPSIR-CY-001"

print("Using catalog:", catalog)
print("OriginatingSystemOfficeKey:", originating_office_key)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create RESO Office from Silver Agent

# COMMAND ----------

# Check silver agent table
try:
    agent_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.agent").collect()[0]["c"]
    print(f"📋 Silver agent table has {agent_count} records")
except Exception as e:
    print(f"⚠️ Silver agent table not found: {e}")
    agent_count = 0

# COMMAND ----------

# In Qobrix, agencies are agents that have other agents as sub-agents
# We identify "offices" as agents that are referenced by other agents' parent_agent_id field
# or agents without a parent (top-level)

create_office_sql = f"""
CREATE OR REPLACE TABLE reso_gold.office AS

SELECT DISTINCT
    -- RESO core identifiers
    CONCAT('QOBRIX_OFFICE_', a.agent_id)             AS OfficeKey,
    COALESCE(a.agent_ref, '')                        AS OfficeMlsId,
    
    -- Office name
    COALESCE(a.full_name, '')                        AS OfficeName,
    
    -- Contact info
    COALESCE(a.email, '')                            AS OfficeEmail,
    COALESCE(a.phone, a.phone_2, '')                 AS OfficePhone,
    COALESCE(a.phone_2, '')                          AS OfficeFax,
    
    -- Status mapping (already normalized in silver)
    CASE a.status
        WHEN 'active'   THEN 'Active'
        WHEN 'inactive' THEN 'Inactive'
        ELSE 'Active'
    END                                              AS OfficeStatus,
    
    -- Office type
    CASE a.agent_type
        WHEN 'broker'     THEN 'Broker'
        WHEN 'agency'     THEN 'MLS'
        ELSE 'Broker'
    END                                              AS OfficeType,
    
    -- Address
    COALESCE(a.street, '')                           AS OfficeAddress1,
    ''                                               AS OfficeAddress2,
    COALESCE(a.city, '')                             AS OfficeCity,
    COALESCE(a.state, '')                            AS OfficeStateOrProvince,
    COALESCE(a.post_code, '')                        AS OfficePostalCode,
    COALESCE(a.country, '')                          AS OfficeCountry,
    
    -- Broker info (if this office has a parent)
    CASE 
        WHEN a.parent_agent_id IS NOT NULL
        THEN CONCAT('QOBRIX_OFFICE_', a.parent_agent_id)
        ELSE NULL
    END                                              AS OfficeBrokerKey,
    
    -- Qobrix extension fields (X_ prefix per RESO convention)
    a.agent_id                                       AS X_QobrixAgentId,
    a.agent_ref                                      AS X_QobrixAgentRef,
    CAST(NULL AS STRING)                             AS X_QobrixDescription,
    CAST(a.commission_rate AS STRING)                AS X_QobrixCommission1,
    CAST(NULL AS STRING)                             AS X_QobrixCommission2,
    CAST(NULL AS STRING)                             AS X_QobrixCommission3,
    CAST(NULL AS STRING)                             AS X_QobrixAgreementDate,
    a.owner_id                                       AS X_QobrixOwnerId,
    CAST(NULL AS STRING)                             AS X_QobrixPrimaryContactId,
    CAST(a.created_ts AS STRING)                     AS X_QobrixCreated,
    CAST(a.modified_ts AS STRING)                    AS X_QobrixModified,
    
    -- Multi-tenant access control: Data source office
    -- SHARPSIR-CY-001 = Cyprus (Qobrix data source)
    -- SHARPSIR-HU-001 = Hungary (Dash JSON data source)
    '{originating_office_key}'                       AS OriginatingSystemOfficeKey,
    
    -- ETL metadata
    CURRENT_TIMESTAMP()                              AS etl_timestamp,
    CONCAT('office_batch_', CURRENT_DATE())          AS etl_batch_id

FROM qobrix_silver.agent a
WHERE a.source_type = 'agent'  -- Only agents (not users) become offices
  AND (
    -- Agents that are referenced as parent (have sub-agents)
    a.agent_id IN (SELECT DISTINCT parent_agent_id FROM qobrix_silver.agent WHERE parent_agent_id IS NOT NULL)
    -- OR agents with agent_type indicating they are an agency/broker
    OR a.agent_type IN ('agency', 'broker')
    -- OR top-level agents (no parent)
    OR a.parent_agent_id IS NULL
  )
"""

print("📊 Creating gold RESO Office table...")
spark.sql(create_office_sql)

office_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.office").collect()[0]["c"]
print(f"✅ Gold RESO Office records: {office_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show sample data
print("\n📋 Sample RESO Offices:")
spark.sql("""
    SELECT OfficeKey, OfficeName, OfficeEmail, OfficeCity, OfficeStatus, OfficeType
    FROM reso_gold.office
    LIMIT 10
""").show(truncate=False)

# Count by type
print("\n📊 Offices by Type:")
spark.sql("""
    SELECT OfficeType, COUNT(*) as count
    FROM reso_gold.office
    GROUP BY OfficeType
""").show()

