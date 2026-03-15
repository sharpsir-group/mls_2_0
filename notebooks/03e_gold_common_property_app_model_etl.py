#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Silver (qobrix_silver_properties) -> Gold (common_* property tables)
#
# Purpose:
# - Project the cleaned silver properties into the Common Data Layer tables
#   defined in app_data_model.dbml:
#     - common_properties
#     - common_property_profiles
#     - common_property_listing
# - This is a first pass: mostly 1:1 mapping from silver, no complex
#   business rules or deduplication yet.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Must match the catalog and schema used in 00b and 02e (e.g. sharp + mls2)
catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

print("Using catalog:", catalog, "schema:", schema)

# Silver table lives in sharp.mls2
silver_table = f"{catalog}.{schema}.qobrix_silver_properties"
silver_df = spark.table(silver_table)
print(f"Silver table {silver_table}: {silver_df.count()} rows, {len(silver_df.columns)} columns")

# Deduplicate: group by business key (ref, project, address) and keep latest modified
# Each expression must be a separate argument to selectExpr (no comma inside one string)
dedup_key_exprs = [
    "COALESCE(CAST(ref AS STRING), '') AS k_ref",
    "COALESCE(CAST(project AS STRING), '') AS k_project",
    "COALESCE(UPPER(TRIM(country)), '') AS k_country",
    "COALESCE(LOWER(TRIM(city)), '') AS k_city",
    "COALESCE(LOWER(TRIM(municipality)), '') AS k_municipality",
    "COALESCE(LOWER(TRIM(post_code)), '') AS k_post_code",
    "COALESCE(LOWER(TRIM(street)), '') AS k_street",
    "COALESCE(LOWER(TRIM(unit_number)), '') AS k_unit_number",
]

dedup_df = (
    silver_df
    .selectExpr("*", *dedup_key_exprs)
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy(
                "k_ref",
                "k_project",
                "k_country",
                "k_city",
                "k_municipality",
                "k_post_code",
                "k_street",
                "k_unit_number",
            ).orderBy(F.col("modified").desc_nulls_last(), F.col("created").desc_nulls_last())
        ),
    )
    .filter(F.col("_rn") == 1)
    .drop("_rn", "k_ref", "k_project", "k_country", "k_city", "k_municipality", "k_post_code", "k_street", "k_unit_number")
)

dedup_df.createOrReplaceTempView("qobrix_silver_properties_dedup")

print(f"After deduplication: {dedup_df.count()} rows remain")

# COMMAND ----------

