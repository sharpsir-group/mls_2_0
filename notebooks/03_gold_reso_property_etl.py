# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Silver -> Gold RESO Property ETL (Unified)
# MAGIC 
# MAGIC **Purpose:** Transforms silver properties from multiple sources to RESO Data Dictionary 2.x compliant format.
# MAGIC 
# MAGIC **Input Sources:**
# MAGIC - `mls2.qobrix_silver.property` - Cyprus SIR (Qobrix) data
# MAGIC - `mls2.dash_silver.property` - Hungary SIR (Dash/Sotheby's) data
# MAGIC 
# MAGIC **Output:** `mls2.reso_gold.property` (UNION of all sources)
# MAGIC 
# MAGIC **Multi-Tenant Access Control:**
# MAGIC - `OriginatingSystemOfficeKey` = CSIR for Qobrix data
# MAGIC - `OriginatingSystemOfficeKey` = HSIR for Dash data
# MAGIC - OAuth clients filtered by office key
# MAGIC 
# MAGIC **RESO Data Dictionary 2.0:** https://ddwiki.reso.org/display/DDW20/Property+Resource
# MAGIC 
# MAGIC **Run After:** 02_silver_qobrix_property_etl.py, 01_dash_silver_property_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

# Widget for Qobrix OriginatingSystemOfficeKey
dbutils.widgets.text("QOBRIX_OFFICE_KEY", "CSIR")
qobrix_office_key = os.getenv("QOBRIX_API_OFFICE_KEY") or dbutils.widgets.get("QOBRIX_OFFICE_KEY") or "CSIR"

# Widget for Dash OriginatingSystemOfficeKey  
dbutils.widgets.text("DASH_OFFICE_KEY", "HSIR")
dash_office_key = os.getenv("DASH_OFFICE_KEY") or dbutils.widgets.get("DASH_OFFICE_KEY") or "HSIR"

# MLS List Office Key (brokerage identity for third-party exports)
# Hardcoded to SHARP_SIR for all data
list_office_key = os.getenv("MLS_LIST_OFFICE_KEY") or "SHARP_SIR"

print("Using catalog:", catalog)
print("Qobrix OriginatingSystemOfficeKey:", qobrix_office_key)
print("Dash OriginatingSystemOfficeKey:", dash_office_key)
print("ListOfficeKey:", list_office_key)

# COMMAND ----------

# Check available data sources
qobrix_available = False
dash_available = False

try:
    qobrix_count = spark.sql("SELECT COUNT(*) AS c FROM qobrix_silver.property").collect()[0]["c"]
    print(f"📊 Qobrix Silver properties: {qobrix_count}")
    qobrix_available = qobrix_count > 0
except Exception as e:
    print(f"⚠️ Qobrix Silver not available: {e}")

try:
    dash_count = spark.sql("SELECT COUNT(*) AS c FROM dash_silver.property").collect()[0]["c"]
    print(f"📊 Dash Silver properties: {dash_count}")
    dash_available = dash_count > 0
except Exception as e:
    print(f"⚠️ Dash Silver not available: {e}")

if not qobrix_available and not dash_available:
    print("❌ No data sources available. Aborting.")
    dbutils.notebook.exit("No data to process")

# COMMAND ----------

# Get column info for available sources
if qobrix_available:
    silver_cols = set([c.lower() for c in spark.table("qobrix_silver.property").columns])
    print(f"📋 Qobrix Silver table has {len(silver_cols)} columns")
    
    bronze_cols = set([c.lower() for c in spark.table("qobrix_bronze.properties").columns])
    print(f"📋 Qobrix Bronze table has {len(bronze_cols)} columns")

if dash_available:
    dash_silver_cols = set([c.lower() for c in spark.table("dash_silver.property").columns])
    print(f"📋 Dash Silver table has {len(dash_silver_cols)} columns")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform to RESO with Extension Fields

# COMMAND ----------

