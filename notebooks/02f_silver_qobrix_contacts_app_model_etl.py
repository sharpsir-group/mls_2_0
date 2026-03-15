#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_contacts) -> Silver (qobrix_silver_contacts)
#
# Purpose: Transform raw Qobrix contacts from bronze into normalized silver
# per app_data_model.dbml. All columns gold needs are included to avoid UNRESOLVED_COLUMN.

# COMMAND ----------

from pyspark.sql import functions as F

# Match 00b and 02e: sharp + mls2
catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

print("Using catalog:", catalog, "schema:", schema)

# COMMAND ----------

# Full path so table is found regardless of current schema
bronze_table = f"{catalog}.{schema}.qobrix_api_contacts"
bronze_df = spark.table(bronze_table)
bronze_cols = set(c.lower() for c in bronze_df.columns)
print(f"Bronze table {bronze_table}: {bronze_df.count()} rows, {len(bronze_cols)} columns")


def has_col(col_name: str) -> bool:
    return col_name.lower() in bronze_cols


def col_or_null(col_name: str, alias: str | None = None) -> str:
    alias = alias or col_name
    if has_col(col_name):
        return f"p.`{col_name}` AS {alias}"
    return f"NULL AS {alias}"


# COMMAND ----------

# Silver: normalize strings (TRIM/LOWER), cast types; include every column gold needs
transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_contacts AS
SELECT
    {col_or_null('id')},
    TRY_CAST(p.ref AS INT)                                   AS ref,
    TRIM(p.first_name)                                       AS first_name,
    TRIM(p.last_name)                                        AS last_name,
    TRIM(p.name)                                             AS name,
    TRY_CAST(p.is_company AS BOOLEAN)                        AS is_company,
    CASE WHEN p.email IS NULL OR TRIM(p.email) = '' THEN NULL ELSE LOWER(TRIM(p.email)) END AS email,
    CASE WHEN p.email_2 IS NULL OR TRIM(p.email_2) = '' THEN NULL ELSE LOWER(TRIM(p.email_2)) END AS email_2,
    TRIM(p.phone)                                            AS phone,
    TRIM(p.phone_2)                                         AS phone_2,
    CASE WHEN p.website IS NULL OR TRIM(p.website) = '' THEN NULL
         WHEN LOWER(TRIM(p.website)) LIKE 'http%' THEN TRIM(p.website)
         ELSE CONCAT('https://', TRIM(p.website)) END         AS website,
    TRIM(p.street)                                           AS street,
    TRIM(p.city)                                             AS city,
    TRIM(p.state)                                            AS state,
    TRIM(p.post_code)                                        AS post_code,
    UPPER(TRIM(p.country))                                   AS country,
    TRIM(p.role)                                             AS role,
    TRIM(p.registration_number)                              AS registration_number,
    TRIM(p.vat_number)                                       AS vat_number,
    TRIM(p.nationality)                                      AS nationality,
    {col_or_null('assigned_to')},
    TRIM(p.description)                                     AS description,
    COALESCE(TRY_CAST(p.email_consent AS BOOLEAN), TRUE)     AS email_consent,
    COALESCE(TRY_CAST(p.sms_consent AS BOOLEAN), TRUE)        AS sms_consent,
    COALESCE(TRY_CAST(p.phone_consent AS BOOLEAN), TRUE)      AS phone_consent,
    COALESCE(TRY_CAST(p.postal_consent AS BOOLEAN), TRUE)     AS postal_consent,
    COALESCE(TRY_CAST(p.marketing_consent AS BOOLEAN), TRUE)  AS marketing_consent,
    {col_or_null('consent_token')},
    TRY_CAST(p.personal_data_cleared AS TIMESTAMP)           AS personal_data_cleared,
    TRY_CAST(p.created AS TIMESTAMP)                         AS created,
    TRY_CAST(p.modified AS TIMESTAMP)                        AS modified,
    {col_or_null('created_by')},
    {col_or_null('modified_by')},
    TRIM(p.custom_contact_person_first_name)                 AS custom_contact_person_first_name,
    TRIM(p.custom_contact_person_last_name)                  AS custom_contact_person_last_name,
    {col_or_null('custom_works_for')},
    TRIM(p.custom_mailchimp_subscriber_status)               AS custom_mailchimp_subscriber_status
FROM {bronze_table} p
"""

# Retry on Delta concurrent metadata change (e.g. when multiple job tasks run in parallel)
import time
max_retries = 3
for attempt in range(max_retries):
    try:
        print("Creating mls2.qobrix_silver_contacts from bronze...")
        spark.sql(transform_sql)
        break
    except Exception as e:
        msg = str(e).upper()
        if ("METADATA_CHANGED" in msg or "CONCURRENT" in msg) and attempt < max_retries - 1:
            wait_sec = (attempt + 1) * 5
            print(f"Concurrent update conflict, retrying in {wait_sec}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_sec)
        else:
            raise

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_contacts")
print(f"✅ qobrix_silver_contacts: {silver_df.count()} rows, {len(silver_df.columns)} columns")
