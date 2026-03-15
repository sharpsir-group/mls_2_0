#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_agents) -> Silver (qobrix_silver_agents)
#
# Purpose: Transform raw Qobrix agents from bronze into normalized silver
# per app_data_model.dbml. All columns gold needs are included to avoid UNRESOLVED_COLUMN.

# COMMAND ----------

from pyspark.sql import functions as F

# Match 00b and 02e: sharp + mls2
catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

print("Using catalog:", catalog, "schema:", schema)

# COMMAND ----------

# Full path so table is found regardless of current schema
bronze_table = f"{catalog}.{schema}.qobrix_api_agents"
bronze_df = spark.table(bronze_table)
bronze_cols = set(c.lower() for c in bronze_df.columns)
print(f"Bronze table {bronze_table}: {bronze_df.count()} rows, {len(bronze_cols)} columns")


def has_col(col_name: str) -> bool:
    return col_name.lower() in bronze_cols


def col_or_null(col_name: str, alias: str | None = None) -> str:
    alias = alias or col_name
    if has_col(col_name):
        return f"p.`{col_name}` AS {alias}"
    return f"NULL AS {alias}"


# COMMAND ----------

# Optional columns: avoid UNRESOLVED_COLUMN if bronze schema varies
legacy_id_expr = "TRIM(p.legacy_id) AS legacy_id" if has_col("legacy_id") else "NULL AS legacy_id"
commission_parts = [
    "TRY_CAST(p.commission_1 AS DECIMAL(20,4))" if has_col("commission_1") else "NULL",
    "TRY_CAST(p.commission_2 AS DECIMAL(20,4))" if has_col("commission_2") else "NULL",
    "TRY_CAST(p.commission_3 AS DECIMAL(20,4))" if has_col("commission_3") else "NULL",
]
commission_expr = f"COALESCE({', '.join(commission_parts)}) AS commission"
trashed_expr = "TRY_CAST(p.trashed AS TIMESTAMP) AS trashed" if has_col("trashed") else "CAST(NULL AS TIMESTAMP) AS trashed"

# Silver: normalize strings (TRIM), cast types; commission = coalesce(commission_1, 2, 3)
transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_agents AS
SELECT
    {col_or_null('id')},
    TRY_CAST(p.ref AS INT)                                   AS ref,
    {legacy_id_expr},
    TRIM(p.name)                                             AS name,
    TRIM(p.description)                                      AS description,
    TRIM(p.status)                                           AS status,
    TRIM(p.agent_type)                                       AS agent_type,
    {col_or_null('agency')},
    {col_or_null('owner')},
    {col_or_null('primary_contact')},
    {col_or_null('sub_agent_of')},
    TRY_CAST(p.agreement_date AS DATE)                       AS agreement_date,
    {commission_expr},
    TRY_CAST(p.created AS TIMESTAMP)                         AS created,
    {col_or_null('created_by')},
    TRY_CAST(p.modified AS TIMESTAMP)                        AS modified,
    {col_or_null('modified_by')},
    {trashed_expr}
FROM {bronze_table} p
"""

print("Creating mls2.qobrix_silver_agents from bronze...")
spark.sql(transform_sql)

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_agents")
print(f"✅ qobrix_silver_agents: {silver_df.count()} rows, {len(silver_df.columns)} columns")
