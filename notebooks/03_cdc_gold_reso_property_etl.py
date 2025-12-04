# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - CDC Gold RESO Property ETL (Incremental)
# MAGIC 
# MAGIC **Purpose:** Transforms changed silver properties to RESO format using MERGE.
# MAGIC 
# MAGIC **How it works:**
# MAGIC 1. Identifies properties changed since last gold ETL (using `etl_timestamp`)
# MAGIC 2. MERGEs only changed records into gold (insert/update)
# MAGIC 3. Much faster than full refresh for incremental updates
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.property`, `mls2.qobrix_bronze.properties`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.property` (125+ fields)
# MAGIC 
# MAGIC **When to use:**
# MAGIC - After CDC silver sync: Run this notebook
# MAGIC - After full refresh silver: Run 03_gold_reso_property_etl.py (full refresh)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

from datetime import datetime

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("=" * 80)
print("🔄 CDC MODE - Gold RESO Property ETL")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Changed Records

# COMMAND ----------

# Get last gold ETL timestamp
try:
    last_gold_etl = spark.sql("""
        SELECT MAX(etl_timestamp) as last_etl 
        FROM reso_gold.property
    """).collect()[0]["last_etl"]
    
    if last_gold_etl:
        print(f"📊 Last gold ETL: {last_gold_etl}")
    else:
        last_gold_etl = datetime(2000, 1, 1)
        print("⚠️ Gold table is empty, will process all records")
except:
    last_gold_etl = datetime(2000, 1, 1)
    print("⚠️ Gold table doesn't exist, will create from scratch")

# Count changed records in silver
try:
    changed_count = spark.sql(f"""
        SELECT COUNT(*) as cnt 
        FROM qobrix_silver.property 
        WHERE etl_timestamp > '{last_gold_etl}'
    """).collect()[0]["cnt"]
    print(f"📊 Changed properties since last gold ETL: {changed_count}")
    use_cdc = changed_count > 0