# Build the UNION query combining Qobrix and Dash data

# Qobrix transform SQL (with all extension fields)
qobrix_select_sql = f"""
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

    -- PropertyClass (RESO standard)
    CASE
        WHEN LOWER(s.property_type) = 'land' THEN 'LAND'
        WHEN LOWER(s.property_type) IN ('apartment', 'house') THEN
            CASE LOWER(COALESCE(s.sale_rent, 'for_sale'))
                WHEN 'for_rent' THEN 'RLSE'
                ELSE 'RESI'
            END
        WHEN LOWER(s.property_type) IN ('office', 'retail', 'building', 'hotel', 'industrial', 'investment') THEN
            CASE LOWER(COALESCE(s.sale_rent, 'for_sale'))
                WHEN 'for_rent' THEN 'COML'
                ELSE 'COMS'
            END
        ELSE 'RESI'
    END                                           AS PropertyClass,

    -- DevelopmentStatus
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

    -- Property subtype
    COALESCE(
        CAST(ps.label AS STRING),
        CAST(ps.code AS STRING),
        CAST(s.property_subtype_id AS STRING),
        NULL
    )                                            AS PropertySubType,

    -- Beds / baths
    TRY_CAST(s.bedrooms AS INT)                   AS BedroomsTotal,
    TRY_CAST(s.bathrooms AS INT)                  AS BathroomsTotalInteger,
    TRY_CAST(TRY_CAST(b.wc_bathrooms AS DOUBLE) AS INT) AS BathroomsHalf,

    -- Size / area
    TRY_CAST(s.internal_area_amount AS DECIMAL(18,2)) AS LivingArea,
    'SquareMeters'                                AS LivingAreaUnits,
    TRY_CAST(s.plot_area_amount AS DECIMAL(18,2)) AS LotSizeSquareFeet,
    'SquareMeters'                                AS LotSizeUnits,
    ROUND(TRY_CAST(s.plot_area_amount AS DECIMAL(18,6)) * 0.000247105, 4) AS LotSizeAcres,

    -- Pricing
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

    -- Dates
    s.created_ts                                 AS OriginalEntryTimestamp,
    s.listing_date                               AS ListingContractDate,
    s.modified_ts                                AS ModificationTimestamp,

    -- Address / location
    s.street                                      AS UnparsedAddress,
    s.city                                        AS City,
    s.state                                       AS StateOrProvince,
    s.post_code                                   AS PostalCode,
    s.country                                     AS Country,

    -- Coordinates
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 0) AS DOUBLE) AS Latitude,
    TRY_CAST(GET(SPLIT(s.coordinates, ','), 1) AS DOUBLE) AS Longitude,

    -- Remarks
    s.description                                 AS PublicRemarks,

    -- Agent/Office linkage
    CASE WHEN b.agent IS NOT NULL AND b.agent != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.agent) 
         ELSE NULL END                            AS ListAgentKey,
    CASE WHEN b.salesperson IS NOT NULL AND b.salesperson != '' 
         THEN CONCAT('QOBRIX_AGENT_', b.salesperson) 
         ELSE NULL END                            AS CoListAgentKey,
    '{list_office_key}'                           AS ListOfficeKey,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD FIELDS (Mapped from Qobrix)
    -- ═══════════════════════════════════════════════════════════════════════════
    
    TRY_CAST(TRY_CAST(b.construction_year AS DOUBLE) AS INT)  AS YearBuilt,
    TRY_CAST(TRY_CAST(b.renovation_year AS DOUBLE) AS INT)    AS YearBuiltEffective,
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
    TRY_CAST(TRY_CAST(b.floors_building AS DOUBLE) AS INT)    AS StoriesTotal,
    TRY_CAST(TRY_CAST(b.floor_number AS DOUBLE) AS INT)       AS Stories,
    b.flooring                                    AS Flooring,
    b.fireplace_features                          AS FireplaceFeatures,
    b.waterfront_features                         AS WaterfrontFeatures,
    b.patio_porch                                 AS PatioAndPorchFeatures,
    b.other_structures                            AS OtherStructures,
    b.association_amenities                       AS AssociationAmenities,
    b.fencing                                     AS Fencing,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- QOBRIX EXTENSION FIELDS (X_ prefix)
    -- ═══════════════════════════════════════════════════════════════════════════
    
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
    TRY_CAST(TRY_CAST(b.storeys_max_floor AS DOUBLE) AS INT) AS X_MaxFloor,
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

    -- Metadata
    s.qobrix_id                                   AS X_QobrixId,
    s.qobrix_ref                                  AS X_QobrixRef,
    s.qobrix_source                               AS X_QobrixSource,
    b.legacy_id                                   AS X_QobrixLegacyId,
    b.seller                                      AS X_QobrixSellerId,
    s.modified_ts                                 AS X_QobrixModified,

    -- Multi-tenant access control
    '{qobrix_office_key}'                         AS OriginatingSystemOfficeKey,
    'qobrix'                                      AS X_DataSource,

    -- ETL metadata
    CURRENT_TIMESTAMP()                           AS etl_timestamp,
    CONCAT('gold_batch_', CURRENT_DATE())         AS etl_batch_id

FROM qobrix_silver.property s
LEFT JOIN qobrix_bronze.properties b 
    ON CAST(s.qobrix_id AS STRING) = CAST(b.id AS STRING)
LEFT JOIN qobrix_bronze.property_subtypes ps 
    ON CAST(s.property_subtype_id AS STRING) = CAST(ps.id AS STRING)
"""

