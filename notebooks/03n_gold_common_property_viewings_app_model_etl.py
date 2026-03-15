#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_property_viewings) -> Gold (common_property_viewings)
#
# Purpose: One row per property-viewing assessment; dedup by (property_id, viewing_id), keep latest modified.
# Gold: no trashed column (per app_data_model.dbml).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_property_viewings"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by (property_id, viewing_id); keep latest modified
dedup_key_exprs = [
    "COALESCE(CAST(property_id AS STRING), '') AS k_property_id",
    "COALESCE(CAST(viewing_id AS STRING), '') AS k_viewing_id",
]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("k_property_id", "k_viewing_id").orderBy(
                F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last()
            )
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_property_id", "k_viewing_id")
)
dedup_df.createOrReplaceTempView("qobrix_silver_property_viewings_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold common.common_property_viewings ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_viewings AS
SELECT
    id                           AS id,
    property_id                   AS property_id,
    viewing_id                    AS viewing_id,
    display_order                 AS display_order,
    further_feedback              AS further_feedback,
    exterior_appeal_assessment    AS exterior_appeal_assessment,
    interior_appeal_assessment    AS interior_appeal_assessment,
    location_assessment           AS location_assessment,
    price_assessment             AS price_assessment,
    views_assessment              AS views_assessment,
    viewing_outcome               AS viewing_outcome,
    created                       AS created,
    created_by                    AS created_by,
    modified                      AS modified,
    modified_by                   AS modified_by
FROM qobrix_silver_property_viewings_dedup
"""
)

gold_df = spark.table("common.common_property_viewings")
print(f"✅ common.common_property_viewings: {gold_df.count()} rows, {len(gold_df.columns)} columns")
