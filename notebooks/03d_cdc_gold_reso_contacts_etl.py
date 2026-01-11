# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - CDC Gold RESO Contacts ETL (Incremental)
# MAGIC 
# MAGIC **Purpose:** Transforms changed silver contacts to RESO format using MERGE.
# MAGIC 
# MAGIC **How it works:**
# MAGIC 1. Identifies contacts changed since last gold ETL (using `etl_timestamp`)
# MAGIC 2. MERGEs only changed records into gold (insert/update)
# MAGIC 3. Much faster than full refresh for incremental updates
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.contact`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.contacts`
# MAGIC 
# MAGIC **When to use:**
# MAGIC - After CDC silver sync: Run this notebook
# MAGIC - After full refresh silver: Run 03d_gold_reso_contacts_etl.py (full refresh)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

from datetime import datetime

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS reso_gold")

print("=" * 80)
print("🔄 CDC MODE - Gold RESO Contacts ETL")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Changed Records

# COMMAND ----------

# Get last gold ETL timestamp
try:
    last_gold_etl = spark.sql("""
        SELECT MAX(etl_timestamp) as last_etl 
        FROM reso_gold.contacts
    """).collect()[0]["last_etl"]
    
    if last_gold_etl:
        print(f"📊 Last gold ETL: {last_gold_etl}")
    else:
        last_gold_etl = datetime(2000, 1, 1)
        print("⚠️ Gold contacts table is empty, will process all records")
except:
    last_gold_etl = datetime(2000, 1, 1)
    print("⚠️ Gold contacts table doesn't exist, will create from scratch")

# Count changed records in silver
try:
    changed_count = spark.sql(f"""
        SELECT COUNT(*) as cnt 
        FROM qobrix_silver.contact 
        WHERE etl_timestamp > '{last_gold_etl}'
    """).collect()[0]["cnt"]
    print(f"📊 Changed contacts since last gold ETL: {changed_count}")
    use_cdc = changed_count > 0