# Dash transform SQL - Full RESO DD 2.0 mapping with features join
dash_select_sql = f"""
SELECT
    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD FIELDS - Core Identifiers
    -- ═══════════════════════════════════════════════════════════════════════════
    CONCAT('DASH_', d.dash_id)                    AS ListingKey,
    CAST(d.dash_ref AS STRING)                    AS ListingId,

    -- Status mapping (Dash -> RESO)
    CASE UPPER(d.status)
        WHEN 'AC' THEN 'Active'
        WHEN 'PS' THEN 'Pending'
        WHEN 'CL' THEN 'Closed'
        WHEN 'WD' THEN 'Withdrawn'
        ELSE 'Active'
    END                                           AS StandardStatus,

    -- PropertyClass
    CASE
        WHEN LOWER(d.property_type) = 'land' THEN 'LAND'
        WHEN LOWER(d.property_type) IN ('apartment', 'house') THEN
            CASE LOWER(COALESCE(d.sale_rent, 'for_sale'))
                WHEN 'for_rent' THEN 'RLSE'
                ELSE 'RESI'
            END
        ELSE 'RESI'
    END                                           AS PropertyClass,

    NULL                                          AS DevelopmentStatus,

    -- Property type
    CASE LOWER(d.property_type)
        WHEN 'apartment' THEN 'Apartment'
        WHEN 'house'     THEN 'SingleFamilyDetached'
        WHEN 'land'      THEN 'Land'
        WHEN 'office'    THEN 'Office'
        ELSE 'Other'
    END                                           AS PropertyType,

    CAST(d.property_subtype AS STRING)            AS PropertySubType,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Beds / Baths
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(d.bedrooms AS INT)                   AS BedroomsTotal,
    TRY_CAST(d.bathrooms AS INT)                  AS BathroomsTotalInteger,
    TRY_CAST(d.half_bath AS INT)                  AS BathroomsHalf,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Size / Area
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(d.living_area AS DECIMAL(18,2))      AS LivingArea,
    'SquareMeters'                                AS LivingAreaUnits,
    TRY_CAST(d.lot_size AS DECIMAL(18,2))         AS LotSizeSquareFeet,
    'SquareMeters'                                AS LotSizeUnits,
    ROUND(TRY_CAST(d.lot_size AS DECIMAL(18,6)) * 0.000247105, 4) AS LotSizeAcres,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Pricing
    -- ═══════════════════════════════════════════════════════════════════════════
    TRY_CAST(d.list_price AS DECIMAL(18,2))       AS ListPrice,
    NULL                                          AS LeasePrice,
    NULL                                          AS LeaseAmountFrequency,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Dates
    -- ═══════════════════════════════════════════════════════════════════════════
    d.created_ts                                  AS OriginalEntryTimestamp,
    d.listing_date                                AS ListingContractDate,
    d.modified_ts                                 AS ModificationTimestamp,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Location
    -- ═══════════════════════════════════════════════════════════════════════════
    d.street                                      AS UnparsedAddress,
    d.city                                        AS City,
    d.state                                       AS StateOrProvince,
    d.post_code                                   AS PostalCode,
    d.country                                     AS Country,
    d.latitude                                    AS Latitude,
    d.longitude                                   AS Longitude,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Remarks
    -- ═══════════════════════════════════════════════════════════════════════════
    COALESCE(d.public_remarks, d.name)            AS PublicRemarks,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Agent/Office (NEW - from silver)
    -- ═══════════════════════════════════════════════════════════════════════════
    CASE WHEN d.agent_id IS NOT NULL THEN CONCAT('DASH_AGENT_', d.agent_id) ELSE NULL END AS ListAgentKey,
    NULL                                          AS CoListAgentKey,
    '{list_office_key}'                           AS ListOfficeKey,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- RESO STANDARD - Property Features (from parsed features table)
    -- ═══════════════════════════════════════════════════════════════════════════
    d.year_built                                  AS YearBuilt,
    NULL                                          AS YearBuiltEffective,
    f.view                                        AS View,
    f.pool_features                               AS PoolFeatures,
    f.heating_features                            AS Heating,
    f.cooling_features                            AS Cooling,
    NULL                                          AS Furnished,
    NULL                                          AS PetsAllowed,
    CASE WHEN d.has_fireplace THEN TRUE ELSE NULL END AS FireplaceYN,
    f.garage_features                             AS ParkingFeatures,
    NULL                                          AS StoriesTotal,
    NULL                                          AS Stories,
    f.flooring                                    AS Flooring,
    f.fireplace_features                          AS FireplaceFeatures,
    f.waterfront_features                         AS WaterfrontFeatures,
    f.patio_porch_features                        AS PatioAndPorchFeatures,
    NULL                                          AS OtherStructures,
    f.amenities                                   AS AssociationAmenities,
    f.fencing                                     AS Fencing,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- EXTENSION FIELDS - Views/Location (NULL for Dash)
    -- ═══════════════════════════════════════════════════════════════════════════
    NULL AS X_SeaView,
    NULL AS X_MountainView,
    NULL AS X_BeachFront,
    NULL AS X_AbutsGreenArea,
    NULL AS X_ElevatedArea,
    CASE WHEN d.has_pool THEN 'true' ELSE NULL END AS X_PrivateSwimmingPool,
    NULL AS X_CommonSwimmingPool,
    NULL AS X_GardenArea,
    NULL AS X_RoofGardenArea,
    NULL AS X_Elevator,
    CAST(d.has_ac AS STRING)                      AS X_AirCondition,
    CASE WHEN d.has_security THEN 'true' ELSE NULL END AS X_Alarm,
    NULL AS X_SmartHome,
    NULL AS X_SolarWaterHeater,
    NULL AS X_StorageSpace,
    NULL AS X_MaidsRoom,
    NULL AS X_ConciergeReception,
    NULL AS X_SecureDoor,
    NULL AS X_Kitchenette,
    NULL AS X_HomeOffice,
    NULL AS X_SeparateLaundryRoom,
    NULL AS X_Reception,
    NULL AS X_StoreRoom,
    NULL AS X_ConstructionType,
    NULL AS X_ConstructionStage,
    NULL AS X_FloorType,
    CASE WHEN d.is_new_construction THEN 'true' ELSE NULL END AS X_NewBuild,
    NULL AS X_Height,
    NULL AS X_MaxFloor,
    NULL AS X_UnitNumber,
    NULL AS X_EnergyEfficiencyGrade,
    NULL AS X_EnergyConsumptionRating,
    NULL AS X_EnergyConsumptionValue,
    NULL AS X_EnergyEmissionRating,
    f.heating_fuel                                AS X_HeatingType,
    NULL AS X_HeatingMedium,
    NULL AS X_CoolingType,
    f.electric                                    AS X_Electricity,
    NULL AS X_ElectricityType,
    f.water_source                                AS X_Water,
    NULL AS X_DistanceFromBeach,
    NULL AS X_DistanceFromAirport,
    NULL AS X_DistanceFromCentre,
    NULL AS X_DistanceFromSchool,
    NULL AS X_DistanceFromShops,
    NULL AS X_DistanceFromHospital,
    NULL AS X_DistanceFromUniversity,
    NULL AS X_DistanceFromRailStation,
    NULL AS X_DistanceFromTubeStation,
    NULL AS X_LivingRooms,
    NULL AS X_Kitchens,
    f.kitchen_features                            AS X_KitchenType,
    NULL AS X_OfficeSpaces,
    NULL AS X_VerandasCount,
    NULL AS X_CoveredArea,
    NULL AS X_UncoveredArea,
    TRY_CAST(d.building_area AS DECIMAL(18,2))    AS X_TotalArea,
    NULL AS X_MezzanineArea,
    NULL AS X_StorageArea,
    NULL AS X_CoveredVerandas,
    NULL AS X_UncoveredVerandas,
    NULL AS X_Frontage,
    NULL AS X_BuildingDensity,
    NULL AS X_Coverage,
    NULL AS X_CoverFactor,
    NULL AS X_CornerPlot,
    NULL AS X_RightOfWay,
    NULL AS X_RegisteredRoad,
    NULL AS X_TownPlanningZone,
    NULL AS X_LandLocked,
    NULL AS X_CadastralReference,
    NULL AS X_IdealFor,
    NULL AS X_LicensedFor,
    NULL AS X_BusinessTransferOrSale,
    NULL AS X_BusinessTransferPrice,
    NULL AS X_BusinessActivity,
    NULL AS X_ConferenceRoom,
    NULL AS X_ServerRoom,
    NULL AS X_EnclosedOffice,
    NULL AS X_OfficeLayout,
    NULL AS X_PricePerSquare,
    NULL AS X_PriceQualifier,
    NULL AS X_PlusVAT,
    NULL AS X_MinimumTenancy,
    NULL AS X_TenancyType,
    NULL AS X_Occupancy,
    NULL AS X_PreviousListPrice,
    NULL AS X_PreviousLeasePrice,
    NULL AS X_ListPriceModified,
    NULL AS X_LeasePriceModified,
    CASE WHEN d.is_for_auction THEN 'true' ELSE NULL END AS X_AuctionStartDate,
    NULL AS X_AuctionEndDate,
    NULL AS X_ReservePrice,
    NULL AS X_StartingBid,
    NULL AS X_ProjectId,
    NULL AS X_DeveloperId,
    NULL AS X_Featured,
    NULL AS X_FeaturedPriority,
    NULL AS X_PropertyOfTheMonth,
    NULL AS X_VideoLink,
    NULL AS X_VirtualTourLink,
    d.listing_url                                 AS X_WebsiteUrl,
    NULL AS X_WebsiteStatus,
    NULL AS X_ShortDescription,
    d.name                                        AS X_PropertyName,
    NULL AS X_ApartmentType,
    NULL AS X_HouseType,
    NULL AS X_LandType,
    NULL AS X_OfficeType,
    NULL AS X_RetailType,
    NULL AS X_IndustrialType,
    NULL AS X_HotelType,
    NULL AS X_BuildingType,
    NULL AS X_InvestmentType,
    TRY_CAST(f.garage_spaces AS INT)              AS X_CustomerParking,
    f.general_features                            AS X_AdditionalFeatures,
    f.interior_features                           AS X_InteriorFeatures,
    COALESCE(f.exterior_features, f.exterior_description) AS X_ExteriorFeatures,
    f.community_features                          AS X_CommunityFeatures,
    f.lot_features                                AS X_LotFeatures,
    NULL AS X_SecurityFeatures,
    f.appliances                                  AS X_Appliances,

    -- ═══════════════════════════════════════════════════════════════════════════
    -- METADATA (Dash-specific)
    -- ═══════════════════════════════════════════════════════════════════════════
    d.dash_id                                     AS X_QobrixId,
    d.dash_ref                                    AS X_QobrixRef,
    d.dash_source                                 AS X_QobrixSource,
    NULL                                          AS X_QobrixLegacyId,
    NULL                                          AS X_QobrixSellerId,
    d.modified_ts                                 AS X_QobrixModified,

    -- Multi-tenant access control
    '{dash_office_key}'                           AS OriginatingSystemOfficeKey,
    'dash_sothebys'                               AS X_DataSource,

    -- ETL metadata
    CURRENT_TIMESTAMP()                           AS etl_timestamp,
    CONCAT('gold_batch_', CURRENT_DATE())         AS etl_batch_id

FROM dash_silver.property d
LEFT JOIN dash_silver.property_features f ON d.dash_id = f.property_id
"""

