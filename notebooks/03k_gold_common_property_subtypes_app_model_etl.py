#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_property_subtypes) -> Gold (common_property_subtypes)
#
# Purpose: Property subtype dictionary for apps; dedup by (code, property_type), keep latest modified.
# Gold columns: id, code, label, property_type only (no created/modified).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_property_subtypes"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by (code, property_type); keep latest modified
dedup_key_exprs = [
    "COALESCE(code, '') AS k_code",
    "COALESCE(property_type, '') AS k_property_type",
]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("k_code", "k_property_type").orderBy(
                F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last()
            )
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_code", "k_property_type")
)
dedup_df.createOrReplaceTempView("qobrix_silver_property_subtypes_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold common.common_property_subtypes ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_subtypes AS
SELECT
    id            AS id,
    code          AS code,
    label         AS label,
    property_type AS property_type
FROM qobrix_silver_property_subtypes_dedup
"""
)

gold_df = spark.table("common.common_property_subtypes")
print(f"✅ common.common_property_subtypes: {gold_df.count()} rows, {len(gold_df.columns)} columns")
