#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_media) -> Silver (qobrix_silver_media)
# Run only when 00b INCLUDE_MEDIA=True.

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

bronze_table = f"{catalog}.{schema}.qobrix_api_media"
try:
    spark.table(bronze_table).limit(1).collect()
    has_bronze = True
except Exception:
    has_bronze = False
if not has_bronze:
    print("⚠️ qobrix_api_media not found. Run 00b with INCLUDE_MEDIA=True first. Skipping.")
else:
    transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_media AS
SELECT
    id,
    category_id,
    TRIM(related_model) AS related_model,
    related_id,
    TRIM(media_type) AS media_type,
    TRIM(reference_id) AS reference_id,
    TRY_CAST(display_order AS INT) AS display_order,
    file_id,
    TRY_CAST(created AS TIMESTAMP) AS created,
    TRY_CAST(modified AS TIMESTAMP) AS modified
FROM {bronze_table}
"""
    spark.sql(transform_sql)
    silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_media")
    print(f"✅ qobrix_silver_media: {silver_df.count()} rows")