# COMMAND ----------

# Build the UNION query based on available sources
print("📊 Building unified gold table...")

if qobrix_available and dash_available:
    # Both sources available - UNION ALL
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.property AS
    {qobrix_select_sql}
    UNION ALL
    {dash_select_sql}
    """
    print("🔗 Using UNION ALL: Qobrix + Dash")
elif qobrix_available:
    # Only Qobrix
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.property AS
    {qobrix_select_sql}
    """
    print("📦 Using Qobrix only")
else:
    # Only Dash
    full_sql = f"""
    CREATE OR REPLACE TABLE reso_gold.property AS
    {dash_select_sql}
    """
    print("📦 Using Dash only")

spark.sql(full_sql)

# COMMAND ----------

# Verify results
gold_count = spark.sql("SELECT COUNT(*) AS c FROM reso_gold.property").collect()[0]["c"]
gold_cols = len(spark.table("reso_gold.property").columns)
print(f"✅ Gold RESO property records: {gold_count}")
print(f"✅ Gold RESO property columns: {gold_cols}")

# Show data source breakdown
print("\n📊 Records by data source:")
spark.sql("""
    SELECT X_DataSource, OriginatingSystemOfficeKey, COUNT(*) as count
    FROM reso_gold.property
    GROUP BY X_DataSource, OriginatingSystemOfficeKey
    ORDER BY X_DataSource
""").show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show sample records from each source
print("\n📋 Sample RESO Properties (combined):")
spark.sql("""
    SELECT ListingKey, ListingId, StandardStatus, PropertyType,
           BedroomsTotal, ListPrice, City, Country, 
           OriginatingSystemOfficeKey, X_DataSource
    FROM reso_gold.property
    LIMIT 10
""").show(truncate=False)

# Count fields by type
all_cols = spark.table("reso_gold.property").columns
extension_cols = [c for c in all_cols if c.startswith("X_")]
standard_cols = [c for c in all_cols if not c.startswith("X_") and not c.startswith("etl_")]
print(f"\n📊 RESO Standard fields: {len(standard_cols)}")
print(f"📊 Extension fields (X_): {len(extension_cols)}")
