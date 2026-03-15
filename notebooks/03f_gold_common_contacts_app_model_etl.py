#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_contacts) -> Gold (common_contact_profiles)
#
# Purpose: One row per contact; dedup by ref, keep latest modified.
# No ::uuid (Spark uses STRING for UUIDs). Window from pyspark.sql.window.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_contacts"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by ref (one row per contact ref; keep latest modified)
dedup_key_exprs = ["COALESCE(CAST(ref AS STRING), '') AS k_ref"]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("k_ref").orderBy(
                F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last()
            )
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_ref")
)
dedup_df.createOrReplaceTempView("qobrix_silver_contacts_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold.common_contact_profiles ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_contact_profiles AS
SELECT
    id                                       AS id,
    ref                                      AS ref,
    first_name                               AS first_name,
    last_name                                AS last_name,
    name                                     AS name,
    is_company                               AS is_company,
    email                                    AS email,
    email_2                                  AS email_2,
    phone                                    AS phone,
    phone_2                                  AS phone_2,
    website                                  AS website,
    street                                   AS street,
    city                                     AS city,
    state                                    AS state,
    post_code                                AS post_code,
    country                                  AS country,
    role                                     AS role,
    registration_number                      AS registration_number,
    vat_number                               AS vat_number,
    nationality                              AS nationality,
    assigned_to                              AS assigned_to,
    description                              AS description,
    email_consent                            AS email_consent,
    sms_consent                              AS sms_consent,
    phone_consent                            AS phone_consent,
    postal_consent                           AS postal_consent,
    marketing_consent                        AS marketing_consent,
    consent_token                            AS consent_token,
    personal_data_cleared                     AS personal_data_cleared,
    created                                  AS created,
    modified                                 AS modified,
    created_by                               AS created_by,
    modified_by                              AS modified_by,
    custom_contact_person_first_name         AS custom_contact_person_first_name,
    custom_contact_person_last_name          AS custom_contact_person_last_name,
    custom_works_for                          AS custom_works_for,
    custom_mailchimp_subscriber_status       AS custom_mailchimp_subscriber_status
FROM qobrix_silver_contacts_dedup
"""
)

gold_df = spark.table("common.common_contact_profiles")
print(f"✅ common.common_contact_profiles: {gold_df.count()} rows, {len(gold_df.columns)} columns")