except Exception as e:
    print(f"⚠️ Error checking silver: {e}")
    use_cdc = False
    changed_count = spark.sql("SELECT COUNT(*) as cnt FROM qobrix_silver.property").collect()[0]["cnt"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## MERGE Changed Records

# COMMAND ----------

# Define the transformation SELECT (same as full refresh, but can filter)
transform_select = """
SELECT
    -- RESO STANDARD FIELDS (Core)
    CONCAT('QOBRIX_', s.qobrix_id)               AS ListingKey,
    CAST(s.qobrix_ref AS STRING)                 AS ListingId,

    CASE LOWER(s.status)
        WHEN 'available'    THEN 'Active'
        WHEN 'reserved'     THEN 'Pending'
        WHEN 'under_offer'  THEN 'Pending'
        WHEN 'sold'         THEN 'Closed'
        WHEN 'rented'       THEN 'Closed'
        WHEN 'withdrawn'    THEN 'Withdrawn'
        ELSE 'Active'
    END                                           AS StandardStatus,

    CASE LOWER(s.property_type)
        WHEN 'apartment'     THEN 'Apartment'
        WHEN 'house'         THEN 'SingleFamilyDetached'
        WHEN 'land'          THEN 'Land'
        WHEN 'office'        THEN 'Office'
        WHEN 'investment'    THEN 'Commercial'
        WHEN 'building'      THEN 'Commercial'
        WHEN 'hotel'         THEN 'Commercial'
        WHEN 'parking_lot'   THEN 'Parking'
        WHEN 'retail'        THEN 'Commercial'
        WHEN 'industrial'    THEN 'Commercial'
        WHEN 'other'         THEN 'Other'
        ELSE 'Other'
    END                                           AS PropertyType,

    COALESCE(
        CAST(ps.label AS STRING),
        CAST(ps.code AS STRING),
        CAST(s.property_subtype_id AS STRING),
        NULL
    )                                            AS PropertySubType,

    TRY_CAST(s.bedrooms AS INT)                   AS BedroomsTotal,
    TRY_CAST(s.bathrooms AS INT)                  AS BathroomsTotalInteger,
    TRY_CAST(TRY_CAST(b.wc_bathrooms AS DOUBLE) AS INT) AS BathroomsHalf,
    TRY_CAST(s.internal_area_amount AS DECIMAL(18,2)) AS LivingArea,
    'SquareMeters'                                AS LivingAreaUnits,
    TRY_CAST(s.plot_area_amount AS DECIMAL(18,2)) AS LotSizeSquareFeet,
    'SquareMeters'                                AS LotSizeUnits,
    ROUND(TRY_CAST(s.plot_area_amount AS DECIMAL(18,6)) * 0.000247105, 4) AS LotSizeAcres,
    TRY_CAST(s.list_selling_price_amount AS DECIMAL(18,2)) AS ListPrice,
    TRY_CAST(b.list_rental_price_amount AS DECIMAL(18,2))  AS LeasePrice,
    CASE LOWER(COALESCE(b.rent_frequency, ''))
        WHEN 'monthly' THEN 'Monthly'
        WHEN 'weekly' THEN 'Weekly'
        WHEN 'daily' THEN 'Daily'
        WHEN 'yearly' THEN 'Annually'
        WHEN 'annually' THEN 'Annually'
        ELSE b.rent_frequency
    END                                           AS LeaseAmountFrequency,
    s.listing_date                                AS ListingContractDate,
    s.modified_ts                                 AS ModificationTimestamp,
    s.street                                      AS UnparsedAddress,
    s.city                                        AS City,
    s.state                                       AS StateOrProvince,
    s.post_code                                   AS PostalCode,
    s.country                                     AS Country,
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 0) AS DOUBLE) AS Latitude,
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 1) AS DOUBLE) AS Longitude,
    s.description                                 AS PublicRemarks,
    CASE WHEN b.agent IS NOT NULL AND b.agent != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.agent) 
         ELSE NULL END                            AS ListAgentKey,
    CASE WHEN b.salesperson IS NOT NULL AND b.salesperson != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.salesperson) 
         ELSE NULL END                            AS CoListAgentKey,
    CASE WHEN b.agent IS NOT NULL AND b.agent != '' 
         THEN CONCAT('QOBRIX_OFFICE_', b.agent) 
         ELSE NULL END                            AS ListOfficeKey,

    -- RESO STANDARD FIELDS (Mapped from Qobrix)
    TRY_CAST(b.construction_year AS INT)          AS YearBuilt,
    TRY_CAST(b.renovation_year AS INT)            AS YearBuiltEffective,
    b.view                                        AS View,
    b.pool_features                               AS PoolFeatures,
    b.heating                                     AS Heating,
    b.cooling                                     AS Cooling,
    CASE LOWER(COALESCE(b.furnished, ''))
        WHEN 'true'  THEN 'Furnished'
        WHEN 'false' THEN 'Unfurnished'
        WHEN 'partially' THEN 'Partially'
        ELSE NULL
    END                                           AS Furnished,
    CASE LOWER(COALESCE(b.pets_allowed, ''))
        WHEN 'true'  THEN 'Yes'
        WHEN 'false' THEN 'No'
        ELSE NULL
    END                                           AS PetsAllowed,
    CASE LOWER(COALESCE(b.fireplace, ''))
        WHEN 'true'  THEN TRUE
        WHEN 'false' THEN FALSE
        ELSE NULL
    END                                           AS FireplaceYN,
    CONCAT_WS(',',
        CASE WHEN COALESCE(b.covered_parking, '') != '' AND b.covered_parking != '0' THEN 'Covered' ELSE NULL END,
        CASE WHEN COALESCE(b.uncovered_parking, '') != '' AND b.uncovered_parking != '0' THEN 'Uncovered' ELSE NULL END,
        CASE WHEN COALESCE(b.parking, '') != '' THEN b.parking ELSE NULL END
    )                                             AS ParkingFeatures,
    TRY_CAST(b.floors_building AS INT)            AS StoriesTotal,
    TRY_CAST(b.floor_number AS INT)               AS Stories,
    b.flooring                                    AS Flooring,
    b.fireplace_features                          AS FireplaceFeatures,
    b.waterfront_features                         AS WaterfrontFeatures,
    b.patio_porch                                 AS PatioAndPorchFeatures,
    b.other_structures                            AS OtherStructures,
    b.association_amenities                       AS AssociationAmenities,
    b.fencing                                     AS Fencing,

    -- QOBRIX EXTENSION FIELDS
    b.sea_view                                    AS X_SeaView,
    b.mountain_view                               AS X_MountainView,
    b.beach_front                                 AS X_BeachFront,
    b.abuts_green_area                            AS X_AbutsGreenArea,
    b.elevated_area                               AS X_ElevatedArea,
    b.private_swimming_pool                       AS X_PrivateSwimmingPool,
    b.common_swimming_pool                        AS X_CommonSwimmingPool,
    b.garden_area_amount                          AS X_GardenArea,
    b.roof_garden_area_amount                     AS X_RoofGardenArea,
    b.elevator                                    AS X_Elevator,
    b.air_condition                               AS X_AirCondition,
    b.alarm                                       AS X_Alarm,
    b.smart_home                                  AS X_SmartHome,
    b.solar_water_heater                          AS X_SolarWaterHeater,
    b.storage_space                               AS X_StorageSpace,
    b.maids_room                                  AS X_MaidsRoom,
    b.concierge_reception                         AS X_ConciergeReception,
    b.secure_door                                 AS X_SecureDoor,
    b.kitchenette                                 AS X_Kitchenette,
    b.home_office                                 AS X_HomeOffice,
    b.separate_laundry_room                       AS X_SeparateLaundryRoom,
    b.reception                                   AS X_Reception,
    b.store_room                                  AS X_StoreRoom,
    b.construction_type                           AS X_ConstructionType,
    b.construction_stage                          AS X_ConstructionStage,
    b.floor_type                                  AS X_FloorType,
    b.new_build                                   AS X_NewBuild,
    TRY_CAST(b.height AS DECIMAL(10,2))           AS X_Height,
    TRY_CAST(b.storeys_max_floor AS INT)          AS X_MaxFloor,
    b.unit_number                                 AS X_UnitNumber,
    b.energy_efficiency_grade                     AS X_EnergyEfficiencyGrade,
    b.energy_consumption_rating                   AS X_EnergyConsumptionRating,
    b.energy_consumption_value                    AS X_EnergyConsumptionValue,
    b.energy_emission_rating                      AS X_EnergyEmissionRating,
    b.heating_type                                AS X_HeatingType,
    b.heating_medium                              AS X_HeatingMedium,
    b.cooling_type                                AS X_CoolingType,
    b.electricity                                 AS X_Electricity,
    b.electricity_type                            AS X_ElectricityType,
    b.water                                       AS X_Water,
    b.distance_from_beach                         AS X_DistanceFromBeach,
    b.distance_from_airport                       AS X_DistanceFromAirport,
    b.distance_from_centre                        AS X_DistanceFromCentre,
    b.distance_from_school                        AS X_DistanceFromSchool,
    b.distance_from_shops                         AS X_DistanceFromShops,
    b.distance_from_hospital                      AS X_DistanceFromHospital,
    b.distance_from_university                    AS X_DistanceFromUniversity,
    b.distance_from_rail_station                  AS X_DistanceFromRailStation,
    b.distance_from_tube_station                  AS X_DistanceFromTubeStation,
    TRY_CAST(b.living_rooms AS INT)               AS X_LivingRooms,
    TRY_CAST(b.kitchens AS INT)                   AS X_Kitchens,
    b.kitchen_type                                AS X_KitchenType,
    TRY_CAST(TRY_CAST(b.wc_bathrooms AS DOUBLE) AS INT) AS X_WCBathrooms,
    TRY_CAST(b.office_spaces AS INT)              AS X_OfficeSpaces,
    TRY_CAST(b.verandas AS INT)                   AS X_VerandasCount,
    TRY_CAST(b.covered_area_amount AS DECIMAL(18,2))     AS X_CoveredArea,
    TRY_CAST(b.uncovered_area_amount AS DECIMAL(18,2))   AS X_UncoveredArea,
    TRY_CAST(b.total_area_amount AS DECIMAL(18,2))       AS X_TotalArea,
    TRY_CAST(b.mezzanine_amount AS DECIMAL(18,2))        AS X_MezzanineArea,
    TRY_CAST(b.storage_amount AS DECIMAL(18,2))          AS X_StorageArea,
    TRY_CAST(b.covered_verandas_amount AS DECIMAL(18,2)) AS X_CoveredVerandas,
    TRY_CAST(b.uncovered_verandas_amount AS DECIMAL(18,2)) AS X_UncoveredVerandas,
    TRY_CAST(b.frontage_amount AS DECIMAL(18,2))         AS X_Frontage,
    b.building_density                            AS X_BuildingDensity,
    b.coverage                                    AS X_Coverage,
    b.cover_factor                                AS X_CoverFactor,
    b.corner_plot                                 AS X_CornerPlot,
    b.right_of_way                                AS X_RightOfWay,
    b.registered_road                             AS X_RegisteredRoad,
    b.town_planning_zone                          AS X_TownPlanningZone,
    b.land_locked                                 AS X_LandLocked,
    b.cadastral_reference                         AS X_CadastralReference,
    b.ideal_for                                   AS X_IdealFor,
    b.licensed_for                                AS X_LicensedFor,
    b.business_transfer_or_sale                   AS X_BusinessTransferOrSale,
    b.business_transfer_price                     AS X_BusinessTransferPrice,
    b.business_transfer_commercial_activity       AS X_BusinessActivity,
    b.conference                                  AS X_ConferenceRoom,
    b.server_room                                 AS X_ServerRoom,
    b.enclosed_office_room                        AS X_EnclosedOffice,
    b.office_layout                               AS X_OfficeLayout,
    b.price_per_square                            AS X_PricePerSquare,
    b.price_qualifier                             AS X_PriceQualifier,
    b.plus_vat                                    AS X_PlusVAT,
    b.rent_frequency                              AS X_RentFrequency,
    b.minimum_tenancy                             AS X_MinimumTenancy,
    b.tenancy_type                                AS X_TenancyType,
    b.occupancy                                   AS X_Occupancy,
    TRY_CAST(b.previous_list_selling_price AS DECIMAL(18,2)) AS X_PreviousListPrice,
    TRY_CAST(b.previous_list_rental_price AS DECIMAL(18,2))  AS X_PreviousLeasePrice,
    b.list_selling_price_modified                 AS X_ListPriceModified,
    b.list_rental_price_modified                  AS X_LeasePriceModified,
    b.auction_start_date                          AS X_AuctionStartDate,
    b.auction_end_date                            AS X_AuctionEndDate,
    TRY_CAST(b.reserve_price_amount AS DECIMAL(18,2))      AS X_ReservePrice,
    TRY_CAST(b.starting_bidding_amount AS DECIMAL(18,2))   AS X_StartingBid,
    b.project                                     AS X_ProjectId,
    b.developer_id                                AS X_DeveloperId,
    b.featured                                    AS X_Featured,
    b.featured_priority                           AS X_FeaturedPriority,
    b.property_of_the_month                       AS X_PropertyOfTheMonth,
    b.video_link                                  AS X_VideoLink,
    b.virtual_tour_link                           AS X_VirtualTourLink,
    b.website_url                                 AS X_WebsiteUrl,
    b.website_status                              AS X_WebsiteStatus,
    b.short_description                           AS X_ShortDescription,
    b.name                                        AS X_PropertyName,
    b.apartment_type                              AS X_ApartmentType,
    b.house_type                                  AS X_HouseType,
    b.land_type                                   AS X_LandType,
    b.office_type                                 AS X_OfficeType,
    b.retail_type                                 AS X_RetailType,
    b.industrial_type                             AS X_IndustrialType,
    b.hotel_type                                  AS X_HotelType,
    b.building_type                               AS X_BuildingType,
    b.investment_type                             AS X_InvestmentType,
    TRY_CAST(b.customer_parking AS INT)           AS X_CustomerParking,
    b.additional_features                         AS X_AdditionalFeatures,
    b.interior_features                           AS X_InteriorFeatures,
    b.exterior_features                           AS X_ExteriorFeatures,
    b.community_features                          AS X_CommunityFeatures,
    b.lot_features                                AS X_LotFeatures,
    b.security_features                           AS X_SecurityFeatures,
    b.appliances                                  AS X_Appliances,
    s.qobrix_id                                   AS X_QobrixId,
    s.qobrix_ref                                  AS X_QobrixRef,
    s.qobrix_source                               AS X_QobrixSource,
    b.legacy_id                                   AS X_QobrixLegacyId,
    b.seller                                      AS X_QobrixSellerId,
    s.created_ts                                  AS X_QobrixCreated,
    s.modified_ts                                 AS X_QobrixModified,

    CURRENT_TIMESTAMP()                           AS etl_timestamp,
    CONCAT('gold_cdc_', CURRENT_DATE())           AS etl_batch_id

FROM qobrix_silver.property s
LEFT JOIN qobrix_bronze.properties b 
    ON CAST(s.qobrix_id AS STRING) = CAST(b.id AS STRING)
LEFT JOIN qobrix_bronze.property_subtypes ps 
    ON CAST(s.property_subtype_id AS STRING) = CAST(ps.id AS STRING)
"""

# Check if gold table exists
tables = [t.name for t in spark.catalog.listTables("reso_gold")]

if "property" not in tables:
    # First run - create table
    print("📊 Creating reso_gold.property table (first run)...")
    spark.sql(f"CREATE OR REPLACE TABLE reso_gold.property AS {transform_select}")
    
elif not use_cdc:
    # Full refresh mode
    print("📊 Running full refresh (no CDC data available)...")
    spark.sql(f"CREATE OR REPLACE TABLE reso_gold.property AS {transform_select}")
    
else:
    # CDC mode - MERGE only changed records
    print(f"📊 Merging {changed_count} changed records...")
    
    # Create temp view with only changed records
    cdc_filter = f"WHERE s.etl_timestamp > '{last_gold_etl}'"
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _cdc_gold_property AS
        {transform_select}
        {cdc_filter}
    """)
    
    # MERGE into gold
    merge_sql = """
        MERGE INTO reso_gold.property AS target
        USING _cdc_gold_property AS source
        ON target.ListingKey = source.ListingKey
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """
    
    spark.sql(merge_sql)
    print(f"✅ Merged {changed_count} records into reso_gold.property")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

gold_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.property").collect()[0]["c"]
gold_cols = len(spark.table("reso_gold.property").columns)
print(f"\n📊 Gold RESO property total records: {gold_count}")
print(f"📊 Gold RESO property columns: {gold_cols}")

# Show recent changes
print("\nRecent modifications:")
spark.sql("""
    SELECT ListingKey, ListingId, StandardStatus, PropertyType, etl_timestamp
    FROM reso_gold.property
    ORDER BY etl_timestamp DESC
    LIMIT 5
""").show(truncate=False)

print("\n" + "=" * 80)
print("✅ CDC Gold RESO Property ETL Complete")
print("=" * 80)
