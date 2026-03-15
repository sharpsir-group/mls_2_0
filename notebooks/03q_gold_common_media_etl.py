#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_media) -> Gold (common_media)
# Run 02q first (and 00b with INCLUDE_MEDIA=True).

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

silver_table = f"{catalog}.{schema}.qobrix_silver_media"
try:
    silver_df = spark.table(silver_table)
    spark.sql(
        f"""
CREATE OR REPLACE TABLE common.common_media AS
SELECT
    id,
    related_model AS entity_type,
    related_id AS entity_id,
    category_id,
    media_type,
    reference_id,
    display_order,
    file_id,
    created,
    CAST(NULL AS STRING) AS created_by,
    modified,
    CAST(NULL AS STRING) AS modified_by
FROM {silver_table}
"""
    )
    gold_df = spark.table("common.common_media")
    print(f"✅ common.common_media: {gold_df.count()} rows")
except Exception:
    spark.sql(
        """
CREATE TABLE IF NOT EXISTS common.common_media (
    id STRING, entity_type STRING, entity_id STRING, category_id STRING, media_type STRING,
    reference_id STRING, display_order INT, file_id STRING, created TIMESTAMP, created_by STRING,
    modified TIMESTAMP, modified_by STRING
)
"""
    )
    print("✅ common.common_media: created (empty; run 02q after 00b INCLUDE_MEDIA=True)")