print("Creating gold.common_properties ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_properties AS
SELECT
    -- PK / identity (1:1 with silver property id)
    id                                         AS id,
    ref                                        AS ref,

    -- Status / type
    status                                    AS status,
    sale_rent                                 AS sale_rent,
    property_type                             AS property_type,
    property_subtype                          AS property_subtype,
    website_status                            AS website_status,

    -- Dates
    listing_date                              AS listing_date,
    created                                   AS created,
    modified                                  AS modified,

    -- Assignment / relationships
    CAST(NULL AS STRING)                        AS created_by,      -- to be populated from common_users later
    CAST(NULL AS STRING)                        AS modified_by,     -- to be populated from common_users later
    agent                                     AS agent_id,        -- will point to common_users.id once populated
    salesperson                               AS salesperson_id,  -- will point to common_users.id once populated
    seller                                    AS seller_id,       -- will point to common_contact_profiles.id
    developer_id                              AS developer_id,
    project                                   AS project_id,      -- will point to common_projects.id
    group_id                                  AS group_id,
    campaign_id                               AS campaign_id

FROM qobrix_silver_properties_dedup
"""
)

gold_props = spark.table("common.common_properties")
print(f"✅ common.common_properties: {gold_props.count()} rows, {len(gold_props.columns)} columns")

# COMMAND ----------

print("Creating gold.common_property_profiles ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_profiles AS
SELECT
    -- 1:1 with common_properties.id
    id                                       AS property_id,

    -- Location
    coordinates                              AS coordinates,
    CAST(NULL AS STRING)                     AS geocode_type,
    country                                  AS country,
    state                                    AS state,
    city                                     AS city,
    municipality                             AS municipality,
    post_code                                AS post_code,
    street                                   AS street,
    town_planning_zone                       AS town_planning_zone,
    cadastral_reference                      AS cadastral_reference,
    land_locked                              AS land_locked,
    right_of_way                             AS right_of_way,
    registered_road                          AS registered_road,
    corner_plot                              AS corner_plot,

    -- Areas / sizes
    internal_area_amount                     AS internal_area_amount,
    covered_area_amount                      AS covered_area_amount,
    uncovered_area_amount                    AS uncovered_area_amount,
    total_area_amount                        AS total_area_amount,
    plot_area_amount                         AS plot_area_amount,
    roof_garden_area_amount                  AS roof_garden_area_amount,
    garden_area_amount                       AS garden_area_amount,
    mezzanine_amount                         AS mezzanine_amount,
    storage_amount                           AS storage_amount,
    covered_verandas_amount                  AS covered_verandas_amount,
    uncovered_verandas_amount                AS uncovered_verandas_amount,
    frontage_amount                          AS frontage_amount,

    -- Rooms
    bedrooms                                 AS bedrooms,
    bathrooms                                AS bathrooms,
    wc_bathrooms                             AS wc_bathrooms,
    living_rooms                             AS living_rooms,
    kitchens                                 AS kitchens,
    office_spaces                            AS office_spaces,
    verandas                                 AS verandas,
    floors_building                          AS floors_building,
    floor_number                             AS floor_number,
    storeys_max_floor                        AS storeys_max_floor,
    height                                   AS height,
    unit_number                              AS unit_number,
    floor_type                               AS floor_type,

    -- Pricing
    list_selling_price_amount                AS list_selling_price_amount,
    list_selling_price_modified              AS list_selling_price_modified,
    list_rental_price_amount                 AS list_rental_price_amount,
    list_rental_price_modified               AS list_rental_price_modified,
    rent_frequency                           AS rent_frequency,
    price_per_square                         AS price_per_square,
    price_qualifier                          AS price_qualifier,
    plus_vat                                 AS plus_vat,
    previous_list_selling_price              AS previous_list_selling_price,
    previous_list_rental_price               AS previous_list_rental_price,
    reserve_price_amount                     AS reserve_price_amount,
    starting_bidding_amount                  AS starting_bidding_amount,
    minimum_tenancy                          AS minimum_tenancy,
    tenancy_type                             AS tenancy_type,
    occupancy                                AS occupancy,
    engagement_letter_date                   AS engagement_letter_date,
    inspection_date                          AS inspection_date,
    auction_start_date                       AS auction_start_date,
    auction_end_date                         AS auction_end_date,

    -- Construction / energy
    construction_year                        AS construction_year,
    renovation_year                          AS renovation_year,
    construction_type                        AS construction_type,
    construction_stage                       AS construction_stage,
    energy_efficiency_grade                  AS energy_efficiency_grade,
    energy_consumption_rating                AS energy_consumption_rating,
    energy_consumption_value                 AS energy_consumption_value,
    energy_emission_rating                   AS energy_emission_rating,
    energy_emission_value                    AS energy_emission_value,

    -- Utilities / features (booleans)
    electricity                              AS electricity,
    electricity_type                         AS electricity_type,
    water                                    AS water,
    heating_type                             AS heating_type,
    heating_medium                           AS heating_medium,
    cooling_type                             AS cooling_type,
    furnished                                AS furnished,
    pets_allowed                             AS pets_allowed,
    fireplace                                AS fireplace,
    sea_view                                 AS sea_view,
    mountain_view                            AS mountain_view,
    beach_front                              AS beach_front,
    abuts_green_area                         AS abuts_green_area,
    private_swimming_pool                    AS private_swimming_pool,
    common_swimming_pool                     AS common_swimming_pool,
    air_condition                            AS air_condition,
    alarm                                    AS alarm,
    smart_home                               AS smart_home,
    solar_water_heater                       AS solar_water_heater,
    storage_space                            AS storage_space,
    maids_room                               AS maids_room,
    concierge_reception                      AS concierge_reception,
    secure_door                              AS secure_door,
    kitchenette                              AS kitchenette,
    home_office                              AS home_office,
    separate_laundry_room                    AS separate_laundry_room,
    reception                                AS reception,
    store_room                               AS store_room,
    enclosed_office_room                     AS enclosed_office_room,
    server_room                              AS server_room,
    business_transfer_or_sale                AS business_transfer_or_sale,

    -- Parking / distances
    covered_parking                          AS covered_parking,
    uncovered_parking                        AS uncovered_parking,
    parking                                  AS parking,
    customer_parking                         AS customer_parking,
    elevator                                 AS elevator,
    distance_from_airport                    AS distance_from_airport,
    distance_from_beach                      AS distance_from_beach,
    distance_from_centre                     AS distance_from_centre,
    distance_from_hospital                   AS distance_from_hospital,
    distance_from_rail_station               AS distance_from_rail_station,
    distance_from_school                     AS distance_from_school,
    distance_from_shops                      AS distance_from_shops,
    distance_from_tube_station               AS distance_from_tube_station,
    distance_from_university                 AS distance_from_university,

    -- Type slices
    apartment_type                           AS apartment_type,
    building_type                            AS building_type,
    hotel_type                               AS hotel_type,
    house_type                               AS house_type,
    industrial_type                          AS industrial_type,
    land_type                                AS land_type,
    office_type                              AS office_type,
    retail_type                              AS retail_type

FROM qobrix_silver_properties_dedup
"""
)

