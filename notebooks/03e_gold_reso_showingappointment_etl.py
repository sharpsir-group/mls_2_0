# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MAGIC %md
# MAGIC # MLS 2.0 - Silver → Gold RESO ShowingAppointment ETL
# MAGIC 
# MAGIC **Purpose:** Creates RESO-compliant ShowingAppointment resource from normalized Qobrix viewing data.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.viewing`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.showing_appointment` with RESO standard fields:
# MAGIC - `ShowingAppointmentKey` - Unique identifier (QOBRIX_SHOWING_{id})
# MAGIC - `ListingKey` - Link to Property
# MAGIC - `ShowingAgentKey` - Agent conducting the showing
# MAGIC - `BuyerAgentKey` - Buyer's agent (if applicable)
# MAGIC - `ShowingDate`, `ShowingStartTime`, `ShowingEndTime`
# MAGIC - `ShowingStatus` - Scheduled, Confirmed, Completed, Cancelled
# MAGIC - `ShowingRemarks` - Notes/feedback
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/ShowingAppointment+Resource
# MAGIC 
# MAGIC **Run After:** `02d_silver_qobrix_viewing_etl.py`

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
# MAGIC ## Create RESO ShowingAppointment from Silver Viewing

# COMMAND ----------

# Check if silver viewing table exists and has data
try:
    viewings_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.viewing").collect()[0]["c"]
    print(f"📊 Silver viewing records: {viewings_count}")
    
    if viewings_count == 0:
        print("⚠️ No viewing records in silver layer.")
except Exception as e:
    print(f"⚠️ Silver viewing table not found: {e}")
    viewings_count = 0

# COMMAND ----------

if viewings_count > 0:
    create_showing_sql = """
    CREATE OR REPLACE TABLE reso_gold.showing_appointment AS
    
    SELECT
        -- RESO core identifiers
        CONCAT('QOBRIX_SHOWING_', v.viewing_id)      AS ShowingAppointmentKey,
        
        -- Property linkage
        CASE 
            WHEN v.property_id IS NOT NULL
            THEN CONCAT('QOBRIX_', v.property_id)
            ELSE NULL
        END                                          AS ListingKey,
        
        -- Agent linkage
        CASE 
            WHEN v.agent_id IS NOT NULL
            THEN CONCAT('QOBRIX_AGENT_', v.agent_id)
            WHEN v.user_id IS NOT NULL
            THEN CONCAT('QOBRIX_USER_', v.user_id)
            ELSE NULL
        END                                          AS ShowingAgentKey,
        
        -- Buyer/Contact linkage
        CASE 
            WHEN v.contact_id IS NOT NULL
            THEN CONCAT('QOBRIX_CONTACT_', v.contact_id)
            ELSE NULL
        END                                          AS BuyerContactKey,
        
        -- Date/Time fields (already normalized in silver)
        v.viewing_date                               AS ShowingDate,
        v.viewing_time                               AS ShowingStartTime,
        CASE 
            WHEN v.viewing_time IS NOT NULL AND v.duration_minutes IS NOT NULL
            THEN CONCAT(v.viewing_time, ' (+', CAST(v.duration_minutes AS STRING), ' min)')
            ELSE NULL
        END                                          AS ShowingEndTime,
        
        -- Status (already normalized in silver)
        CASE v.status
            WHEN 'scheduled'  THEN 'Scheduled'
            WHEN 'confirmed'  THEN 'Confirmed'
            WHEN 'completed'  THEN 'Completed'
            WHEN 'cancelled'  THEN 'Cancelled'
            WHEN 'no_show'    THEN 'NoShow'
            ELSE 'Scheduled'
        END                                          AS ShowingStatus,
        
        -- Showing type
        'InPerson'                                   AS ShowingType,
        
        -- Remarks/Notes (combine assessments)
        CONCAT_WS(' | ',
            CASE WHEN v.assessment_price IS NOT NULL 
                 THEN CONCAT('Price: ', v.assessment_price) ELSE NULL END,
            CASE WHEN v.assessment_location IS NOT NULL 
                 THEN CONCAT('Location: ', v.assessment_location) ELSE NULL END,
            CASE WHEN v.assessment_condition IS NOT NULL 
                 THEN CONCAT('Condition: ', v.assessment_condition) ELSE NULL END,
            CASE WHEN v.assessment_overall IS NOT NULL 
                 THEN CONCAT('Overall: ', v.assessment_overall) ELSE NULL END
        )                                            AS ShowingRemarks,
        COALESCE(v.feedback, v.notes, '')            AS ShowingFeedback,
        
        -- Interest level as outcome
        COALESCE(v.interest_level, '')               AS ShowingOutcome,
        
        -- Qobrix extension fields (X_ prefix)
        v.viewing_id                                 AS X_QobrixViewingId,
        CAST(NULL AS STRING)                         AS X_QobrixViewingRef,
        v.property_id                                AS X_QobrixPropertyId,
        v.contact_id                                 AS X_QobrixContactId,
        CAST(NULL AS STRING)                         AS X_QobrixOwnerId,
        CAST(v.viewing_date AS STRING)               AS X_QobrixDateTime,
        CAST(v.duration_minutes AS STRING)           AS X_QobrixDuration,
        CAST(NULL AS STRING)                         AS X_QobrixLocation,
        CAST(v.created_ts AS STRING)                 AS X_QobrixCreated,
        CAST(v.modified_ts AS STRING)                AS X_QobrixModified,
        v.created_by                                 AS X_QobrixCreatedBy,
        v.modified_by                                AS X_QobrixModifiedBy,
        
        -- ETL metadata
        CURRENT_TIMESTAMP()                          AS etl_timestamp,
        CONCAT('showing_batch_', CURRENT_DATE())     AS etl_batch_id
    
    FROM qobrix_silver.viewing v
    WHERE v.status != 'cancelled'  -- Exclude cancelled viewings
    """
    
    print("📊 Creating gold RESO ShowingAppointment table...")
    spark.sql(create_showing_sql)
