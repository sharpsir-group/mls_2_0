#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_media_files) -> Silver (qobrix_silver_media_files)
# Run only when 00b INCLUDE_MEDIA=True; otherwise bronze table may be missing.

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

bronze_table = f"{catalog}.{schema}.qobrix_api_media_files"
try:
    spark.table(bronze_table).limit(1).collect()
    has_bronze = True
except Exception:
    has_bronze = False
if not has_bronze:
    print("⚠️ qobrix_api_media_files not found. Run 00b with INCLUDE_MEDIA=True first. Skipping.")
else:
    transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_media_files AS
SELECT
    id, TRIM(filename) AS filename, TRIM(original_filename) AS original_filename,
    TRIM(original_url) AS original_url, TRIM(href) AS href, thumbnails,
    TRIM(mime_type) AS mime_type, TRY_CAST(filesize AS INT) AS filesize, TRIM(filesystem) AS filesystem,
    TRY_CAST(created AS TIMESTAMP) AS created, TRY_CAST(modified AS TIMESTAMP) AS modified
FROM {bronze_table}
"""
    spark.sql(transform_sql)
    silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_media_files")
    print(f"✅ qobrix_silver_media_files: {silver_df.count()} rows")