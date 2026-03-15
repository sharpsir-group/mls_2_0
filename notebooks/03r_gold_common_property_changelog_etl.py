#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_property_changes) -> Gold (common_property_changelog)
#
# Purpose: One row per property change event; maps bronze audit log to gold audit table.
# Run 00b first to populate qobrix_api_property_changes.

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

bronze_table = f"{catalog}.{schema}.qobrix_api_property_changes"
try:
    spark.table(bronze_table).limit(1).collect()
    has_bronze = True
except Exception:
    has_bronze = False
if has_bronze:
    spark.sql(
        f"""
CREATE OR REPLACE TABLE common.common_property_changelog AS
SELECT
    id                                       AS id,
    primary_key                              AS property_id,
    TRY_CAST(timestamp AS TIMESTAMP)         AS changed_at,
    user_id                                  AS changed_by_user_id,
    TRIM(type)                               AS event_type,
    CAST(NULL AS STRING)                     AS field_name,
    original                                 AS old_value,
    changed                                  AS new_value,
    'qobrix'                                 AS source_system,
    id                                       AS raw_event_id
FROM {bronze_table}
"""
    )
    gold_df = spark.table("common.common_property_changelog")
    print(f"✅ common.common_property_changelog: {gold_df.count()} rows")
else:
    # Empty table with correct schema
    spark.sql(
        """
CREATE OR REPLACE TABLE common.common_property_changelog (
    id STRING,
    property_id STRING,
    changed_at TIMESTAMP,
    changed_by_user_id STRING,
    event_type STRING,
    field_name STRING,
    old_value STRING,
    new_value STRING,
    source_system STRING,
    raw_event_id STRING
)
"""
    )
    print("✅ common.common_property_changelog: created (empty; run 00b with property changes to populate)")