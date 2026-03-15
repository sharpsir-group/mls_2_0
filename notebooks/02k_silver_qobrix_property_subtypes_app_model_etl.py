#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_property_subtypes) -> Silver (qobrix_silver_property_subtypes)
#
# Purpose: Transform property subtype dictionary from bronze into normalized silver per app_data_model.dbml.

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

print("Using catalog:", catalog, "schema:", schema)

# COMMAND ----------

bronze_table = f"{catalog}.{schema}.qobrix_api_property_subtypes"
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


def trim_or_null(col_name: str) -> str:
    if has_col(col_name):
        return f"TRIM(p.`{col_name}`) AS {col_name}"
    return f"NULL AS {col_name}"


def try_cast_or_null(col_name: str, cast_type: str) -> str:
    if has_col(col_name):
        return f"TRY_CAST(p.`{col_name}` AS {cast_type}) AS {col_name}"
    return f"CAST(NULL AS {cast_type}) AS {col_name}"


# COMMAND ----------

transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_property_subtypes AS
SELECT
    {col_or_null('id')},
    {trim_or_null('code')},
    {trim_or_null('label')},
    {trim_or_null('property_type')},
    {try_cast_or_null('created', 'TIMESTAMP')},
    {col_or_null('created_by')},
    {try_cast_or_null('modified', 'TIMESTAMP')},
    {col_or_null('modified_by')},
    {try_cast_or_null('trashed', 'TIMESTAMP')}
FROM {bronze_table} p
"""

print("Creating mls2.qobrix_silver_property_subtypes from bronze...")
spark.sql(transform_sql)

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_property_subtypes")
print(f"✅ qobrix_silver_property_subtypes: {silver_df.count()} rows, {len(silver_df.columns)} columns")