gold_profiles = spark.table("common.common_property_profiles")
print(f"✅ common.common_property_profiles: {gold_profiles.count()} rows, {len(gold_profiles.columns)} columns")

# COMMAND ----------

print("Creating gold.common_property_listing ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_listing AS
SELECT
    -- 1:1 with common_properties.id
    id                                       AS property_id,

    -- Listing identity / descriptions
    name                                     AS name,
    short_description                        AS short_description,
    description                              AS description,

    -- Web / media
    website_url                              AS website_url,
    original_website_url                     AS original_website_url,
    website_listing_date                     AS website_listing_date,
    video_link                               AS video_link,
    virtual_tour_link                        AS virtual_tour_link,
    ideal_for                                AS ideal_for,
    licensed_for                             AS licensed_for,
    key_holder_details                       AS key_holder_details,

    -- Feature/flag fields (not in current silver; use NULL until added to 02e)
    CAST(NULL AS BOOLEAN)                    AS featured,
    CAST(NULL AS INT)                        AS featured_priority,
    CAST(NULL AS BOOLEAN)                    AS property_of_the_month,
    CAST(NULL AS TIMESTAMP)                  AS last_media_update,
    CAST(NULL AS BOOLEAN)                    AS inherit_project_media,

    -- Extra marketing attributes (not in current silver)
    CAST(NULL AS STRING)                     AS kitchen_type,
    CAST(NULL AS STRING)                     AS office_layout,
    original_name                            AS original_name,
    original_ref                             AS original_ref

FROM qobrix_silver_properties_dedup
"""
)

gold_listing = spark.table("common.common_property_listing")
print(f"✅ common.common_property_listing: {gold_listing.count()} rows, {len(gold_listing.columns)} columns")

# COMMAND ----------

print("Creating gold.common_property_bazaraki ...")

spark.sql(
    """
CREATE OR REPLACE TABLE common.common_property_bazaraki AS
SELECT
    id                                       AS property_id,
    custom_bazaraki_negotiable_price         AS custom_bazaraki_negotiable_price,
    custom_bazaraki_exchange                 AS custom_bazaraki_exchange,
    custom_bazaraki_registration_block       AS custom_bazaraki_registration_block,
    custom_bazaraki_chosen_phone             AS custom_bazaraki_chosen_phone,
    custom_bazaraki_registration_number      AS custom_bazaraki_registration_number,
    custom_bazaraki_online_viewing           AS custom_bazaraki_online_viewing,
    custom_bazaraki_url                      AS custom_bazaraki_url,
    custom_bazaraki_location                 AS custom_bazaraki_location,
    custom_bazaraki_disallow_chat            AS custom_bazaraki_disallow_chat,
    custom_bazaraki_phone_hide               AS custom_bazaraki_phone_hide
FROM qobrix_silver_properties_dedup
"""
)

gold_bazaraki = spark.table("common.common_property_bazaraki")
print(f"✅ common.common_property_bazaraki: {gold_bazaraki.count()} rows, {len(gold_bazaraki.columns)} columns")

