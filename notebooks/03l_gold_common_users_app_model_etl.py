#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_users) -> Gold (common_users)
#
# Purpose: One row per user; dedup by id, keep latest modified.
# Gold: id, contact_id, active, role, username, name (per app_data_model.dbml).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_users"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by id (one row per user); keep latest modified
dedup_key_exprs = ["COALESCE(CAST(id AS STRING), '') AS k_id"]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("k_id").orderBy(
                F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last()
            )
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_id")
)
dedup_df.createOrReplaceTempView("qobrix_silver_users_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold common.common_users ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_users AS
SELECT
    id         AS id,
    contact_id AS contact_id,
    active     AS active,
    role       AS role,
    username   AS username,
    name       AS name
FROM qobrix_silver_users_dedup
"""
)

gold_df = spark.table("common.common_users")
print(f"✅ common.common_users: {gold_df.count()} rows, {len(gold_df.columns)} columns")
