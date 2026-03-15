#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_opportunities) -> Gold (common_leads)
#
# Purpose: One row per lead; dedup by id, keep latest modified.
# Gold column names: contact_profile_id, agent_id, owner_id (per app_data_model.dbml).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_opportunities"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by id (one row per opportunity); keep latest modified
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
dedup_df.createOrReplaceTempView("qobrix_silver_opportunities_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

# common_leads: subset of silver; contact_name -> contact_profile_id, agent -> agent_id, owner -> owner_id
print("Creating gold common.common_leads ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_leads AS
SELECT
    id                                       AS id,
    ref                                      AS ref,
    contact_name                             AS contact_profile_id,
    agent                                    AS agent_id,
    owner                                    AS owner_id,
    campaign_id                               AS campaign_id,
    created                                  AS created,
    created_by                               AS created_by,
    modified                                 AS modified,
    modified_by                              AS modified_by,
    enquiry_date                             AS enquiry_date,
    enquiry_type                             AS enquiry_type,
    status                                   AS status,
    last_status_change                       AS last_status_change,
    buy_rent                                 AS buy_rent,
    source                                   AS source,
    direct_source                            AS direct_source,
    source_description                       AS source_description,
    description                              AS description,
    website_url                              AS website_url,
    virtual_contact_name                      AS virtual_contact_name,
    notify_matching_properties               AS notify_matching_properties,
    notify_properties_price_drop             AS notify_properties_price_drop,
    next_follow_up_date                      AS next_follow_up_date,
    last_website_visit                       AS last_website_visit,
    closed_lost_reason_id                    AS closed_lost_reason_id,
    closed_lost_details                      AS closed_lost_details,
    custom_attended_webinar                  AS custom_attended_webinar,
    custom_do_not_contact                    AS custom_do_not_contact,
    custom_enquiry_low_budget                AS custom_enquiry_low_budget,
    custom_enquiry_stage_type                AS custom_enquiry_stage_type,
    custom_facebook_lead_id                 AS custom_facebook_lead_id,
    custom_general_interest_type             AS custom_general_interest_type,
    custom_interest_type                     AS custom_interest_type,
    custom_mql                               AS custom_mql,
    custom_project                           AS custom_project,
    custom_property                          AS custom_property,
    custom_sql                               AS custom_sql,
    custom_webinars                          AS custom_webinars
FROM qobrix_silver_opportunities_dedup
"""
)

gold_df = spark.table("common.common_leads")
print(f"✅ common.common_leads: {gold_df.count()} rows, {len(gold_df.columns)} columns")

# COMMAND ----------

# common_lead_enquiry_profiles: 1:1 with common_leads; property requirements (budget, location, size, features)
print("Creating gold common.common_lead_enquiry_profiles ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_lead_enquiry_profiles AS
SELECT
    id                                     AS lead_id,
    area_of_interest                        AS area_of_interest,
    post_codes                              AS post_codes,
    enquiry_subtypes                        AS enquiry_subtypes,
    town_planning_zone                      AS town_planning_zone,
    construction_stage                      AS construction_stage,
    sorting_expression                      AS sorting_expression,
    list_selling_price_from                 AS list_selling_price_from,
    list_selling_price_to                   AS list_selling_price_to,
    list_selling_price                      AS list_selling_price,
    list_rental_price_from                  AS list_rental_price_from,
    list_rental_price_to                     AS list_rental_price_to,
    list_letting_price                      AS list_letting_price,
    lowest_selling_price                    AS lowest_selling_price,
    lowest_letting_price                    AS lowest_letting_price,
    bedrooms_from                           AS bedrooms_from,
    bedrooms_to                            AS bedrooms_to,
    bathrooms_from                          AS bathrooms_from,
    bathrooms_to                            AS bathrooms_to,
    covered_area_from_amount                AS covered_area_from_amount,
    covered_area_to_amount                  AS covered_area_to_amount,
    internal_area_from_amount               AS internal_area_from_amount,
    internal_area_to_amount                 AS internal_area_to_amount,
    total_area_from_amount                  AS total_area_from_amount,
    total_area_to_amount                    AS total_area_to_amount,
    plot_area_from_amount                   AS plot_area_from_amount,
    plot_area_to_amount                     AS plot_area_to_amount,
    storage_from_amount                     AS storage_from_amount,
    storage_to_amount                      AS storage_to_amount,
    frontage_from_amount                    AS frontage_from_amount,
    frontage_to_amount                      AS frontage_to_amount,
    covered_parking                         AS covered_parking,
    parking_from                            AS parking_from,
    parking_to                              AS parking_to,
    furnished                               AS furnished,
    air_condition                           AS air_condition,
    common_swimming_pool                    AS common_swimming_pool,
    private_swimming_pool                  AS private_swimming_pool,
    concierge_reception                     AS concierge_reception,
    electricity                             AS electricity,
    water                                   AS water,
    elevator                                AS elevator,
    registered_road                         AS registered_road,
    title_deeds                             AS title_deeds,
    new_build                               AS new_build,
    pets_allowed                            AS pets_allowed,
    enclosed_office_room                    AS enclosed_office_room,
    server_room                             AS server_room,
    business_transfer_or_sale               AS business_transfer_or_sale,
    business_transfer_commercial_activity   AS business_transfer_commercial_activity,
    custom_internal_area_amount             AS custom_internal_area_amount
FROM qobrix_silver_opportunities_dedup
"""
)

enquiry_df = spark.table("common.common_lead_enquiry_profiles")
print(f"✅ common.common_lead_enquiry_profiles: {enquiry_df.count()} rows, {len(enquiry_df.columns)} columns")
