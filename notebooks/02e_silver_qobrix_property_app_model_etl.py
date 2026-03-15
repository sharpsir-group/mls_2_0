#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Bronze (qobrix_api_properties) -> Silver (qobrix_silver_properties)
#
# Purpose:
# - Transform raw Qobrix API property payloads from bronze table qobrix_bronze.qobrix_api_properties
#   into a cleaner, typed silver table qobrix_silver.qobrix_silver_properties that follows app_data_model.dbml.
# - This is a first version focusing on the most important fields (ids, status, types, location,
#   beds/baths, areas, prices, key flags). We can extend it column by column later.

# COMMAND ----------

import os

from pyspark.sql import functions as F

# Must match the catalog and schema used in 00b (e.g. sharp + mls2 in your workspace)
catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS mls2")
spark.sql(f"USE SCHEMA {schema}")

print("Using catalog:", catalog, "schema:", schema)

# COMMAND ----------

print("Inspecting bronze qobrix_api_properties columns...")
# Bronze tables live in sharp.mls2 (same schema as 00b)
bronze_table = f"{catalog}.{schema}.qobrix_api_properties"
bronze_df = spark.table(bronze_table)
bronze_cols = set(c.lower() for c in bronze_df.columns)
print(f"Bronze table {bronze_table} has {len(bronze_cols)} columns")


def has_col(col_name: str) -> bool:
    return col_name.lower() in bronze_cols


def col_or_null(col_name: str, alias: str | None = None) -> str:
    """
    Helper for dynamic SQL: return 'p.col AS alias' if exists in bronze,
    otherwise 'NULL AS alias'.
    """
    alias = alias or col_name
    if has_col(col_name):
        return f"p.`{col_name}` AS {alias}"
    return f"NULL AS {alias}"


# COMMAND ----------

# Build SQL for silver table.
# We keep it readable and limited to high-value fields for now.
# Normalizations here are "technical" (trim, lowercase, URL cleaning) – business
# mappings and deduplication will be done in the Gold layer.

