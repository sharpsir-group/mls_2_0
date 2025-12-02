# Databricks notebook source
# MAGIC %md
# MAGIC # MLS 2.0 – Silver → Gold RESO Member ETL
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant Member resource from normalized Qobrix agent data.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.agent`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.member` with RESO standard fields:
# MAGIC - `MemberKey` – Unique identifier (QOBRIX_AGENT_{id} or QOBRIX_USER_{id})
# MAGIC - `MemberMlsId` – MLS ID (Qobrix ref)
# MAGIC - `MemberFirstName`, `MemberLastName`, `MemberFullName`
# MAGIC - `MemberEmail`, `MemberPreferredPhone`
# MAGIC - `MemberStatus` – Active, Inactive
# MAGIC - `MemberType` – Agent, Staff, etc.
# MAGIC - `OfficeKey` – Link to Office resource
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Member+Resource
# MAGIC 
# MAGIC **Run After:** `02a_silver_qobrix_agent_etl.py`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS reso_gold")

print("Using catalog:", catalog)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create RESO Member from Silver Agent

# COMMAND ----------

# Check silver agent table
try:
    agent_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.agent").collect()[0]["c"]
    print(f"📋 Silver agent table has {agent_count} records")
except Exception as e:
    print(f"⚠️ Silver agent table not found: {e}")
    agent_count = 0

# COMMAND ----------

# Create Member table from silver agent (unified agents + users)

create_member_sql = """
CREATE OR REPLACE TABLE reso_gold.member AS

SELECT
    -- RESO core identifiers
    CASE a.source_type
        WHEN 'agent' THEN CONCAT('QOBRIX_AGENT_', a.agent_id)
        WHEN 'user'  THEN CONCAT('QOBRIX_USER_', a.agent_id)
        ELSE CONCAT('QOBRIX_MEMBER_', a.agent_id)
    END                                              AS MemberKey,
    COALESCE(a.agent_ref, '')                        AS MemberMlsId,
    
    -- Name fields
    COALESCE(a.first_name, '')                       AS MemberFirstName,
    COALESCE(a.last_name, '')                        AS MemberLastName,
    COALESCE(a.full_name, '')                        AS MemberFullName,
    
    -- Contact info
    COALESCE(a.email, '')                            AS MemberEmail,
    COALESCE(a.phone, '')                            AS MemberPreferredPhone,
    COALESCE(a.phone_2, '')                          AS MemberOfficePhone,
    
    -- Status mapping (already normalized in silver)
    CASE a.status
        WHEN 'active'   THEN 'Active'
        WHEN 'inactive' THEN 'Inactive'
        ELSE 'Active'
    END                                              AS MemberStatus,
    
    -- Member type mapping
    CASE a.agent_type
        WHEN 'agent'      THEN 'Agent'
        WHEN 'broker'     THEN 'Broker'
        WHEN 'salesperson' THEN 'Salesperson'
        WHEN 'admin'      THEN 'Admin'
        WHEN 'supervisor' THEN 'Supervisor'
        WHEN 'staff'      THEN 'Staff'
        ELSE 'Agent'
    END                                              AS MemberType,
    
    -- Office linkage
    CASE 
        WHEN a.parent_agent_id IS NOT NULL
        THEN CONCAT('QOBRIX_OFFICE_', a.parent_agent_id)
        ELSE NULL
    END                                              AS OfficeKey,
    
    -- Address
    COALESCE(a.street, '')                           AS MemberAddress1,
    COALESCE(a.city, '')                             AS MemberCity,
    COALESCE(a.state, '')                            AS MemberStateOrProvince,
    COALESCE(a.post_code, '')                        AS MemberPostalCode,
    COALESCE(a.country, '')                          AS MemberCountry,
    
    -- Qobrix extension fields (X_ prefix per RESO convention)
    a.agent_id                                       AS X_QobrixAgentId,
    a.agent_ref                                      AS X_QobrixAgentRef,
    CAST(NULL AS STRING)                             AS X_QobrixDescription,
    CAST(a.commission_rate AS STRING)                AS X_QobrixCommission1,
    CAST(NULL AS STRING)                             AS X_QobrixAgreementDate,
    a.owner_id                                       AS X_QobrixOwnerId,
    CAST(NULL AS STRING)                             AS X_QobrixPrimaryContactId,
    CAST(a.created_ts AS STRING)                     AS X_QobrixCreated,
    CAST(a.modified_ts AS STRING)                    AS X_QobrixModified,
    
    -- Source tracking
    a.source_type                                    AS X_QobrixSourceType,
    
    -- ETL metadata
    CURRENT_TIMESTAMP()                              AS etl_timestamp,
    CONCAT('member_batch_', CURRENT_DATE())          AS etl_batch_id

FROM qobrix_silver.agent a
"""

print("📊 Creating gold RESO Member table...")
spark.sql(create_member_sql)

member_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.member").collect()[0]["c"]
print(f"✅ Gold RESO Member records: {member_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show sample data
print("\n📋 Sample RESO Members:")
spark.sql("""
    SELECT MemberKey, MemberFullName, MemberEmail, MemberStatus, MemberType, X_QobrixSourceType
    FROM reso_gold.member
    LIMIT 10
""").show(truncate=False)

# Count by type
print("\n📊 Members by Source Type:")
spark.sql("""
    SELECT X_QobrixSourceType, COUNT(*) as count
    FROM reso_gold.member
    GROUP BY X_QobrixSourceType
""").show()

