# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Dash Features Parsing ETL
# MAGIC 
# MAGIC **Purpose:** Parses the `features` JSON column from bronze and aggregates features by group.
# MAGIC 
# MAGIC **Input:** `mls2.dash_bronze.properties` (features column as JSON string)
# MAGIC 
# MAGIC **Output:** `mls2.dash_silver.property_features` with:
# MAGIC - Property ID
# MAGIC - Aggregated feature columns by featureGroupDescription
# MAGIC - Maps to RESO DD 2.0 fields (Cooling, Heating, Pool, etc.)
# MAGIC 
# MAGIC **Run After:** load_dash_bronze.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

catalog = "mls2"
spark.sql(f"USE CATALOG {catalog}")

print("Using catalog:", catalog)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Check Bronze Data

# COMMAND ----------

try:
    bronze_count = spark.sql("SELECT COUNT(*) AS c FROM dash_bronze.properties").collect()[0]["c"]
    print(f"📊 Dash Bronze properties: {bronze_count}")
    if bronze_count == 0:
        print("⚠️ Dash Bronze empty, aborting features ETL.")
        dbutils.notebook.exit("No data to process")
except Exception as e:
    print(f"❌ Error reading dash bronze properties: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Parse Features JSON

# COMMAND ----------

# Ensure dash_silver schema exists
spark.sql("CREATE SCHEMA IF NOT EXISTS dash_silver")

# Parse features JSON and aggregate by feature group
# Each featureGroupDescription becomes a column with comma-separated featureDescriptions

parse_features_sql = """
CREATE OR REPLACE TABLE dash_silver.property_features AS
WITH features_exploded AS (
    SELECT 
        p.id AS property_id,
        f.featureCode AS feature_code,
        f.featureDescription AS feature_description,
        f.featureGroupCode AS feature_group_code,
        f.featureGroupDescription AS feature_group
    FROM dash_bronze.properties p
    LATERAL VIEW OUTER explode(
        from_json(p.features, 'array<struct<featureCode:string, featureDescription:string, featureGroupCode:string, featureGroupDescription:string>>')
    ) AS f
    WHERE p.features IS NOT NULL AND p.features != '' AND p.features != '[]'
),
features_aggregated AS (
    SELECT 
        property_id,
        feature_group,
        CONCAT_WS(', ', COLLECT_SET(feature_description)) AS features_list,
        COUNT(*) AS feature_count
    FROM features_exploded
    WHERE feature_description IS NOT NULL
    GROUP BY property_id, feature_group
)
SELECT
    fa.property_id,
    
    -- RESO Standard: Cooling
    MAX(CASE WHEN fa.feature_group = 'Cooling' THEN fa.features_list END) AS cooling_features,
    
    -- RESO Standard: Heating
    MAX(CASE WHEN fa.feature_group = 'Heating Type' THEN fa.features_list END) AS heating_features,
    
    -- Extension: Heating Fuel
    MAX(CASE WHEN fa.feature_group = 'Heating - Fuel Type' THEN fa.features_list END) AS heating_fuel,
    
    -- RESO Standard: PoolFeatures
    MAX(CASE WHEN fa.feature_group = 'Pool Description' THEN fa.features_list END) AS pool_features,
    
    -- RESO Standard: FireplaceFeatures
    MAX(CASE WHEN fa.feature_group = 'Fireplace Description' THEN fa.features_list END) AS fireplace_features,
    
    -- RESO Standard: FireplacesTotal (parse count from "Fireplace Count" group)
    MAX(CASE WHEN fa.feature_group = 'Fireplace Count' THEN fa.feature_count END) AS fireplaces_total,
    
    -- RESO Standard: ParkingFeatures (from Garage Description)
    MAX(CASE WHEN fa.feature_group = 'Garage Description' THEN fa.features_list END) AS garage_features,
    
    -- RESO Standard: GarageSpaces (parse count from "Garage Count" group)
    MAX(CASE WHEN fa.feature_group = 'Garage Count' THEN fa.feature_count END) AS garage_spaces,
    
    -- RESO Standard: Flooring
    MAX(CASE WHEN fa.feature_group = 'Flooring' THEN fa.features_list END) AS flooring,
    
    -- RESO Standard: View
    MAX(CASE WHEN fa.feature_group = 'Views' THEN fa.features_list END) AS view,
    
    -- RESO Standard: Fencing
    MAX(CASE WHEN fa.feature_group = 'Fencing' THEN fa.features_list END) AS fencing,
    
    -- RESO Standard: PatioAndPorchFeatures (from Exterior Living Space)
    MAX(CASE WHEN fa.feature_group = 'Exterior Living Space' THEN fa.features_list END) AS patio_porch_features,
    
    -- RESO Standard: ExteriorFeatures (combine Exterior + Exterior Description)
    MAX(CASE WHEN fa.feature_group = 'Exterior' THEN fa.features_list END) AS exterior_features,
    MAX(CASE WHEN fa.feature_group = 'Exterior Description' THEN fa.features_list END) AS exterior_description,
    
    -- RESO Standard: InteriorFeatures
    MAX(CASE WHEN fa.feature_group = 'Interior' THEN fa.features_list END) AS interior_features,
    
    -- RESO Standard: Appliances
    MAX(CASE WHEN fa.feature_group = 'Appliances' THEN fa.features_list END) AS appliances,
    
    -- Extension: KitchenFeatures
    MAX(CASE WHEN fa.feature_group = 'Kitchen Features' THEN fa.features_list END) AS kitchen_features,
    
    -- Extension: BathFeatures
    MAX(CASE WHEN fa.feature_group = 'Bath Features' THEN fa.features_list END) AS bath_features,
    
    -- RESO Standard: Basement
    MAX(CASE WHEN fa.feature_group = 'Basement' THEN fa.features_list END) AS basement,
    
    -- RESO Standard: Roof
    MAX(CASE WHEN fa.feature_group = 'Roof' THEN fa.features_list END) AS roof,
    
    -- RESO Standard: WaterSource
    MAX(CASE WHEN fa.feature_group = 'Water' THEN fa.features_list END) AS water_source,
    
    -- RESO Standard: Sewer
    MAX(CASE WHEN fa.feature_group = 'Sewer' THEN fa.features_list END) AS sewer,
    
    -- RESO Standard: Electric
    MAX(CASE WHEN fa.feature_group = 'Electrical' THEN fa.features_list END) AS electric,
    
    -- RESO Standard: LotFeatures (combine Lot Description + Lot Size)
    MAX(CASE WHEN fa.feature_group = 'Lot Description' THEN fa.features_list END) AS lot_features,
    
    -- RESO Standard: RoomType
    MAX(CASE WHEN fa.feature_group = 'Rooms' THEN fa.features_list END) AS room_type,
    
    -- RESO Standard: AssociationAmenities (from Amenities)
    MAX(CASE WHEN fa.feature_group = 'Amenities' THEN fa.features_list END) AS amenities,
    
    -- RESO Standard: WaterfrontFeatures (from Body of Water)
    MAX(CASE WHEN fa.feature_group = 'Body of Water' THEN fa.features_list END) AS waterfront_features,
    
    -- RESO Standard: RoadSurfaceType
    MAX(CASE WHEN fa.feature_group = 'Road Type' THEN fa.features_list END) AS road_surface,
    
    -- RESO Standard: PropertyCondition (from Age)
    MAX(CASE WHEN fa.feature_group = 'Age' THEN fa.features_list END) AS property_condition,
    
    -- RESO Standard: CommunityFeatures
    MAX(CASE WHEN fa.feature_group = 'Community Type' THEN fa.features_list END) AS community_features,
    
    -- Extension: Lifestyles
    MAX(CASE WHEN fa.feature_group = 'Lifestyles' THEN fa.features_list END) AS lifestyles,
    
    -- Extension: SpecialMarket
    MAX(CASE WHEN fa.feature_group = 'Special Market' THEN fa.features_list END) AS special_market,
    
    -- Extension: AreaAmenities
    MAX(CASE WHEN fa.feature_group = 'Area Amenities' THEN fa.features_list END) AS area_amenities,
    
    -- Extension: AreaDescription
    MAX(CASE WHEN fa.feature_group = 'Area Description' THEN fa.features_list END) AS area_description,
    
    -- Extension: General features
    MAX(CASE WHEN fa.feature_group = 'General' THEN fa.features_list END) AS general_features,
    
    -- Extension: Pre-Wiring
    MAX(CASE WHEN fa.feature_group = 'Pre-Wiring' THEN fa.features_list END) AS prewiring,
    
    -- Extension: PropertyDescription
    MAX(CASE WHEN fa.feature_group = 'Property Description' THEN fa.features_list END) AS property_description_features,
    
    -- Extension: Location
    MAX(CASE WHEN fa.feature_group = 'Location' THEN fa.features_list END) AS location_features,
    
    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp,
    CONCAT('dash_features_batch_', CURRENT_DATE()) AS etl_batch_id
    
FROM features_aggregated fa
GROUP BY fa.property_id
"""

print("📊 Parsing features JSON and creating aggregated table...")
spark.sql(parse_features_sql)

features_count = spark.sql("SELECT COUNT(*) AS c FROM dash_silver.property_features").collect()[0]["c"]
print(f"✅ Dash Silver property_features records: {features_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Verify Feature Groups Found

# COMMAND ----------

# Show all distinct feature groups found in the data
print("\n📋 Feature Groups Found in Data:")
spark.sql("""
    WITH features_exploded AS (
        SELECT 
            f.featureGroupDescription AS feature_group,
            f.featureDescription AS feature_description
        FROM dash_bronze.properties p
        LATERAL VIEW OUTER explode(
            from_json(p.features, 'array<struct<featureCode:string, featureDescription:string, featureGroupCode:string, featureGroupDescription:string>>')
        ) AS f
        WHERE p.features IS NOT NULL AND p.features != '' AND p.features != '[]'
    )
    SELECT 
        feature_group,
        COUNT(*) AS occurrences,
        COUNT(DISTINCT feature_description) AS unique_values
    FROM features_exploded
    WHERE feature_group IS NOT NULL
    GROUP BY feature_group
    ORDER BY occurrences DESC
""").show(50, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show sample data
print("\n📋 Sample Property Features:")
spark.sql("""
    SELECT 
        property_id,
        cooling_features,
        heating_features,
        pool_features,
        view,
        flooring,
        appliances,
        garage_features
    FROM dash_silver.property_features
    LIMIT 5
""").show(truncate=False)

# Column count
cols = spark.table("dash_silver.property_features").columns
print(f"\n📊 Dash Silver property_features columns: {len(cols)}")
print(f"Columns: {', '.join(cols)}")