transform_sql = f"""
CREATE OR REPLACE TABLE mls2.qobrix_silver_properties AS
SELECT
    -- Identifiers / relations
    {col_or_null('id')},
    {col_or_null('ref')},
    {col_or_null('legacy_id')},
    {col_or_null('original_ref')},
    {col_or_null('original_name')},
    {col_or_null('name')},
    {col_or_null('project')},
    {col_or_null('seller')},
    {col_or_null('agent')},
    {col_or_null('salesperson')},
    {col_or_null('campaign_id')},
    {col_or_null('group_id')},
    {col_or_null('developer_id')},
    {col_or_null('location')},

    -- Status / type
    TRIM(p.source)                                           AS source,
    TRIM(p.direct_sources)                                   AS direct_sources,
    TRIM(p.source_description)                               AS source_description,
    CASE
        WHEN p.status IS NULL OR TRIM(p.status) = '' THEN NULL
        ELSE LOWER(TRIM(p.status))
    END                                                      AS status,
    CASE
        WHEN p.sale_rent IS NULL OR TRIM(p.sale_rent) = '' THEN NULL
        ELSE LOWER(TRIM(p.sale_rent))
    END                                                      AS sale_rent,
    CASE
        WHEN p.property_type IS NULL OR TRIM(p.property_type) = '' THEN NULL
        ELSE LOWER(TRIM(p.property_type))
    END                                                      AS property_type,
    CASE
        WHEN p.property_subtype IS NULL OR TRIM(p.property_subtype) = '' THEN NULL
        ELSE LOWER(TRIM(p.property_subtype))
    END                                                      AS property_subtype,
    CASE
        WHEN p.website_status IS NULL OR TRIM(p.website_status) = '' THEN NULL
        ELSE LOWER(TRIM(p.website_status))
    END                                                      AS website_status,

    -- Text / marketing
    TRIM(p.short_description)                                AS short_description,
    TRIM(p.description)                                      AS description,
    CASE
        WHEN p.website_url IS NULL OR TRIM(p.website_url) = '' THEN NULL
        WHEN LOWER(TRIM(p.website_url)) LIKE 'http%' THEN TRIM(p.website_url)
        ELSE CONCAT('https://', TRIM(p.website_url))
    END                                                      AS website_url,
    CASE
        WHEN p.original_website_url IS NULL OR TRIM(p.original_website_url) = '' THEN NULL
        WHEN LOWER(TRIM(p.original_website_url)) LIKE 'http%' THEN TRIM(p.original_website_url)
        ELSE CONCAT('https://', TRIM(p.original_website_url))
    END                                                      AS original_website_url,
    TRIM(p.video_link)                                       AS video_link,
    TRIM(p.virtual_tour_link)                                AS virtual_tour_link,
    {col_or_null('ideal_for')},
    {col_or_null('licensed_for')},
    {col_or_null('key_holder_details')},

    -- Dates
    TRY_CAST(p.created AS TIMESTAMP)              AS created,
    TRY_CAST(p.modified AS TIMESTAMP)             AS modified,
    TRY_CAST(p.website_listing_date AS TIMESTAMP) AS website_listing_date,
    TRY_CAST(p.listing_date AS DATE)              AS listing_date,
    TRY_CAST(p.trashed AS TIMESTAMP)              AS trashed,
    TRY_CAST(p.engagement_letter_date AS TIMESTAMP) AS engagement_letter_date,
    TRY_CAST(p.inspection_date AS TIMESTAMP)        AS inspection_date,
    TRY_CAST(p.auction_start_date AS TIMESTAMP)     AS auction_start_date,
    TRY_CAST(p.auction_end_date AS TIMESTAMP)       AS auction_end_date,

    -- Location fields
    TRIM(p.coordinates)                                     AS coordinates,
    {col_or_null('geocode_type')},
    UPPER(TRIM(p.country))                                  AS country,
    TRIM(p.state)                                           AS state,
    TRIM(p.city)                                            AS city,
    TRIM(p.municipality)                                    AS municipality,
    TRIM(p.post_code)                                       AS post_code,
    TRIM(p.street)                                          AS street,
    LOWER(TRIM(p.town_planning_zone))                       AS town_planning_zone,
    TRIM(p.cadastral_reference)                             AS cadastral_reference,
    TRY_CAST(p.land_locked AS BOOLEAN)   AS land_locked,
    TRY_CAST(p.right_of_way AS BOOLEAN)  AS right_of_way,
    TRY_CAST(p.registered_road AS BOOLEAN) AS registered_road,
    TRY_CAST(p.corner_plot AS BOOLEAN)   AS corner_plot,

    -- Areas / sizes
    TRY_CAST(p.internal_area_amount AS DECIMAL(18,2))       AS internal_area_amount,
    TRY_CAST(p.covered_area_amount AS DECIMAL(18,2))        AS covered_area_amount,
    TRY_CAST(p.uncovered_area_amount AS DECIMAL(18,2))      AS uncovered_area_amount,
    TRY_CAST(p.total_area_amount AS DECIMAL(18,2))          AS total_area_amount,
    TRY_CAST(p.plot_area_amount AS DECIMAL(18,2))           AS plot_area_amount,
    TRY_CAST(p.roof_garden_area_amount AS DECIMAL(18,2))    AS roof_garden_area_amount,
    TRY_CAST(p.garden_area_amount AS DECIMAL(18,2))         AS garden_area_amount,
    TRY_CAST(p.mezzanine_amount AS DECIMAL(18,2))           AS mezzanine_amount,
    TRY_CAST(p.storage_amount AS DECIMAL(18,2))             AS storage_amount,
    TRY_CAST(p.covered_verandas_amount AS DECIMAL(18,2))    AS covered_verandas_amount,
    TRY_CAST(p.uncovered_verandas_amount AS DECIMAL(18,2))  AS uncovered_verandas_amount,
    TRY_CAST(p.frontage_amount AS DECIMAL(18,2))            AS frontage_amount,
    TRY_CAST(p.building_density AS DECIMAL(18,4))           AS building_density,
    TRY_CAST(p.cover_factor AS DECIMAL(18,4))               AS cover_factor,
    TRY_CAST(p.coverage AS DECIMAL(18,4))                   AS coverage,
    TRY_CAST(p.elevated_area AS BOOLEAN)                    AS elevated_area,

    -- Rooms
    TRY_CAST(p.bedrooms AS INT)         AS bedrooms,
    TRY_CAST(p.bathrooms AS INT)        AS bathrooms,
    TRY_CAST(p.wc_bathrooms AS INT)     AS wc_bathrooms,
    TRY_CAST(p.living_rooms AS INT)     AS living_rooms,
    TRY_CAST(p.kitchens AS INT)         AS kitchens,
    TRY_CAST(p.office_spaces AS INT)    AS office_spaces,
    TRY_CAST(p.verandas AS INT)         AS verandas,
    TRY_CAST(p.floors_building AS INT)  AS floors_building,
    TRY_CAST(p.floor_number AS INT)     AS floor_number,
    TRY_CAST(p.storeys_max_floor AS INT) AS storeys_max_floor,
    TRY_CAST(p.height AS DECIMAL(18,2)) AS height,
    {col_or_null('unit_number')},
    {col_or_null('floor_type')},

    -- Pricing
    TRY_CAST(p.list_selling_price_amount AS DECIMAL(18,2)) AS list_selling_price_amount,
    TRY_CAST(p.list_rental_price_amount  AS DECIMAL(18,2)) AS list_rental_price_amount,
    TRY_CAST(p.price_per_square          AS DECIMAL(18,4)) AS price_per_square,
    CASE
        WHEN p.rent_frequency IS NULL OR TRIM(p.rent_frequency) = '' THEN NULL
        ELSE LOWER(TRIM(p.rent_frequency))
    END                                                      AS rent_frequency,
    CASE
        WHEN p.price_qualifier IS NULL OR TRIM(p.price_qualifier) = '' THEN NULL
        ELSE LOWER(TRIM(p.price_qualifier))
    END                                                      AS price_qualifier,
    TRY_CAST(p.plus_vat AS BOOLEAN)                         AS plus_vat,
    TRY_CAST(p.previous_list_selling_price AS DECIMAL(18,2)) AS previous_list_selling_price,
    TRY_CAST(p.previous_list_rental_price  AS DECIMAL(18,2)) AS previous_list_rental_price,
    TRY_CAST(p.reserve_price_amount        AS DECIMAL(18,2)) AS reserve_price_amount,
    TRY_CAST(p.starting_bidding_amount     AS DECIMAL(18,2)) AS starting_bidding_amount,
    TRY_CAST(p.business_transfer_price     AS DECIMAL(18,2)) AS business_transfer_price,
    TRY_CAST(p.price_field_amount          AS DECIMAL(18,2)) AS price_field_amount,
    TRY_CAST(p.minimum_tenancy AS INT)                      AS minimum_tenancy,
    {col_or_null('tenancy_type')},
    {col_or_null('occupancy')},
    TRY_CAST(p.list_selling_price_modified AS TIMESTAMP)    AS list_selling_price_modified,
    TRY_CAST(p.list_rental_price_modified  AS TIMESTAMP)    AS list_rental_price_modified,

    -- Construction / energy
    TRY_CAST(p.construction_year AS INT)            AS construction_year,
    TRY_CAST(p.renovation_year AS INT)              AS renovation_year,
    LOWER(TRIM(p.construction_type))               AS construction_type,
    LOWER(TRIM(p.construction_stage))              AS construction_stage,
    LOWER(TRIM(p.energy_efficiency_grade))         AS energy_efficiency_grade,
    LOWER(TRIM(p.energy_consumption_rating))       AS energy_consumption_rating,
    TRY_CAST(p.energy_consumption_value AS DECIMAL(18,4)) AS energy_consumption_value,
    LOWER(TRIM(p.energy_emission_rating))          AS energy_emission_rating,
    TRY_CAST(p.energy_emission_value AS DECIMAL(18,4))    AS energy_emission_value,

    -- Utilities / features (a subset for now)
    TRY_CAST(p.electricity AS BOOLEAN)        AS electricity,
    LOWER(TRIM(p.electricity_type))           AS electricity_type,
    TRY_CAST(p.water AS BOOLEAN)             AS water,
    LOWER(TRIM(p.heating_type))              AS heating_type,
    LOWER(TRIM(p.heating_medium))            AS heating_medium,
    LOWER(TRIM(p.cooling_type))              AS cooling_type,
    {col_or_null('heating')},
    {col_or_null('cooling')},
    {col_or_null('furnished')},
    TRY_CAST(p.pets_allowed AS BOOLEAN)      AS pets_allowed,
    TRY_CAST(p.fireplace AS BOOLEAN)         AS fireplace,
    TRY_CAST(p.sea_view AS BOOLEAN)          AS sea_view,
    TRY_CAST(p.mountain_view AS BOOLEAN)     AS mountain_view,
    TRY_CAST(p.beach_front AS BOOLEAN)       AS beach_front,
    TRY_CAST(p.abuts_green_area AS BOOLEAN)  AS abuts_green_area,
    TRY_CAST(p.private_swimming_pool AS BOOLEAN) AS private_swimming_pool,
    TRY_CAST(p.common_swimming_pool AS BOOLEAN)  AS common_swimming_pool,
    TRY_CAST(p.air_condition AS BOOLEAN)         AS air_condition,
    TRY_CAST(p.alarm AS BOOLEAN)                 AS alarm,
    TRY_CAST(p.smart_home AS BOOLEAN)            AS smart_home,
    TRY_CAST(p.solar_water_heater AS BOOLEAN)    AS solar_water_heater,
    TRY_CAST(p.storage_space AS BOOLEAN)         AS storage_space,
    TRY_CAST(p.maids_room AS BOOLEAN)            AS maids_room,
    TRY_CAST(p.concierge_reception AS BOOLEAN)   AS concierge_reception,
    TRY_CAST(p.secure_door AS BOOLEAN)           AS secure_door,
    TRY_CAST(p.kitchenette AS BOOLEAN)           AS kitchenette,
    TRY_CAST(p.home_office AS BOOLEAN)           AS home_office,
    TRY_CAST(p.separate_laundry_room AS BOOLEAN) AS separate_laundry_room,
    TRY_CAST(p.reception AS BOOLEAN)             AS reception,
    TRY_CAST(p.store_room AS BOOLEAN)            AS store_room,
    TRY_CAST(p.enclosed_office_room AS BOOLEAN)  AS enclosed_office_room,
    TRY_CAST(p.server_room AS BOOLEAN)           AS server_room,
    TRY_CAST(p.business_transfer_or_sale AS BOOLEAN) AS business_transfer_or_sale,

    -- Parking / distances
    TRY_CAST(p.covered_parking AS INT)     AS covered_parking,
    TRY_CAST(p.uncovered_parking AS INT)   AS uncovered_parking,
    TRY_CAST(p.parking AS INT)            AS parking,
    TRY_CAST(p.customer_parking AS INT)    AS customer_parking,
    TRY_CAST(p.elevator AS BOOLEAN)        AS elevator,
    TRY_CAST(p.distance_from_airport AS DECIMAL(18,2))     AS distance_from_airport,
    TRY_CAST(p.distance_from_beach AS DECIMAL(18,2))       AS distance_from_beach,
    TRY_CAST(p.distance_from_centre AS DECIMAL(18,2))      AS distance_from_centre,
    TRY_CAST(p.distance_from_hospital AS DECIMAL(18,2))    AS distance_from_hospital,
    TRY_CAST(p.distance_from_rail_station AS DECIMAL(18,2)) AS distance_from_rail_station,
    TRY_CAST(p.distance_from_school AS DECIMAL(18,2))      AS distance_from_school,
    TRY_CAST(p.distance_from_shops AS DECIMAL(18,2))       AS distance_from_shops,
    TRY_CAST(p.distance_from_tube_station AS DECIMAL(18,2)) AS distance_from_tube_station,
    TRY_CAST(p.distance_from_university AS DECIMAL(18,2))  AS distance_from_university,

    -- JSON array fields (kept as-is for now)
    {col_or_null('view')},
    {col_or_null('pool_features')},
    {col_or_null('flooring')},
    {col_or_null('waterfront_features')},
    {col_or_null('patio_porch')},
    {col_or_null('other_structures')},
    {col_or_null('association_amenities')},
    {col_or_null('fencing')},
    {col_or_null('fireplace_features')},
    {col_or_null('additional_features')},
    {col_or_null('appliances')},
    {col_or_null('community_features')},
    {col_or_null('exterior_features')},
    {col_or_null('interior_features')},
    {col_or_null('lot_features')},
    {col_or_null('security_features')},

    -- Misc mapping fields we may need for gold or portals later
    LOWER(TRIM(p.apartment_type))             AS apartment_type,
    LOWER(TRIM(p.building_type))              AS building_type,
    LOWER(TRIM(p.hotel_type))                 AS hotel_type,
    LOWER(TRIM(p.house_type))                 AS house_type,
    LOWER(TRIM(p.industrial_type))            AS industrial_type,
    LOWER(TRIM(p.land_type))                  AS land_type,
    LOWER(TRIM(p.office_type))                AS office_type,
    LOWER(TRIM(p.retail_type))                AS retail_type,

    -- Bazaraki portal fields (for common_property_bazaraki)
    {col_or_null('custom_bazaraki_negotiable_price') if has_col('custom_bazaraki_negotiable_price') else 'CAST(NULL AS BOOLEAN) AS custom_bazaraki_negotiable_price'},
    {col_or_null('custom_bazaraki_exchange') if has_col('custom_bazaraki_exchange') else 'CAST(NULL AS BOOLEAN) AS custom_bazaraki_exchange'},
    {col_or_null('custom_bazaraki_registration_block') if has_col('custom_bazaraki_registration_block') else 'CAST(NULL AS INT) AS custom_bazaraki_registration_block'},
    {col_or_null('custom_bazaraki_chosen_phone') if has_col('custom_bazaraki_chosen_phone') else 'CAST(NULL AS STRING) AS custom_bazaraki_chosen_phone'},
    {col_or_null('custom_bazaraki_registration_number') if has_col('custom_bazaraki_registration_number') else 'CAST(NULL AS INT) AS custom_bazaraki_registration_number'},
    {col_or_null('custom_bazaraki_online_viewing') if has_col('custom_bazaraki_online_viewing') else 'CAST(NULL AS BOOLEAN) AS custom_bazaraki_online_viewing'},
    {col_or_null('custom_bazaraki_url') if has_col('custom_bazaraki_url') else 'CAST(NULL AS STRING) AS custom_bazaraki_url'},
    {col_or_null('custom_bazaraki_location') if has_col('custom_bazaraki_location') else 'CAST(NULL AS STRING) AS custom_bazaraki_location'},
    {col_or_null('custom_bazaraki_disallow_chat') if has_col('custom_bazaraki_disallow_chat') else 'CAST(NULL AS BOOLEAN) AS custom_bazaraki_disallow_chat'},
    {col_or_null('custom_bazaraki_phone_hide') if has_col('custom_bazaraki_phone_hide') else 'CAST(NULL AS BOOLEAN) AS custom_bazaraki_phone_hide'}

FROM {bronze_table} p
"""

print("Creating mls2.qobrix_silver_properties from bronze...")
spark.sql(transform_sql)

silver_df = spark.table(f"{catalog}.{schema}.qobrix_silver_properties")
print(f"✅ Silver properties rows: {silver_df.count()}, columns: {len(silver_df.columns)}")

