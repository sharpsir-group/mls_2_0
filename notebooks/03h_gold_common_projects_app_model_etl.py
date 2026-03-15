#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_projects) -> Gold (common_projects)
#
# Purpose: One row per project; dedup by ref, keep latest modified.
# Gold is a subset of silver columns per app_data_model.dbml (common_projects).

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

silver_table = f"{catalog}.{schema}.qobrix_silver_projects"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# COMMAND ----------

# Dedup by ref (one row per project ref; keep latest modified)
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
dedup_df.createOrReplaceTempView("qobrix_silver_projects_dedup")
print(f"After deduplication: {dedup_df.count()} rows")

# COMMAND ----------

# common_projects: subset of silver columns (no location/address, no video/distance/custom_* except a few)
print("Creating gold common.common_projects ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_projects AS
SELECT
    id                                       AS id,
    ref                                      AS ref,
    name                                     AS name,
    abbreviation                             AS abbreviation,
    reference_code                           AS reference_code,
    type                                     AS type,
    housing_type                             AS housing_type,
    availability_status                      AS availability_status,
    description                              AS description,
    short_description                        AS short_description,
    amenities_description                    AS amenities_description,
    developer_id                             AS developer_id,
    assigned_to                              AS assigned_to,
    number_of_units                          AS number_of_units,
    starting_price_from                      AS starting_price_from,
    price_to                                 AS price_to,
    project_listing_priority                 AS project_listing_priority,
    website_status                           AS website_status,
    website_url                              AS website_url,
    website_listing_date                     AS website_listing_date,
    featured                                 AS featured,
    featured_priority                        AS featured_priority,
    custom_active                            AS custom_active,
    custom_list_selling_price_amount         AS custom_list_selling_price_amount,
    custom_resale                            AS custom_resale,
    created                                  AS created,
    created_by                               AS created_by,
    modified                                 AS modified,
    modified_by                              AS modified_by
FROM qobrix_silver_projects_dedup
"""
)

gold_df = spark.table("common.common_projects")
print(f"✅ common.common_projects: {gold_df.count()} rows, {len(gold_df.columns)} columns")

# COMMAND ----------

# common_project_profiles: 1:1 with common_projects; location, distances, video, amenities (per DBML)
print("Creating gold common.common_project_profiles ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_project_profiles AS
SELECT
    id                                     AS project_id,
    location                               AS location,
    coordinates                            AS coordinates,
    country                                AS country,
    state                                  AS state,
    city                                   AS city,
    municipality                           AS municipality,
    post_code                              AS post_code,
    street                                 AS street,
    street_2                               AS street_2,
    completion_date                        AS completion_date,
    construction_stage                     AS construction_stage,
    distance_from_airport_amount           AS distance_from_airport_amount,
    distance_from_beach_amount            AS distance_from_beach_amount,
    distance_from_centre_amount           AS distance_from_centre_amount,
    distance_from_hospital_amount         AS distance_from_hospital_amount,
    distance_from_rail_station_amount     AS distance_from_rail_station_amount,
    distance_from_school_amount           AS distance_from_school_amount,
    distance_from_shops_amount            AS distance_from_shops_amount,
    distance_from_tube_station_amount     AS distance_from_tube_station_amount,
    distance_from_university_amount      AS distance_from_university_amount,
    video_link                            AS video_link,
    video_links                            AS video_links,
    virtual_tour_link                      AS virtual_tour_link,
    virtual_tour_links                     AS virtual_tour_links,
    last_media_update                      AS last_media_update,
    views                                  AS views,
    further_features                       AS further_features,
    custom_business_centre                 AS custom_business_centre,
    custom_concierge_services             AS custom_concierge_services,
    custom_delivery_date                   AS custom_delivery_date,
    custom_gym                             AS custom_gym,
    custom_heated_pool                     AS custom_heated_pool,
    custom_kids_play_area                  AS custom_kids_play_area,
    custom_reception                       AS custom_reception,
    custom_restaurant_cafe                 AS custom_restaurant_cafe,
    custom_security_service                AS custom_security_service,
    custom_spa                             AS custom_spa,
    custom_tennis_court                    AS custom_tennis_court,
    custom_valet_parking                   AS custom_valet_parking
FROM qobrix_silver_projects_dedup
"""
)

profiles_df = spark.table("common.common_project_profiles")
print(f"✅ common.common_project_profiles: {profiles_df.count()} rows, {len(profiles_df.columns)} columns")
