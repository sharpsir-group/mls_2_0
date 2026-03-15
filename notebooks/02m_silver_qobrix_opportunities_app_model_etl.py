#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_opportunities) -> Silver (qobrix_silver_opportunities)
#
# Purpose: Transform opportunities/leads from bronze into normalized silver per app_data_model.dbml.
# Many columns; optional bronze cols use col_or_null/try_cast_or_null.

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

print("Using catalog:", catalog, "schema:", schema)

# COMMAND ----------

bronze_table = f"{catalog}.{schema}.qobrix_api_opportunities"
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


# COMMAND ----------

# Column definitions: (name, 'uuid'|'str'|'int'|'decimal'|'date'|'timestamp'|'boolean')
# Order matches qobrix_silver_opportunities in DBML
_COLUMNS = [
    ("id", "uuid"),
    ("ref", "int"),
    ("contact_name", "uuid"),
    ("agent", "uuid"),
    ("owner", "uuid"),
    ("campaign_id", "uuid"),
    ("created", "timestamp"),
    ("created_by", "uuid"),
    ("modified", "timestamp"),
    ("modified_by", "uuid"),
    ("enquiry_date", "date"),
    ("enquiry_type", "str"),
    ("status", "str"),
    ("last_status_change", "timestamp"),
    ("buy_rent", "str"),
    ("source", "str"),
    ("direct_source", "str"),
    ("source_description", "str"),
    ("description", "str"),
    ("legacy_id", "str"),
    ("website_url", "str"),
    ("virtual_contact_name", "str"),
    ("area_of_interest", "str"),
    ("post_codes", "str"),
    ("enquiry_subtypes", "str"),
    ("town_planning_zone", "str"),
    ("construction_stage", "str"),
    ("sorting_expression", "str"),
    ("list_selling_price_from", "decimal"),
    ("list_selling_price_to", "decimal"),
    ("list_selling_price", "decimal"),
    ("list_rental_price_from", "decimal"),
    ("list_rental_price_to", "decimal"),
    ("list_letting_price", "decimal"),
    ("lowest_selling_price", "decimal"),
    ("lowest_letting_price", "decimal"),
    ("bedrooms_from", "int"),
    ("bedrooms_to", "int"),
    ("bathrooms_from", "int"),
    ("bathrooms_to", "int"),
    ("covered_area_from_amount", "decimal"),
    ("covered_area_to_amount", "decimal"),
    ("internal_area_from_amount", "decimal"),
    ("internal_area_to_amount", "decimal"),
    ("total_area_from_amount", "decimal"),
    ("total_area_to_amount", "decimal"),
    ("plot_area_from_amount", "decimal"),
    ("plot_area_to_amount", "decimal"),
    ("storage_from_amount", "decimal"),
    ("storage_to_amount", "decimal"),
    ("frontage_from_amount", "decimal"),
    ("frontage_to_amount", "decimal"),
    ("covered_parking", "int"),
    ("parking_from", "int"),
    ("parking_to", "int"),
    ("furnished", "str"),
    ("air_condition", "boolean"),
    ("common_swimming_pool", "boolean"),
    ("private_swimming_pool", "boolean"),
    ("concierge_reception", "boolean"),
    ("electricity", "boolean"),
    ("water", "boolean"),
    ("elevator", "boolean"),
    ("registered_road", "boolean"),
    ("title_deeds", "boolean"),
    ("new_build", "boolean"),
    ("pets_allowed", "boolean"),
    ("enclosed_office_room", "boolean"),
    ("server_room", "boolean"),
    ("business_transfer_or_sale", "boolean"),
    ("business_transfer_commercial_activity", "str"),
    ("notify_matching_properties", "boolean"),
    ("notify_properties_price_drop", "boolean"),
    ("next_follow_up_date", "timestamp"),
    ("last_website_visit", "timestamp"),
    ("closed_lost_reason_id", "uuid"),
    ("closed_lost_details", "str"),
    ("trashed", "timestamp"),
    ("custom_attended_webinar", "boolean"),
    ("custom_do_not_contact", "boolean"),
    ("custom_enquiry_low_budget", "boolean"),
    ("custom_enquiry_stage_type", "str"),
    ("custom_facebook_lead_id", "str"),
    ("custom_general_interest_type", "str"),
    ("custom_interest_type", "str"),
    ("custom_internal_area_amount", "decimal"),
    ("custom_mql", "boolean"),
    ("custom_project", "uuid"),
    ("custom_property", "uuid"),
    ("custom_sql", "boolean"),
    ("custom_webinars", "str"),
]


def expr_for(col_name: str, kind: str) -> str:
    if kind == "uuid":
        return col_or_null(col_name)
    if kind == "str":
        if col_name == "website_url":
            return (
                "CASE WHEN p.website_url IS NULL OR TRIM(p.website_url) = '' THEN NULL "
                "WHEN LOWER(TRIM(p.website_url)) LIKE 'http%' THEN TRIM(p.website_url) "
                "ELSE CONCAT('https://', TRIM(p.website_url)) END AS website_url"
                if has_col("website_url")
                else "NULL AS website_url"
            )
        return trim_or_null(col_name)
    if kind == "int":
        return try_cast_or_null(col_name, "INT")
    if kind == "decimal":
        return try_cast_or_null(col_name, "DECIMAL(20,4)")
    if kind == "date":
        return try_cast_or_null(col_name, "DATE")
    if kind == "timestamp":
        return try_cast_or_null(col_name, "TIMESTAMP")
    if kind == "boolean":
        return try_cast_or_null(col_name, "BOOLEAN")
    return col_or_null(col_name)


select_parts = [expr_for(name, kind) for name, kind in _COLUMNS]
select_sql = ",\n    ".join(select_parts)

# COMMAND ----------

transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_opportunities AS
SELECT
    {select_sql}
FROM {bronze_table} p
"""

print("Creating mls2.qobrix_silver_opportunities from bronze...")
spark.sql(transform_sql)

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_opportunities")
print(f"✅ qobrix_silver_opportunities: {silver_df.count()} rows, {len(silver_df.columns)} columns")
