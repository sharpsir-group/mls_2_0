# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 – Silver → Gold RESO Contacts ETL
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant Contacts resource from normalized Qobrix contact data.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.contact`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.contacts` with RESO standard fields:
# MAGIC - `ContactKey` – Unique identifier (QOBRIX_CONTACT_{id})
# MAGIC - `ContactFirstName`, `ContactLastName`, `ContactFullName`
# MAGIC - `ContactEmail`, `ContactPhone`
# MAGIC - `ContactType` – Buyer, Seller, Tenant, Landlord, etc.
# MAGIC - `ContactStatus` – Active, Inactive
# MAGIC - `ContactAddress`, `ContactCity`, `ContactCountry`
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Contacts+Resource
# MAGIC 
# MAGIC **Run After:** `02b_silver_qobrix_contact_etl.py`

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
# MAGIC ## Create RESO Contacts from Silver Contact

# COMMAND ----------

# Check if silver contact table exists and has data
try:
    contacts_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.contact").collect()[0]["c"]
    print(f"📊 Silver contact records: {contacts_count}")
    
    if contacts_count == 0:
        print("⚠️ No contact records in silver layer.")
except Exception as e:
    print(f"⚠️ Silver contact table not found: {e}")
    contacts_count = 0

# COMMAND ----------

if contacts_count > 0:
    create_contacts_sql = """
    CREATE OR REPLACE TABLE reso_gold.contacts AS
    
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
        CONCAT('contacts_batch_', CURRENT_DATE())    AS etl_batch_id
    
    FROM qobrix_silver.contact c
    """
    
    print("📊 Creating gold RESO Contacts table...")
    spark.sql(create_contacts_sql)
else:
    # Create empty table with correct schema
    print("📊 Creating empty RESO Contacts table (no source data)...")
    spark.sql("""
    CREATE OR REPLACE TABLE reso_gold.contacts (
        ContactKey STRING,
        ContactMlsId STRING,
        ContactFirstName STRING,
        ContactLastName STRING,
        ContactFullName STRING,
        ContactEmail STRING,
        ContactEmail2 STRING,
        ContactPhone STRING,
        ContactPhone2 STRING,
        ContactType STRING,
        ContactStatus STRING,
        ContactAddress1 STRING,
        ContactCity STRING,
        ContactStateOrProvince STRING,
        ContactPostalCode STRING,
        ContactCountry STRING,
        ContactNationality STRING,
        ContactTitle STRING,
        ContactBirthdate STRING,
        ContactWebsite STRING,
        ContactEntityType STRING,
        ContactCompanyRegistrationNumber STRING,
        ContactAssignedToKey STRING,
        X_QobrixContactId STRING,
        X_QobrixContactRef STRING,
        X_QobrixContactLegacyId STRING,
        X_QobrixDescription STRING,
        X_QobrixPreferredLanguage STRING,
        X_QobrixContactPersonFirstName STRING,
        X_QobrixContactPersonLastName STRING,
        X_QobrixCreated STRING,
        X_QobrixModified STRING,
        X_QobrixCreatedBy STRING,
        X_QobrixModifiedBy STRING,
        etl_timestamp TIMESTAMP,
        etl_batch_id STRING
    )
    """)

gold_contacts_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.contacts").collect()[0]["c"]
print(f"✅ Gold RESO Contacts records: {gold_contacts_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if gold_contacts_count > 0:
    # Show sample data
    print("\n📋 Sample RESO Contacts:")
    spark.sql("""
        SELECT ContactKey, ContactFullName, ContactEmail, ContactType, ContactCity, ContactCountry
        FROM reso_gold.contacts
        LIMIT 10
    """).show(truncate=False)
    
    # Count by type
    print("\n📊 Contacts by Type:")
    spark.sql("""
        SELECT ContactType, COUNT(*) as count
        FROM reso_gold.contacts
        GROUP BY ContactType
        ORDER BY count DESC
    """).show()
    
    # Count by entity type
    print("\n📊 Contacts by Entity Type:")
    spark.sql("""
        SELECT ContactEntityType, COUNT(*) as count
        FROM reso_gold.contacts
        GROUP BY ContactEntityType
    """).show()
else:
    print("\n⚠️ No contacts records to display")