except Exception as e:
    print(f"⚠️ Error checking silver: {e}")
    use_cdc = False
    changed_count = spark.sql("SELECT COUNT(*) as cnt FROM qobrix_silver.contact").collect()[0]["cnt"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## MERGE Changed Records

# COMMAND ----------

# Define the transformation SELECT (same as full refresh)
transform_select = """
SELECT
    -- RESO core identifiers
    CONCAT('QOBRIX_CONTACT_', c.contact_id)      AS ContactKey,
    COALESCE(c.contact_ref, '')                  AS ContactMlsId,
    
    -- Name fields (already normalized in silver)
    COALESCE(c.first_name, '')                   AS ContactFirstName,
    COALESCE(c.last_name, '')                    AS ContactLastName,
    COALESCE(c.full_name, '')                    AS ContactFullName,
    
    -- Contact info
    COALESCE(c.email, '')                        AS ContactEmail,
    COALESCE(c.email_2, '')                      AS ContactEmail2,
    COALESCE(c.phone, '')                        AS ContactPhone,
    COALESCE(c.phone_2, '')                      AS ContactPhone2,
    
    -- Contact type mapping (already normalized in silver)
    CASE c.role
        WHEN 'buyer'      THEN 'Buyer'
        WHEN 'seller'     THEN 'Seller'
        WHEN 'tenant'     THEN 'Tenant'
        WHEN 'landlord'   THEN 'Landlord'
        WHEN 'investor'   THEN 'Investor'
        WHEN 'agent'      THEN 'Agent'
        WHEN 'developer'  THEN 'Developer'
        ELSE 'Other'
    END                                          AS ContactType,
    
    -- Status
    'Active'                                     AS ContactStatus,
    
    -- Address
    COALESCE(c.street, '')                       AS ContactAddress1,
    COALESCE(c.city, '')                         AS ContactCity,
    COALESCE(c.state, '')                        AS ContactStateOrProvince,
    COALESCE(c.post_code, '')                    AS ContactPostalCode,
    COALESCE(c.country, '')                      AS ContactCountry,
    
    -- Additional RESO fields
    COALESCE(c.nationality, '')                  AS ContactNationality,
    COALESCE(c.title, '')                        AS ContactTitle,
    CAST(c.birthdate AS STRING)                  AS ContactBirthdate,
    COALESCE(c.website, '')                      AS ContactWebsite,
    
    -- Company info
    CASE c.is_company
        WHEN TRUE THEN 'Company'
        ELSE 'Individual'
    END                                          AS ContactEntityType,
    COALESCE(c.registration_number, '')          AS ContactCompanyRegistrationNumber,
    COALESCE(c.company_name, '')                 AS ContactCompanyName,
    
    -- Assigned agent linkage
    CASE 
        WHEN c.assigned_to IS NOT NULL
        THEN CONCAT('QOBRIX_USER_', c.assigned_to)
        ELSE NULL
    END                                          AS ContactAssignedToKey,
    
    -- Qobrix extension fields (X_ prefix)
    c.contact_id                                 AS X_QobrixContactId,
    c.contact_ref                                AS X_QobrixContactRef,
    CAST(NULL AS STRING)                         AS X_QobrixContactLegacyId,
    c.description                                AS X_QobrixDescription,
    c.preferred_language                         AS X_QobrixPreferredLanguage,
    CAST(NULL AS STRING)                         AS X_QobrixContactPersonFirstName,
    CAST(NULL AS STRING)                         AS X_QobrixContactPersonLastName,
    CAST(c.created_ts AS STRING)                 AS X_QobrixCreated,
    CAST(c.modified_ts AS STRING)                AS X_QobrixModified,
    c.created_by                                 AS X_QobrixCreatedBy,
    c.modified_by                                AS X_QobrixModifiedBy,
    
    -- ETL metadata
    CURRENT_TIMESTAMP()                          AS etl_timestamp,
    CONCAT('contacts_cdc_', CURRENT_DATE())      AS etl_batch_id

FROM qobrix_silver.contact c
"""

# Check if gold table exists
tables = [t.name for t in spark.catalog.listTables("reso_gold")]

if "contacts" not in tables:
    # First run - create table using DataFrame API (reliable)
    print("📊 Creating reso_gold.contacts table (first run)...")
    contacts_df = spark.sql(transform_select)
    df_count = contacts_df.count()
    print(f"📊 DataFrame has {df_count} rows")
    contacts_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("reso_gold.contacts")
    print(f"✅ Created reso_gold.contacts with {df_count} records")
    
elif not use_cdc:
    # Full refresh mode using DataFrame API (reliable)
    print("📊 Running full refresh (no CDC data available)...")
    contacts_df = spark.sql(transform_select)
    df_count = contacts_df.count()
    print(f"📊 DataFrame has {df_count} rows")
    contacts_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("reso_gold.contacts")
    print(f"✅ Full refresh complete: {df_count} records")
    
else:
    # CDC mode - MERGE only changed records
    print(f"📊 Merging {changed_count} changed contacts...")
    
    # Create temp view with only changed records
    cdc_filter = f"WHERE c.etl_timestamp > '{last_gold_etl}'"
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _cdc_gold_contacts AS
        {transform_select}
        {cdc_filter}
    """)
    
    # MERGE into gold
    merge_sql = """
        MERGE INTO reso_gold.contacts AS target
        USING _cdc_gold_contacts AS source
        ON target.ContactKey = source.ContactKey
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """
    
    spark.sql(merge_sql)
    print(f"✅ Merged {changed_count} contacts into reso_gold.contacts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

gold_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.contacts").collect()[0]["c"]
silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.contact").collect()[0]["c"]

print(f"\n📊 Silver contacts: {silver_count}")
print(f"📊 Gold RESO contacts: {gold_count}")

if silver_count == gold_count:
    print("✅ All contacts transferred successfully!")
else:
    diff = silver_count - gold_count
    print(f"⚠️ Difference: {diff} contacts")

# Show contact type breakdown
print("\n📊 Contacts by Type:")
spark.sql("""
    SELECT ContactType, COUNT(*) as count
    FROM reso_gold.contacts
    GROUP BY ContactType
    ORDER BY count DESC
""").show()

# Show recent changes
print("\n📋 Recent modifications:")
spark.sql("""
    SELECT ContactKey, ContactFullName, ContactEmail, ContactType, etl_timestamp
    FROM reso_gold.contacts
    ORDER BY etl_timestamp DESC
    LIMIT 5
""").show(truncate=False)

print("\n" + "=" * 80)
print("✅ CDC Gold RESO Contacts ETL Complete")
print("=" * 80)