else:
    # Create empty table with correct schema
    print("📊 Creating empty RESO ShowingAppointment table (no source data)...")
    spark.sql("""
    CREATE OR REPLACE TABLE reso_gold.showing_appointment (
        ShowingAppointmentKey STRING,
        ListingKey STRING,
        ShowingAgentKey STRING,
        BuyerContactKey STRING,
        ShowingDate DATE,
        ShowingStartTime STRING,
        ShowingEndTime STRING,
        ShowingStatus STRING,
        ShowingType STRING,
        ShowingRemarks STRING,
        ShowingFeedback STRING,
        ShowingOutcome STRING,
        X_QobrixViewingId STRING,
        X_QobrixViewingRef STRING,
        X_QobrixPropertyId STRING,
        X_QobrixContactId STRING,
        X_QobrixOwnerId STRING,
        X_QobrixDateTime STRING,
        X_QobrixDuration STRING,
        X_QobrixLocation STRING,
        X_QobrixCreated STRING,
        X_QobrixModified STRING,
        X_QobrixCreatedBy STRING,
        X_QobrixModifiedBy STRING,
        etl_timestamp TIMESTAMP,
        etl_batch_id STRING
    )
    """)

gold_showing_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.showing_appointment").collect()[0]["c"]
print(f"✅ Gold RESO ShowingAppointment records: {gold_showing_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

if gold_showing_count > 0:
    # Show sample data
    print("\n📋 Sample RESO ShowingAppointments:")
    spark.sql("""
        SELECT ShowingAppointmentKey, ListingKey, ShowingDate, ShowingStatus, ShowingType
        FROM reso_gold.showing_appointment
        LIMIT 10
    """).show(truncate=False)
    
    # Count by status
    print("\n📊 Showings by Status:")
    spark.sql("""
        SELECT ShowingStatus, COUNT(*) as count
        FROM reso_gold.showing_appointment
        GROUP BY ShowingStatus
        ORDER BY count DESC
    """).show()
    
    # Count by type
    print("\n📊 Showings by Type:")
    spark.sql("""
        SELECT ShowingType, COUNT(*) as count
        FROM reso_gold.showing_appointment
        GROUP BY ShowingType
    """).show()
    
    # Showings per month (if we have dates)
    print("\n📊 Showings by Month:")
    spark.sql("""
        SELECT DATE_TRUNC('month', ShowingDate) as month, COUNT(*) as count
        FROM reso_gold.showing_appointment
        WHERE ShowingDate IS NOT NULL
        GROUP BY DATE_TRUNC('month', ShowingDate)
        ORDER BY month DESC
        LIMIT 12
    """).show()
else:
    print("\n⚠️ No showing appointment records to display")

