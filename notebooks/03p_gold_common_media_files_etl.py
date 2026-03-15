#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_media_files) -> Gold (common_media_files)
# Run 02p first (and 00b with INCLUDE_MEDIA=True).

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

silver_table = f"{catalog}.{schema}.qobrix_silver_media_files"
try:
    silver_df = spark.table(silver_table)
    spark.sql(
        f"""
CREATE OR REPLACE TABLE common.common_media_files AS
SELECT id, filename, original_filename, original_url, href, thumbnails, mime_type, filesize, filesystem
FROM {silver_table}
"""
    )
    gold_df = spark.table("common.common_media_files")
    print(f"✅ common.common_media_files: {gold_df.count()} rows")
except Exception:
    spark.sql(
        """
CREATE TABLE IF NOT EXISTS common.common_media_files (
    id STRING, filename STRING, original_filename STRING, original_url STRING, href STRING,
    thumbnails STRING, mime_type STRING, filesize INT, filesystem STRING
)
"""
    )
    print("✅ common.common_media_files: created (empty; run 02p after 00b INCLUDE_MEDIA=True)")