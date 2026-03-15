#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_projects) -> Silver (qobrix_silver_projects)
#
# Purpose: Transform raw Qobrix projects from bronze into normalized silver
# per app_data_model.dbml. All columns gold needs are included; optional bronze cols use col_or_null.

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

bronze_table = f"{catalog}.{schema}.qobrix_api_projects"
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


def try_cast_or_null(col_name: str, cast_type: str, alias: str | None = None) -> str:
    alias = alias or col_name
    if has_col(col_name):
        return f"TRY_CAST(p.`{col_name}` AS {cast_type}) AS {alias}"
    return f"CAST(NULL AS {cast_type}) AS {alias}"


# Build SELECT expressions for qobrix_silver_projects (order per DBML)
select_parts = [
    col_or_null("id"),
    try_cast_or_null("ref", "INT"),
    trim_or_null("legacy_id"),
    trim_or_null("name"),
    trim_or_null("abbreviation"),
    trim_or_null("reference_code"),
    trim_or_null("type"),
    trim_or_null("housing_type"),
    trim_or_null("availability_status"),
    trim_or_null("description"),
    trim_or_null("short_description"),
    trim_or_null("amenities_description"),
    trim_or_null("location_description"),
    trim_or_null("map_popup_description"),
    col_or_null("developer_id"),
    col_or_null("assigned_to"),
    col_or_null("location"),
    trim_or_null("coordinates"),
    "UPPER(TRIM(p.`country`)) AS country" if has_col("country") else "NULL AS country",
    trim_or_null("state"),
    trim_or_null("city"),
    trim_or_null("municipality"),
    trim_or_null("post_code"),
    trim_or_null("street"),
    trim_or_null("street_2"),
    try_cast_or_null("completion_date", "DATE"),
    trim_or_null("construction_stage"),
    try_cast_or_null("number_of_units", "INT"),
    try_cast_or_null("starting_price_from", "DECIMAL(20,4)"),
    try_cast_or_null("price_to", "DECIMAL(20,4)"),
    try_cast_or_null("project_listing_priority", "INT"),
    trim_or_null("website_status"),
    "CASE WHEN p.website_url IS NULL OR TRIM(p.website_url) = '' THEN NULL "
    "WHEN LOWER(TRIM(p.website_url)) LIKE 'http%' THEN TRIM(p.website_url) "
    "ELSE CONCAT('https://', TRIM(p.website_url)) END AS website_url" if has_col("website_url") else "NULL AS website_url",
    try_cast_or_null("website_listing_date", "TIMESTAMP"),
    trim_or_null("video_link"),
    trim_or_null("video_links"),
    trim_or_null("virtual_tour_link"),
    trim_or_null("virtual_tour_links"),
    try_cast_or_null("last_media_update", "TIMESTAMP"),
    trim_or_null("views"),
    trim_or_null("further_features"),
    try_cast_or_null("distance_from_airport_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_beach_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_centre_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_hospital_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_rail_station_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_school_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_shops_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_tube_station_amount", "DECIMAL(20,4)"),
    try_cast_or_null("distance_from_university_amount", "DECIMAL(20,4)"),
    try_cast_or_null("featured", "BOOLEAN"),
    try_cast_or_null("featured_priority", "INT"),
    try_cast_or_null("custom_active", "BOOLEAN"),
    try_cast_or_null("custom_business_centre", "BOOLEAN"),
    try_cast_or_null("custom_concierge_services", "BOOLEAN"),
    try_cast_or_null("custom_delivery_date", "DATE"),
    try_cast_or_null("custom_gym", "BOOLEAN"),
    try_cast_or_null("custom_heated_pool", "BOOLEAN"),
    try_cast_or_null("custom_kids_play_area", "BOOLEAN"),
    try_cast_or_null("custom_list_selling_price_amount", "DECIMAL(20,4)"),
    try_cast_or_null("custom_reception", "BOOLEAN"),
    try_cast_or_null("custom_resale", "BOOLEAN"),
    try_cast_or_null("custom_restaurant_cafe", "BOOLEAN"),
    try_cast_or_null("custom_security_service", "BOOLEAN"),
    try_cast_or_null("custom_spa", "BOOLEAN"),
    try_cast_or_null("custom_tennis_court", "BOOLEAN"),
    try_cast_or_null("custom_valet_parking", "BOOLEAN"),
    try_cast_or_null("created", "TIMESTAMP"),
    col_or_null("created_by"),
    try_cast_or_null("modified", "TIMESTAMP"),
    col_or_null("modified_by"),
    try_cast_or_null("trashed", "TIMESTAMP"),
]
select_sql = ",\n    ".join(select_parts)

# COMMAND ----------

# Use full three-level name so table is created in sharp.mls2 (avoids TABLE_OR_VIEW_NOT_FOUND in gold)
silver_table_full = f"{catalog}.{schema}.qobrix_silver_projects"
transform_sql = f"""
CREATE OR REPLACE TABLE {silver_table_full} AS
SELECT
    {select_sql}
FROM {bronze_table} p
"""

print(f"Creating {silver_table_full} from bronze...")
spark.sql(transform_sql)

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_projects")
print(f"✅ qobrix_silver_projects: {silver_df.count()} rows, {len(silver_df.columns)} columns")
