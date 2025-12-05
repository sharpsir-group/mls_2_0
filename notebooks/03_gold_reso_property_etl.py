# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Silver -> Gold RESO Property ETL
# MAGIC 
# MAGIC **Purpose:** Transforms silver properties to RESO Data Dictionary 2.x compliant format.
# MAGIC 
# MAGIC **Input:** `mls2.qobrix_silver.property`, `mls2.qobrix_bronze.property_subtypes`, `mls2.qobrix_bronze.properties`
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.property` with:
# MAGIC 
# MAGIC **RESO Standard Fields (Core):**
# MAGIC - `ListingKey`, `ListingId` - Unique identifiers
# MAGIC - `StandardStatus` - Active, Pending, Closed, Withdrawn
# MAGIC - `PropertyType`, `PropertySubType` - Property classification
# MAGIC - `BedroomsTotal`, `BathroomsTotalInteger`, `LivingArea`, `ListPrice`
# MAGIC - `City`, `StateOrProvince`, `Country`, `Latitude`, `Longitude`
# MAGIC - `ListAgentKey`, `CoListAgentKey` - Links to Member resource
# MAGIC 
# MAGIC **RESO Standard Fields (Mapped from Qobrix):**
# MAGIC - `YearBuilt`, `YearBuiltEffective` - Construction/renovation years
# MAGIC - `View`, `PoolFeatures` - Views and pool amenities
# MAGIC - `Heating`, `Cooling` - HVAC systems
# MAGIC - `Furnished`, `PetsAllowed` - Property conditions
# MAGIC - `FireplaceYN`, `FireplaceFeatures`, `ParkingFeatures` - Features
# MAGIC - `StoriesTotal`, `Stories` - Building floors
# MAGIC - `Flooring`, `Fencing`, `WaterfrontFeatures` - Property details
# MAGIC - `PatioAndPorchFeatures`, `OtherStructures`, `AssociationAmenities` - Amenities
# MAGIC 
# MAGIC **Qobrix Extension Fields (X_ prefix per RESO convention):**
# MAGIC - `X_SeaView`, `X_MountainView`, `X_BeachFront`, `X_AbutsGreenArea` - View flags
# MAGIC - `X_EnergyEfficiencyGrade`, `X_HeatingType` - Energy details
# MAGIC - `X_DistanceFromBeach`, `X_DistanceFromAirport`, `X_DistanceFromRailStation` - Distances
# MAGIC - `X_Featured`, `X_PropertyOfTheMonth`, `X_ShortDescription` - Marketing
# MAGIC - `X_UnitNumber`, `X_Height`, `X_MaxFloor` - Building details
# MAGIC - `X_AuctionStartDate`, `X_ReservePrice` - Auction fields
# MAGIC - `X_PreviousListPrice`, `X_ListPriceModified` - Price history
# MAGIC - `X_ApartmentType`, `X_HouseType`, `X_LandType` - Property subtypes
# MAGIC - All other Qobrix-specific attributes preserved (125+ total fields)
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Property+Resource
# MAGIC 
# MAGIC **Run After:** 02_silver_qobrix_property_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("Using catalog:", catalog)

# COMMAND ----------

try:
    silver_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.property").collect()[0]["c"]
    print("📊 Silver properties:", silver_count)
    if silver_count == 0:
        print("⚠️ Silver property table is empty. Aborting RESO transform.")
except Exception as e:
    print("❌ Error reading silver property table:", e)
    raise

# COMMAND ----------

# First, let's see what columns are actually available in silver and bronze
silver_cols = set([c.lower() for c in spark.table("qobrix_silver.property").columns])
print(f"📋 Silver table has {len(silver_cols)} columns")

bronze_cols = set([c.lower() for c in spark.table("qobrix_bronze.properties").columns])
print(f"📋 Bronze table has {len(bronze_cols)} columns")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform to RESO with Extension Fields

# COMMAND ----------

# Build the SQL with all Qobrix extension fields (X_ prefix per RESO convention)
# We join bronze for additional fields not in silver

transform_silver_to_reso_sql = """
CREATE OR REPLACE TABLE reso_gold.property AS
SELECT
    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD FIELDS
    -- ═══════════════════════════════════════════════════════════════════════════
    
    -- Core identifiers
    CONCAT('QOBRIX_', s.qobrix_id)               AS ListingKey,
    CAST(s.qobrix_ref AS STRING)                 AS ListingId,

    -- Status mapping (Qobrix -> RESO StandardStatus)
    CASE LOWER(s.status)
        WHEN 'available'    THEN 'Active'
        WHEN 'reserved'     THEN 'Pending'
        WHEN 'under_offer'  THEN 'Pending'
        WHEN 'sold'         THEN 'Closed'
        WHEN 'rented'       THEN 'Closed'
        WHEN 'withdrawn'    THEN 'Withdrawn'
        ELSE 'Active'
    END                                           AS StandardStatus,

    -- PropertyClass (RESO standard: RESI, RLSE, COMS, COML, LAND)
    -- Distinguishes Sale vs Lease and Residential vs Commercial
    CASE
        -- Land is always LAND
        WHEN LOWER(s.property_type) = 'land' THEN 'LAND'
        -- Residential types
        WHEN LOWER(s.property_type) IN ('apartment', 'house') THEN
            CASE LOWER(COALESCE(s.sale_rent, 'for_sale'))
                WHEN 'for_rent' THEN 'RLSE'  -- Residential Lease
                ELSE 'RESI'                   -- Residential Sale
            END
        -- Commercial types
        WHEN LOWER(s.property_type) IN ('office', 'retail', 'building', 'hotel', 'industrial', 'investment') THEN
            CASE LOWER(COALESCE(s.sale_rent, 'for_sale'))
                WHEN 'for_rent' THEN 'COML'  -- Commercial Lease
                ELSE 'COMS'                   -- Commercial Sale
            END
        -- Default to Residential Sale
        ELSE 'RESI'
    END                                           AS PropertyClass,

    -- DevelopmentStatus (RESO standard: Proposed, Under Construction, Complete)
    -- Maps Qobrix project construction stage to RESO development status
    CASE LOWER(COALESCE(b.project_project_construction_stage, ''))
        WHEN 'offplans'          THEN 'Proposed'
        WHEN 'construction_phase' THEN 'Under Construction'
        WHEN 'completed'         THEN 'Complete'
        ELSE NULL
    END                                           AS DevelopmentStatus,

    -- Property type mapping
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

    -- Property subtype (from lookup)
    COALESCE(
        CAST(ps.label AS STRING),
        CAST(ps.code AS STRING),
        CAST(s.property_subtype_id AS STRING),
        NULL
    )                                            AS PropertySubType,

    -- Beds / baths (RESO standard)
    TRY_CAST(s.bedrooms AS INT)                   AS BedroomsTotal,
    TRY_CAST(s.bathrooms AS INT)                  AS BathroomsTotalInteger,
    TRY_CAST(TRY_CAST(b.wc_bathrooms AS DOUBLE) AS INT) AS BathroomsHalf,

    -- Size / area (RESO standard)
    TRY_CAST(s.internal_area_amount AS DECIMAL(18,2)) AS LivingArea,
    'SquareMeters'                                AS LivingAreaUnits,
    TRY_CAST(s.plot_area_amount AS DECIMAL(18,2)) AS LotSizeSquareFeet,
    'SquareMeters'                                AS LotSizeUnits,
    -- LotSizeAcres: Convert from square meters (1 m² = 0.000247105 acres)
    ROUND(TRY_CAST(s.plot_area_amount AS DECIMAL(18,6)) * 0.000247105, 4) AS LotSizeAcres,

    -- Pricing (RESO standard)
    TRY_CAST(s.list_selling_price_amount AS DECIMAL(18,2)) AS ListPrice,
    TRY_CAST(b.list_rental_price_amount AS DECIMAL(18,2))  AS LeasePrice,
    -- LeaseAmountFrequency: Rent frequency (monthly, weekly, etc.)
    CASE LOWER(COALESCE(b.rent_frequency, ''))
        WHEN 'monthly' THEN 'Monthly'
        WHEN 'weekly' THEN 'Weekly'
        WHEN 'daily' THEN 'Daily'
        WHEN 'yearly' THEN 'Annually'
        WHEN 'annually' THEN 'Annually'
        ELSE b.rent_frequency
    END                                           AS LeaseAmountFrequency,

    -- Dates
    s.listing_date                                AS ListingContractDate,
    s.modified_ts                                 AS ModificationTimestamp,

    -- Address / location
    s.street                                      AS UnparsedAddress,
    s.city                                        AS City,
    s.state                                       AS StateOrProvince,
    s.post_code                                   AS PostalCode,
    s.country                                     AS Country,

    -- Coordinates (safely handle missing or malformed coordinates)
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 0) AS DOUBLE) AS Latitude,
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 1) AS DOUBLE) AS Longitude,

    -- Remarks
    s.description                                 AS PublicRemarks,

    -- Agent/Office linkage (RESO standard)
    CASE WHEN b.agent IS NOT NULL AND b.agent != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.agent) 
         ELSE NULL END                            AS ListAgentKey,
    CASE WHEN b.salesperson IS NOT NULL AND b.salesperson != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.salesperson) 
         ELSE NULL END                            AS CoListAgentKey,
    -- ListOfficeKey: Link to office (agent's agency or agent itself as office)
    CASE WHEN b.agent IS NOT NULL AND b.agent != '' 
         THEN CONCAT('QOBRIX_OFFICE_', b.agent) 
         ELSE NULL END                            AS ListOfficeKey,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD FIELDS (Mapped from Qobrix)
    -- ═══════════════════════════════════════════════════════════════════════════
    
    -- Building Age (RESO standard)
    TRY_CAST(b.construction_year AS INT)          AS YearBuilt,
    TRY_CAST(b.renovation_year AS INT)            AS YearBuiltEffective,
    
    -- View (RESO standard - multi-value lookup)
    b.view                                        AS View,
    
    -- Pool Features (RESO standard - multi-value lookup)
    b.pool_features                               AS PoolFeatures,
    
    -- HVAC (RESO standard)
    b.heating                                     AS Heating,
    b.cooling                                     AS Cooling,
    
    -- Furnished (RESO standard lookup)
    CASE LOWER(COALESCE(b.furnished, ''))
        WHEN 'true'  THEN 'Furnished'
        WHEN 'false' THEN 'Unfurnished'
        WHEN 'partially' THEN 'Partially'
        ELSE NULL
    END                                           AS Furnished,
    
    -- Pets Allowed (RESO standard lookup)
    CASE LOWER(COALESCE(b.pets_allowed, ''))
        WHEN 'true'  THEN 'Yes'
        WHEN 'false' THEN 'No'
        ELSE NULL
    END                                           AS PetsAllowed,
    
    -- Fireplace (RESO standard)
    CASE LOWER(COALESCE(b.fireplace, ''))
        WHEN 'true'  THEN TRUE
        WHEN 'false' THEN FALSE
        ELSE NULL
    END                                           AS FireplaceYN,
    
    -- Parking (RESO standard - multi-value lookup)
    CONCAT_WS(',',
        CASE WHEN COALESCE(b.covered_parking, '') != '' AND b.covered_parking != '0' THEN 'Covered' ELSE NULL END,
        CASE WHEN COALESCE(b.uncovered_parking, '') != '' AND b.uncovered_parking != '0' THEN 'Uncovered' ELSE NULL END,
        CASE WHEN COALESCE(b.parking, '') != '' THEN b.parking ELSE NULL END
    )                                             AS ParkingFeatures,
    
    -- Stories (RESO standard)
    TRY_CAST(b.floors_building AS INT)            AS StoriesTotal,
    TRY_CAST(b.floor_number AS INT)               AS Stories,
    
    -- Flooring (RESO standard)
    b.flooring                                    AS Flooring,
    
    -- Fireplace Features (RESO standard)
    b.fireplace_features                          AS FireplaceFeatures,
    
    -- Waterfront (RESO standard)
    b.waterfront_features                         AS WaterfrontFeatures,
    
    -- Patio/Porch (RESO standard)
    b.patio_porch                                 AS PatioAndPorchFeatures,
    
    -- Other Structures (RESO standard)
    b.other_structures                            AS OtherStructures,
    
    -- Association Amenities (RESO standard)
    b.association_amenities                       AS AssociationAmenities,
    
    -- Fencing (RESO standard)
    b.fencing                                     AS Fencing,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- QOBRIX EXTENSION FIELDS (X_ prefix per RESO convention)
    -- Regional/vendor-specific fields that don't map to RESO standard
    -- ═══════════════════════════════════════════════════════════════════════════
    
    -- Views & Amenities (Qobrix-specific boolean flags)
    b.sea_view                                    AS X_SeaView,
    b.mountain_view                               AS X_MountainView,
    b.beach_front                                 AS X_BeachFront,
    b.abuts_green_area                            AS X_AbutsGreenArea,
    b.elevated_area                               AS X_ElevatedArea,
    b.private_swimming_pool                       AS X_PrivateSwimmingPool,
    b.common_swimming_pool                        AS X_CommonSwimmingPool,
    b.garden_area_amount                          AS X_GardenArea,
    b.roof_garden_area_amount                     AS X_RoofGardenArea,
    
    -- Property Features (Qobrix-specific)
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
    
    -- Building Info (Qobrix-specific details)
    b.construction_type                           AS X_ConstructionType,
    b.construction_stage                          AS X_ConstructionStage,
    b.floor_type                                  AS X_FloorType,
    b.new_build                                   AS X_NewBuild,
    TRY_CAST(b.height AS DECIMAL(10,2))           AS X_Height,
    TRY_CAST(b.storeys_max_floor AS INT)          AS X_MaxFloor,
    b.unit_number                                 AS X_UnitNumber,
    
    -- Energy & Utilities (Qobrix-specific details)
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
    
    -- Distances
    b.distance_from_beach                         AS X_DistanceFromBeach,
    b.distance_from_airport                       AS X_DistanceFromAirport,
    b.distance_from_centre                        AS X_DistanceFromCentre,
    b.distance_from_school                        AS X_DistanceFromSchool,
    b.distance_from_shops                         AS X_DistanceFromShops,
    b.distance_from_hospital                      AS X_DistanceFromHospital,
    b.distance_from_university                    AS X_DistanceFromUniversity,
    b.distance_from_rail_station                  AS X_DistanceFromRailStation,
    b.distance_from_tube_station                  AS X_DistanceFromTubeStation,
    
    -- Room Details
    TRY_CAST(b.living_rooms AS INT)               AS X_LivingRooms,
    TRY_CAST(b.kitchens AS INT)                   AS X_Kitchens,
    b.kitchen_type                                AS X_KitchenType,
    -- X_WCBathrooms moved to BathroomsHalf (RESO standard)
    TRY_CAST(b.office_spaces AS INT)              AS X_OfficeSpaces,
    TRY_CAST(b.verandas AS INT)                   AS X_VerandasCount,
    
    -- Area Details
    TRY_CAST(b.covered_area_amount AS DECIMAL(18,2))     AS X_CoveredArea,
    TRY_CAST(b.uncovered_area_amount AS DECIMAL(18,2))   AS X_UncoveredArea,
    TRY_CAST(b.total_area_amount AS DECIMAL(18,2))       AS X_TotalArea,
    TRY_CAST(b.mezzanine_amount AS DECIMAL(18,2))        AS X_MezzanineArea,
    TRY_CAST(b.storage_amount AS DECIMAL(18,2))          AS X_StorageArea,
    TRY_CAST(b.covered_verandas_amount AS DECIMAL(18,2)) AS X_CoveredVerandas,
    TRY_CAST(b.uncovered_verandas_amount AS DECIMAL(18,2)) AS X_UncoveredVerandas,
    TRY_CAST(b.frontage_amount AS DECIMAL(18,2))         AS X_Frontage,
    
    -- Land Details
    b.building_density                            AS X_BuildingDensity,
    b.coverage                                    AS X_Coverage,
    b.cover_factor                                AS X_CoverFactor,
    b.corner_plot                                 AS X_CornerPlot,
    b.right_of_way                                AS X_RightOfWay,
    b.registered_road                             AS X_RegisteredRoad,
    b.town_planning_zone                          AS X_TownPlanningZone,
    b.land_locked                                 AS X_LandLocked,
    b.cadastral_reference                         AS X_CadastralReference,
    
    -- Commercial
    b.ideal_for                                   AS X_IdealFor,
    b.licensed_for                                AS X_LicensedFor,
    b.business_transfer_or_sale                   AS X_BusinessTransferOrSale,
    b.business_transfer_price                     AS X_BusinessTransferPrice,
    b.business_transfer_commercial_activity       AS X_BusinessActivity,
    b.conference                                  AS X_ConferenceRoom,
    b.server_room                                 AS X_ServerRoom,
    b.enclosed_office_room                        AS X_EnclosedOffice,
    b.office_layout                               AS X_OfficeLayout,
    
    -- Pricing Details
    b.price_per_square                            AS X_PricePerSquare,
    b.price_qualifier                             AS X_PriceQualifier,
    b.plus_vat                                    AS X_PlusVAT,
    -- X_RentFrequency moved to LeaseAmountFrequency (RESO standard)
    b.minimum_tenancy                             AS X_MinimumTenancy,
    b.tenancy_type                                AS X_TenancyType,
    b.occupancy                                   AS X_Occupancy,
    
    -- Price History
    TRY_CAST(b.previous_list_selling_price AS DECIMAL(18,2)) AS X_PreviousListPrice,
    TRY_CAST(b.previous_list_rental_price AS DECIMAL(18,2))  AS X_PreviousLeasePrice,
    b.list_selling_price_modified                 AS X_ListPriceModified,
    b.list_rental_price_modified                  AS X_LeasePriceModified,
    
    -- Auction
    b.auction_start_date                          AS X_AuctionStartDate,
    b.auction_end_date                            AS X_AuctionEndDate,
    TRY_CAST(b.reserve_price_amount AS DECIMAL(18,2))      AS X_ReservePrice,
    TRY_CAST(b.starting_bidding_amount AS DECIMAL(18,2))   AS X_StartingBid,
    
    -- Project/Development
    b.project                                     AS X_ProjectId,
    b.developer_id                                AS X_DeveloperId,
    
    -- Marketing
    b.featured                                    AS X_Featured,
    b.featured_priority                           AS X_FeaturedPriority,
    b.property_of_the_month                       AS X_PropertyOfTheMonth,
    b.video_link                                  AS X_VideoLink,
    b.virtual_tour_link                           AS X_VirtualTourLink,
    b.website_url                                 AS X_WebsiteUrl,
    b.website_status                              AS X_WebsiteStatus,
    b.short_description                           AS X_ShortDescription,
    b.name                                        AS X_PropertyName,
    
    -- Property Subtypes (detailed)
    b.apartment_type                              AS X_ApartmentType,
    b.house_type                                  AS X_HouseType,
    b.land_type                                   AS X_LandType,
    b.office_type                                 AS X_OfficeType,
    b.retail_type                                 AS X_RetailType,
    b.industrial_type                             AS X_IndustrialType,
    b.hotel_type                                  AS X_HotelType,
    b.building_type                               AS X_BuildingType,
    b.investment_type                             AS X_InvestmentType,
    
    -- Parking Details
    TRY_CAST(b.customer_parking AS INT)           AS X_CustomerParking,
    
    -- Additional Features (JSON arrays stored as strings)
    b.additional_features                         AS X_AdditionalFeatures,
    b.interior_features                           AS X_InteriorFeatures,
    b.exterior_features                           AS X_ExteriorFeatures,
    b.community_features                          AS X_CommunityFeatures,
    b.lot_features                                AS X_LotFeatures,
    b.security_features                           AS X_SecurityFeatures,
    b.appliances                                  AS X_Appliances,
    
    -- Qobrix Metadata (for traceability)
    s.qobrix_id                                   AS X_QobrixId,
    s.qobrix_ref                                  AS X_QobrixRef,
    s.qobrix_source                               AS X_QobrixSource,
    b.legacy_id                                   AS X_QobrixLegacyId,
    b.seller                                      AS X_QobrixSellerId,
    s.created_ts                                  AS X_QobrixCreated,
    s.modified_ts                                 AS X_QobrixModified,

    -- ETL metadata (gold layer)
    CURRENT_TIMESTAMP()                           AS etl_timestamp,
    CONCAT('gold_batch_', CURRENT_DATE())         AS etl_batch_id

FROM qobrix_silver.property s
LEFT JOIN qobrix_bronze.properties b 
    ON CAST(s.qobrix_id AS STRING) = CAST(b.id AS STRING)
LEFT JOIN qobrix_bronze.property_subtypes ps 
    ON CAST(s.property_subtype_id AS STRING) = CAST(ps.id AS STRING)
"""

print("📊 Creating gold RESO property table with extension fields...")
spark.sql(transform_silver_to_reso_sql)

gold_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.property").collect()[0]["c"]
gold_cols = len(spark.table("reso_gold.property").columns)
print(f"✅ Gold RESO property records: {gold_count}")
print(f"✅ Gold RESO property columns: {gold_cols}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show RESO standard fields
print("\n📋 Sample RESO Standard Fields:")
spark.sql("""
    SELECT ListingKey, ListingId, StandardStatus, PropertyType, PropertySubType,
           BedroomsTotal, BathroomsTotalInteger, ListPrice, City, Country
    FROM reso_gold.property
    LIMIT 5
""").show(truncate=False)

# Show RESO mapped fields
print("\n📋 Sample RESO Mapped Fields (from Qobrix):")
spark.sql("""
    SELECT ListingKey, YearBuilt, YearBuiltEffective, View, PoolFeatures,
           Heating, Cooling, Furnished, PetsAllowed, FireplaceYN, StoriesTotal
    FROM reso_gold.property
    LIMIT 5
""").show(truncate=False)

# Show extension fields
print("\n📋 Sample Qobrix Extension Fields (X_ prefix):")
spark.sql("""
    SELECT ListingKey, X_SeaView, X_MountainView, X_Elevator,
           X_EnergyEfficiencyGrade, X_DistanceFromBeach
    FROM reso_gold.property
    LIMIT 5
""").show(truncate=False)

# Count fields by type
all_cols = spark.table("reso_gold.property").columns
extension_cols = [c for c in all_cols if c.startswith("X_")]
standard_cols = [c for c in all_cols if not c.startswith("X_") and not c.startswith("etl_")]
print(f"\n📊 RESO Standard fields: {len(standard_cols)}")
print(f"📊 Qobrix Extension fields (X_): {len(extension_cols)}")
