#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_property_types) -> Gold (common_property_types)
#
# Purpose: Property type dictionary for apps; dedup by code, keep latest modified.
# Gold columns: id, code, name, base_type, display_order (no config, no created/modified).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_property_types"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by code (one row per type code); keep latest modified
dedup_key_exprs = ["COALESCE(code, '') AS k_code"]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("k_code").orderBy(
                F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last()
            )
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_code")
)
dedup_df.createOrReplaceTempView("qobrix_silver_property_types_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold common.common_property_types ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_types AS
SELECT
    id            AS id,
    code          AS code,
    name          AS name,
    base_type     AS base_type,
    display_order AS display_order
FROM qobrix_silver_property_types_dedup
"""
)

gold_df = spark.table("common.common_property_types")
print(f"✅ common.common_property_types: {gold_df.count()} rows, {len(gold_df.columns)} columns")
