#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_agents) -> Gold (common_agents)
#
# Purpose: One row per agent; dedup by ref, keep latest modified.
# No ::uuid (Spark uses STRING for UUIDs). Window from pyspark.sql.window.
# Gold column names per DBML: agency_id, owner_profile_id, primary_contact_profile_id, sub_agent_of_id.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_agents"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by ref (one row per agent ref; keep latest modified)
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
dedup_df.createOrReplaceTempView("qobrix_silver_agents_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

print("Creating gold common.common_agents ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_agents AS
SELECT
    id                                       AS id,
    ref                                      AS ref,
    name                                     AS name,
    description                              AS description,
    status                                   AS status,
    agent_type                               AS agent_type,
    agency                                   AS agency_id,
    owner                                    AS owner_profile_id,
    primary_contact                          AS primary_contact_profile_id,
    sub_agent_of                             AS sub_agent_of_id,
    agreement_date                           AS agreement_date,
    commission                               AS commission,
    created                                  AS created,
    created_by                               AS created_by,
    modified                                 AS modified,
    modified_by                              AS modified_by
FROM qobrix_silver_agents_dedup
"""
)

gold_df = spark.table("common.common_agents")
print(f"✅ common.common_agents: {gold_df.count()} rows, {len(gold_df.columns)} columns")
