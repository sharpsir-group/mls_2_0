# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Export: HomeOverseas.ru XML Feed (V4)
# MAGIC 
# MAGIC **Purpose:** Maps RESO gold property + media data to the HomeOverseas V4 XML feed schema
# MAGIC and writes the result to an export staging table.
# MAGIC 
# MAGIC **Input:**
# MAGIC - `<uc_catalog>.reso_gold.property` (filtered for Cyprus, Active)
# MAGIC - `<uc_catalog>.reso_gold.media` (photos only)
# MAGIC - `<uc_catalog>.qobrix_bronze.property_translations_ru` (Russian translations)
# MAGIC 
# MAGIC **Output:** `<uc_catalog>.exports.homesoverseas` — one row per property with all HomeOverseas fields
# MAGIC 
# MAGIC **Stable IDs:** Uses `<uc_catalog>.exports.homesoverseas_id_map` to assign persistent integer `objectid`
# MAGIC values that survive across runs.
# MAGIC 
# MAGIC **Spec:** HomeOverseas.ru XML Feed Technical Requirements V4 (1.05.2023)
# MAGIC 
# MAGIC **Run After:** 03_gold_reso_property_etl.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os
from pyspark.sql.functions import col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

dbutils.widgets.text("DATABRICKS_CATALOG", "mls2")
catalog = (os.getenv("DATABRICKS_CATALOG") or dbutils.widgets.get("DATABRICKS_CATALOG") or "mls2").strip() or "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql("CREATE SCHEMA IF NOT EXISTS exports")

# Cyprus office key filter
dbutils.widgets.text("OFFICE_KEY", "SHARPSIR-CY-001")
office_key = os.getenv("SRC_1_OFFICE_KEY") or dbutils.widgets.get("OFFICE_KEY") or "SHARPSIR-CY-001"

# HomeOverseas region ID for Cyprus (fallback when city/district not mapped)
dbutils.widgets.text("HOMESOVERSEAS_CYPRUS_REGION_ID", "73")
cyprus_region_id = os.getenv("HOMESOVERSEAS_CYPRUS_REGION_ID") or dbutils.widgets.get("HOMESOVERSEAS_CYPRUS_REGION_ID") or "73"

print("=" * 80)
print("EXPORT: HomeOverseas.ru XML Feed V4")
print("=" * 80)
print(f"Office Key filter: {office_key}")
print(f"Cyprus Region ID:  {cyprus_region_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Verify Source Data

# COMMAND ----------

prop_count = spark.sql(f"""
    SELECT COUNT(*) AS c FROM reso_gold.property
    WHERE OriginatingSystemOfficeKey = '{office_key}'
      AND StandardStatus = 'Active'
""").collect()[0]["c"]
print(f"Active Cyprus properties in gold: {prop_count}")

media_count = spark.sql(f"""
    SELECT COUNT(*) AS c FROM reso_gold.media
    WHERE OriginatingSystemOfficeKey = '{office_key}'
      AND MediaCategory = 'Photo'
""").collect()[0]["c"]
print(f"Photo media items in gold: {media_count}")

if prop_count == 0:
    print("No active properties found — nothing to export.")
    dbutils.notebook.exit("No data")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Stable objectid Mapping

# COMMAND ----------

spark.sql("""
    CREATE TABLE IF NOT EXISTS exports.homesoverseas_id_map (
        listing_key STRING,
        objectid INT
    )
    USING DELTA
""")

# Find new listing keys that don't yet have an objectid and assign IDs in two steps
# Step 2a: Compute the current max objectid
max_id_row = spark.sql("SELECT COALESCE(MAX(objectid), 0) AS max_id FROM exports.homesoverseas_id_map").collect()
current_max_id = max_id_row[0]["max_id"]

# Step 2b: Find new keys not yet mapped, assign sequential IDs, and insert
new_keys_df = spark.sql(f"""
    SELECT DISTINCT p.ListingKey
    FROM reso_gold.property p
    LEFT JOIN exports.homesoverseas_id_map m ON p.ListingKey = m.listing_key
    WHERE p.OriginatingSystemOfficeKey = '{office_key}'
      AND p.StandardStatus = 'Active'
      AND m.listing_key IS NULL
    ORDER BY p.ListingKey
""")

new_keys_count = new_keys_df.count()
if new_keys_count > 0:
    from pyspark.sql.window import Window
    from pyspark.sql import functions as F

    w = Window.orderBy("ListingKey")
    new_ids_df = (
        new_keys_df
        .withColumn("objectid", (F.row_number().over(w) + F.lit(current_max_id)).cast("int"))
        .withColumnRenamed("ListingKey", "listing_key")
    )
    new_ids_df.write.mode("append").format("delta").saveAsTable("exports.homesoverseas_id_map")
    print(f"Assigned {new_keys_count} new objectid mappings (starting from {current_max_id + 1})")
else:
    print("No new listing keys to map")

id_count = spark.sql("SELECT COUNT(*) AS c FROM exports.homesoverseas_id_map").collect()[0]["c"]
print(f"Total objectid mappings: {id_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Aggregate Photos (up to 15 per property)

# COMMAND ----------

spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW _ho_photos AS
    SELECT
        ResourceRecordKey,
        COLLECT_LIST(MediaURL) AS photo_urls
    FROM (
        SELECT
            ResourceRecordKey,
            MediaURL,
            ROW_NUMBER() OVER (PARTITION BY ResourceRecordKey ORDER BY COALESCE(TRY_CAST(`Order` AS INT), 9999)) AS rn
        FROM reso_gold.media
        WHERE OriginatingSystemOfficeKey = '{office_key}'
          AND MediaCategory = 'Photo'
          AND MediaURL IS NOT NULL
          AND MediaURL != ''
    )
    WHERE rn <= 15
    GROUP BY ResourceRecordKey
""")

photo_stats = spark.sql("SELECT COUNT(*) AS properties_with_photos FROM _ho_photos").collect()[0]["properties_with_photos"]
print(f"Properties with photos: {photo_stats}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — HomeOverseas Location Mapping
# MAGIC 
# MAGIC Maps English city names from Qobrix/RESO `City` field to HomeOverseas taxonomy IDs.
# MAGIC 
# MAGIC **Strategy:**
# MAGIC 1. Try matching `City` → city-level ID (most specific)
# MAGIC 2. Fall back to matching `StateOrProvince` → district-level ID
# MAGIC 3. Final fallback → 73 (Cyprus country-level)
# MAGIC 
# MAGIC City names are matched case-insensitively. To add new cities, extend the mapping lists below.

# COMMAND ----------

# City-level mapping: English city name (lowercase) -> HomeOverseas city ID
ho_city_data = [
    # --- Ayia Napa region (74) ---
    ("avgora", 2478),
    ("ayia napa", 397), ("agia napa", 397), ("aiya napa", 397),
    ("ayia thekla", 2829), ("agia thekla", 2829), ("ayia tekla", 2829),
    ("vrysoulles", 2477), ("vrysoules", 2477),
    ("deryneia", 2475), ("derynia", 2475),
    ("kapparis", 2825), ("kaparis", 2825),
    ("xylophagou", 430), ("xylofagou", 430),
    ("liopetri", 2480),
    ("paralimni", 396), ("paralimini", 396),
    ("protaras", 158), ("proteras", 158),
    ("sotira", 2476),
    ("frenaros", 2479),

    # --- Larnaca region (75) ---
    ("alethriko", 2840),
    ("zygi", 3408),
    ("kiti", 3164),
    ("larnaca", 431), ("larnaka", 431),
    ("mazatos", 3258), ("mazotos", 3258),
    ("meneou", 724),
    ("oroklini", 422), ("voroklini", 422),
    ("pervolia", 725), ("perivolia", 725),
    ("pyla", 423),

    # --- Limassol region (76) ---
    ("agios athanasios", 2718), ("ayios athanasios", 2718), ("ag. athanasios", 2718),
    ("agios tychonas", 398), ("agios tychon", 398), ("ayios tychonas", 398),
    ("ag. tychonas", 398),
    ("germasogeia", 399), ("germasogia", 399), ("yermasoyia", 399),
    ("ypsonas", 2824), ("ipsonas", 2824),
    ("kalo chorio", 686), ("kalogiri", 686),
    ("limassol", 400), ("lemesos", 400),
    ("mesa geitonia", 3221), ("mesa gitonia", 3221),
    ("monagroulli", 2835), ("monagrouli", 2835),
    ("mouttagiaka", 3212), ("moutagiaka", 3212), ("muttayaka", 3212),
    ("palodia", 2717), ("palodeia", 2717), ("palodja", 2717),
    ("parekklisia", 3001), ("pareklisia", 3001), ("parekklissia", 3001),
    ("pyrgos", 685), ("pyrgos limassol", 685),
    ("pissouri", 402),
    ("platres", 3155), ("pano platres", 3155),
    ("souni", 723), ("souni-zanakia", 723),
    ("erimi", 967),

    # --- Nicosia (2390) ---
    ("nicosia", 2390), ("lefkosia", 2390),

    # --- Paphos region (77) ---
    ("aphrodite hills", 424),
    ("secret valley", 2376),
    ("st. george", 2894), ("st george", 2894), ("saint george", 2894),
    ("agios georgios", 2894),
    ("anavargos", 3082), ("anavargas", 3082),
    ("anarita", 425),
    ("armou", 3363),
    ("geroskipou", 403), ("yeroskipou", 403),
    # Note: "kamares" omitted — exists in both Paphos (HO 429) and Larnaca; district fallback handles it
    ("kathikas", 428),
    ("kato paphos", 409), ("kato pafos", 409), ("lower paphos", 409),
    ("kissonerga", 404), ("kissonearga", 404),
    ("konia", 405),
    ("coral bay", 406), ("corallia", 406),
    ("kouklia", 407),
    ("mandria", 408),
    ("marathounda", 3170), ("marathunda", 3170),
    ("mesa chorio", 2903),
    ("mesogi", 2877), ("mesoyi", 2877),
    ("pano paphos", 410), ("upper paphos", 410), ("pano pafos", 410),
    ("paphos", 77), ("pafos", 77),
    ("peyia", 411), ("pegeia", 411), ("pegia", 411),
    ("sea caves", 426),
    ("tala", 413),
    ("tremithousa", 2878), ("tremithusa", 2878),
    ("chloraka", 414), ("chlorakas", 414),
    ("tsada", 412),
    ("emba", 427), ("empa", 427),

    # --- Polis region (80) ---
    ("argaka", 415),
    ("latchi", 416), ("latsi", 416), ("lakki", 416),
    ("neo chorio", 417),
    ("polis", 418), ("polis chrysochous", 418),
    ("prodromi", 2904), ("prodhromi", 2904),
    ("pomos", 419), ("pommos", 419),

    # --- Northern Cyprus (1611) ---
    ("alsancak", 2831),
    ("bafra", 3632),
    ("bahceli", 3680),
    ("bogaz", 3620), ("boghaz", 3620),
    ("gaziveren", 2907),
    ("guzelyurt", 3677), ("morphou", 3677),
    ("iskele", 2893),
    ("karaoglanoglu", 3715),
    ("karsiyaka", 3691),
    ("kyrenia", 2068), ("girne", 2068),
    ("lapta", 3398),
    ("lefka", 3399), ("lefke", 3399),
    ("north nicosia", 3369),
    ("tatlisu", 2830),
    ("famagusta", 2067), ("gazimagusa", 2067), ("magosa", 2067),
    ("catalkoy", 3397),
    ("esentepe", 3364),

    # --- Troodos (421) ---
    ("troodos", 421),

    # --- Additional city names / sub-areas from Qobrix data ---
    # (mapped to nearest HomeOverseas parent entry)

    # Larnaca sub-areas -> Larnaca city (431)
    ("makenzy", 431), ("mackenzie", 431),
    ("harbor", 431), ("harbour", 431),
    ("finikoudes", 431), ("phinikoudes", 431),
    ("skala", 431),
    ("chrysopolitissa", 431),
    # kamares: handled by district fallback (ambiguous — Larnaca vs Paphos)
    ("drosia", 431),
    ("agioi anargyroi i", 431), ("agioi anargyroi ii", 431),
    ("agioi anargyroi", 431),
    ("sotiros", 431),
    ("tsakilero", 431),
    ("dekeleia", 431),
    ("dromolaxia", 431),
    ("maroni", 431),

    # Limassol sub-areas -> Limassol city (400)
    ("historical center", 400), ("historic center", 400),
    ("limassol marina", 400),
    ("kapsalos", 400),
    ("neapolis", 400),
    ("panthea", 400),
    ("agia zoni", 400),
    ("agios ioannis", 400),
    ("omonia", 400),
    ("apostolos andreas", 400),
    ("linopetra", 400),
    ("tsiflikoudia", 400),
    ("trachoni", 400),
    ("agios nektarios", 400),
    ("ekali", 400),
    ("tserkez tsiftlik (tserkezoi)", 400), ("tserkez tsiftlik", 400),
    ("asomatos", 400),
    ("kolossi", 400),
    ("armenochori", 400),
    ("akrounta", 400),

    # Germasogeia sub-areas -> Germasogeia (399)
    ("potamos germasogeias", 399), ("potamos germasogeia", 399),
    ("germasogeia tourist area", 399),

    # Agios Tychonas sub-areas -> Agios Tychonas (398)
    ("agios tychon tourist area", 398),

    # Mouttagiaka sub-areas -> Mouttagiaka (3212)
    ("mouttagiaka tourist area", 3212),

    # Pyrgos sub-areas -> Pyrgos Limassol (685)
    ("pyrgos tourist area", 685),

    # Oroklini sub-areas -> Oroklini (422)
    ("oroklini tourist area", 422),

    # Geroskipou sub-areas -> Geroskipou (403)
    ("geroskipou tourist area", 403),

    # Kato Paphos sub-areas -> Kato Paphos (409)
    ("tombs of the kings", 409),
    ("universal", 409),
    ("moutallos", 409),
    ("koloni", 409),

    # Paphos misc -> Paphos region (77)
    ("agia marinouda", 77),
    ("agios theodoros", 77),

    # Aphrodite Hills variants -> (424)
    ("aphrodite hills kouklia", 424),

    # Famagusta sub-areas
    ("pernera", 158),  # near Protaras
    ("agia triada", 396),  # near Paralimni

    # Nicosia sub-areas -> Nicosia (2390)
    ("strovolos", 2390),
    ("aglantzia", 2390), ("aglandjia", 2390),
    ("lykabittos", 2390), ("lycavittos", 2390),
    ("agios dometios", 2390),
    ("ag. antonios", 2390),
    ("trypiotis", 2390),
    ("egkomi", 2390), ("engomi", 2390),
    ("latsia", 2390),
    ("palaiometocho", 2390),
]

# District-level mapping: district/state name (lowercase) -> HomeOverseas district ID
ho_district_data = [
    ("ayia napa", 74), ("agia napa", 74),
    ("famagusta", 74), ("ammochostos", 74), ("free famagusta", 74),
    ("larnaca", 75), ("larnaka", 75), ("larnaca district", 75),
    ("limassol", 76), ("lemesos", 76), ("limassol district", 76),
    ("nicosia", 2390), ("lefkosia", 2390), ("nicosia district", 2390),
    ("paphos", 77), ("pafos", 77), ("paphos district", 77),
    ("polis", 80), ("polis chrysochous", 80),
    ("kyrenia", 1611), ("girne", 1611), ("northern cyprus", 1611),
    ("troodos", 421),
]

# Create Spark temp views for SQL JOINs
city_schema = StructType([
    StructField("name_lower", StringType(), False),
    StructField("ho_id", IntegerType(), True),
])

spark.createDataFrame(ho_city_data, city_schema).createOrReplaceTempView("_ho_city_map")
spark.createDataFrame(ho_district_data, city_schema).createOrReplaceTempView("_ho_district_map")

print(f"City-level mappings:     {len(ho_city_data)} entries")
print(f"District-level mappings: {len(ho_district_data)} entries")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Load Russian Translations from Bronze
# MAGIC 
# MAGIC Reads pre-fetched Russian translations from `qobrix_bronze.property_translations_ru`.
# MAGIC This table is populated by the bronze layer notebooks (full refresh and CDC).
# MAGIC 
# MAGIC Maps bronze property `id` to `ListingKey` via `CONCAT('QOBRIX_', id)`.

# COMMAND ----------

tr_schema = StructType([
    StructField("ListingKey", StringType(), False),
    StructField("name_ru", StringType(), True),
    StructField("description_ru", StringType(), True),
    StructField("shortdescription_ru", StringType(), True),
])

# Check if the bronze translations table exists
try:
    tr_count_check = spark.sql("SELECT COUNT(*) FROM qobrix_bronze.property_translations_ru").collect()[0][0]
    has_translations = tr_count_check > 0
except Exception:
    has_translations = False

if not has_translations:
    print("WARNING: qobrix_bronze.property_translations_ru not found or empty.")
    print("         Run bronze pipeline first to populate Russian translations.")
    spark.createDataFrame([], tr_schema).createOrReplaceTempView("_ho_translations_ru")
else:
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _ho_translations_ru AS
        SELECT
            CONCAT('QOBRIX_', id) AS ListingKey,
            COALESCE(name, '') AS name_ru,
            COALESCE(description, '') AS description_ru,
            COALESCE(short_description, '') AS shortdescription_ru
        FROM qobrix_bronze.property_translations_ru
    """)

tr_count = spark.sql("SELECT COUNT(*) AS c FROM _ho_translations_ru WHERE name_ru != '' OR description_ru != ''").collect()[0]["c"]
print(f"Properties with Russian translations: {tr_count} (from qobrix_bronze.property_translations_ru)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — Build Export Table

# COMMAND ----------

export_sql = f"""
CREATE OR REPLACE TABLE exports.homesoverseas AS

SELECT
    -- =====================================================================
    -- MANDATORY FIELDS
    -- =====================================================================
    idm.objectid,
    SUBSTR(COALESCE(p.ListingId, ''), 1, 60) AS ref,

    -- title (max 60 chars)
    SUBSTR(COALESCE(
        NULLIF(p.X_PropertyName, ''),
        NULLIF(p.PublicRemarks, ''),
        CONCAT(COALESCE(p.PropertyType, 'Property'), ' in ', COALESCE(p.City, 'Cyprus'))
    ), 1, 60) AS title_en,

    -- title_ru from Qobrix translations
    SUBSTR(COALESCE(NULLIF(tr.name_ru, ''), ''), 1, 60) AS title_ru,

    -- type: sale or rent
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') THEN 'rent'
        ELSE 'sale'
    END AS listing_type,

    -- market: primary / secondary
    -- RESO 2.0 NewConstructionYN is the primary industry filter (Bridge /
    -- Trestle / Spark / SimplyRETS); fall back to DevelopmentStatus and the
    -- legacy X_NewBuild extension only when NewConstructionYN is undetermined.
    CASE
        WHEN p.NewConstructionYN = TRUE                                         THEN 'primary'
        WHEN p.NewConstructionYN = FALSE                                        THEN 'secondary'
        WHEN p.DevelopmentStatus IN ('Proposed','Under Construction','New Construction') THEN 'primary'
        WHEN p.DevelopmentStatus = 'Existing'                                   THEN 'secondary'
        WHEN LOWER(COALESCE(p.X_NewBuild, '')) = 'true'                         THEN 'primary'
        ELSE 'secondary'
    END AS market,

    -- price
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') THEN NULL
        ELSE COALESCE(TRY_CAST(p.ListPrice AS BIGINT), 0)
    END AS sale_price,
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') AND LOWER(COALESCE(p.LeaseAmountFrequency, '')) = 'daily'
        THEN TRY_CAST(p.LeasePrice AS BIGINT)
        ELSE NULL
    END AS rent_day,
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') AND LOWER(COALESCE(p.LeaseAmountFrequency, '')) = 'weekly'
        THEN TRY_CAST(p.LeasePrice AS BIGINT)
        ELSE NULL
    END AS rent_week,
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') AND LOWER(COALESCE(p.LeaseAmountFrequency, '')) = 'monthly'
        THEN TRY_CAST(p.LeasePrice AS BIGINT)
        ELSE NULL
    END AS rent_month,
    CASE
        WHEN p.PropertyClass IN ('RLSE', 'COML') AND LOWER(COALESCE(p.LeaseAmountFrequency, '')) = 'annually'
        THEN TRY_CAST(p.LeasePrice AS BIGINT)
        ELSE NULL
    END AS rent_year,

    'eur' AS currency,

    -- region: city-level ID -> district-level ID -> fallback to Cyprus (73)
    COALESCE(cm.ho_id, dm.ho_id, {cyprus_region_id}) AS region,

    -- realty_type mapping
    CASE
        WHEN p.PropertyType = 'Apartment' AND LOWER(COALESCE(p.X_ApartmentType, '')) LIKE '%penthouse%' THEN 28
        WHEN p.PropertyType = 'Apartment' AND LOWER(COALESCE(p.X_ApartmentType, '')) LIKE '%loft%' THEN 29
        WHEN p.PropertyType = 'Apartment' AND LOWER(COALESCE(p.X_ApartmentType, '')) LIKE '%studio%' THEN 35
        WHEN p.PropertyType = 'Apartment' THEN 16
        WHEN p.PropertyType = 'SingleFamilyDetached' AND LOWER(COALESCE(p.X_HouseType, '')) LIKE '%chalet%' THEN 31
        WHEN p.PropertyType = 'SingleFamilyDetached' AND LOWER(COALESCE(p.X_HouseType, '')) LIKE '%bungalow%' THEN 32
        WHEN p.PropertyType = 'SingleFamilyDetached' THEN 17
        WHEN p.PropertyType = 'Land' THEN 15
        WHEN p.PropertyType = 'Office' THEN 23
        WHEN p.PropertyType = 'Parking' THEN 26
        WHEN p.PropertyType = 'Commercial' AND p.X_HotelType IS NOT NULL AND p.X_HotelType != '' THEN 20
        WHEN p.PropertyType = 'Commercial' AND p.X_RetailType IS NOT NULL AND p.X_RetailType != '' THEN 22
        WHEN p.PropertyType = 'Commercial' AND p.X_IndustrialType IS NOT NULL AND p.X_IndustrialType != '' THEN 25
        WHEN p.PropertyType = 'Commercial' THEN 14
        WHEN p.PropertySubType = 'Townhouse' THEN 18
        ELSE 26
    END AS realty_type,

    -- =====================================================================
    -- OPTIONAL DETAIL FIELDS
    -- =====================================================================
    TRY_CAST(p.BedroomsTotal AS INT) AS bedrooms,
    TRY_CAST(p.LivingArea AS DECIMAL(18,2)) AS size_house,
    TRY_CAST(p.LotSizeSquareFeet AS DECIMAL(18,2)) AS size_land,
    TRY_CAST(p.YearBuilt AS INT) AS year_built,
    TRY_CAST(p.Stories AS INT) AS level,
    TRY_CAST(p.StoriesTotal AS INT) AS levels,
    TRY_CAST(p.X_DistanceFromAirport AS DECIMAL(10,1)) AS distance_aero,
    TRY_CAST(p.X_DistanceFromBeach AS DECIMAL(10,3)) AS distance_sea,

    -- coordinates
    p.Latitude AS lat,
    p.Longitude AS lng,

    -- annotation_en (max 150 chars)
    SUBSTR(COALESCE(
        NULLIF(p.X_ShortDescription, ''),
        NULLIF(p.PublicRemarks, ''),
        ''
    ), 1, 150) AS annotation_en,

    -- annotation_ru from Qobrix translations (max 150 chars)
    SUBSTR(COALESCE(NULLIF(tr.shortdescription_ru, ''), ''), 1, 150) AS annotation_ru,

    -- description_en (max 65536 chars)
    SUBSTR(COALESCE(p.PublicRemarks, ''), 1, 65536) AS description_en,

    -- description_ru from Qobrix translations (max 65536 chars)
    SUBSTR(COALESCE(NULLIF(tr.description_ru, ''), ''), 1, 65536) AS description_ru,

    -- =====================================================================
    -- OPTIONS (computed as array of integer IDs)
    -- =====================================================================
    CONCAT_WS(',',
        CASE WHEN LOWER(COALESCE(p.X_BeachFront, '')) = 'true' THEN '7' ELSE NULL END,
        CASE WHEN LOWER(COALESCE(p.X_SeaView, '')) = 'true' THEN '6' ELSE NULL END,
        CASE WHEN LOWER(COALESCE(p.X_MountainView, '')) = 'true' THEN '5' ELSE NULL END,
        CASE WHEN p.PoolFeatures IS NOT NULL AND p.PoolFeatures != '' THEN '19'
             WHEN LOWER(COALESCE(p.X_PrivateSwimmingPool, '')) = 'true' THEN '19'
             WHEN LOWER(COALESCE(p.X_CommonSwimmingPool, '')) = 'true' THEN '19'
             ELSE NULL END,
        CASE WHEN p.FireplaceYN = true THEN '12' ELSE NULL END,
        CASE WHEN LOWER(COALESCE(p.X_SmartHome, '')) = 'true' THEN '15' ELSE NULL END,
        CASE WHEN p.Heating IS NOT NULL AND p.Heating != '' THEN '17' ELSE NULL END,
        CASE WHEN p.Cooling IS NOT NULL AND p.Cooling != ''
                  OR LOWER(COALESCE(p.X_AirCondition, '')) = 'true' THEN '18' ELSE NULL END,
        CASE WHEN p.ParkingFeatures IS NOT NULL AND LOWER(p.ParkingFeatures) LIKE '%covered%' THEN '33'
             WHEN p.ParkingFeatures IS NOT NULL AND LOWER(p.ParkingFeatures) LIKE '%garage%' THEN '33'
             WHEN p.ParkingFeatures IS NOT NULL AND p.ParkingFeatures != '' THEN '23'
             ELSE NULL END,
        CASE WHEN LOWER(COALESCE(p.X_StorageSpace, '')) = 'true' THEN '49' ELSE NULL END,
        CASE WHEN p.PatioAndPorchFeatures IS NOT NULL AND p.PatioAndPorchFeatures != '' THEN '35' ELSE NULL END,
        CASE WHEN LOWER(COALESCE(p.X_Elevator, '')) = 'true' THEN '34' ELSE NULL END
    ) AS options_csv,

    -- =====================================================================
    -- PHOTOS (JSON array of URLs, up to 15)
    -- =====================================================================
    COALESCE(ph.photo_urls, ARRAY()) AS photo_urls,

    -- =====================================================================
    -- VIDEO
    -- =====================================================================
    p.X_VideoLink AS video_link,
    p.X_VirtualTourLink AS virtual_tour_link,

    -- price_from flag
    CASE WHEN COALESCE(TRY_CAST(p.ListPrice AS BIGINT), 0) = 0
              AND p.PropertyClass NOT IN ('RLSE', 'COML')
         THEN 'N' ELSE 'N' END AS price_from,

    -- developer flag
    CASE
        WHEN p.DevelopmentStatus IN ('Proposed', 'Under Construction') THEN 'Y'
        WHEN LOWER(COALESCE(p.X_NewBuild, '')) = 'true' THEN 'Y'
        ELSE 'N'
    END AS developer_flag,

    -- location context (for debugging / future use)
    p.City AS city_name,
    p.StateOrProvince AS district_name,

    -- source keys for traceability
    p.ListingKey,
    p.X_DataSource,

    -- date listing was created (for feed sorting: newest first)
    p.ListingContractDate AS listing_created_date,

    -- ETL metadata
    CURRENT_TIMESTAMP() AS etl_timestamp

FROM reso_gold.property p
INNER JOIN exports.homesoverseas_id_map idm
    ON p.ListingKey = idm.listing_key
LEFT JOIN _ho_photos ph
    ON p.ListingKey = ph.ResourceRecordKey
LEFT JOIN _ho_translations_ru tr
    ON p.ListingKey = tr.ListingKey
LEFT JOIN _ho_city_map cm
    ON LOWER(TRIM(p.City)) = cm.name_lower
LEFT JOIN _ho_district_map dm
    ON LOWER(TRIM(p.StateOrProvince)) = dm.name_lower
WHERE p.OriginatingSystemOfficeKey = '{office_key}'
  AND p.StandardStatus = 'Active'
"""

print("Building HomeOverseas export table...")
spark.sql(export_sql)

export_count = spark.sql("SELECT COUNT(*) AS c FROM exports.homesoverseas").collect()[0]["c"]
print(f"HomeOverseas export records: {export_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\nExport Summary:")
print("-" * 50)

# By realty type
print("\nBy Realty Type:")
spark.sql("""
    SELECT realty_type, COUNT(*) as count
    FROM exports.homesoverseas
    GROUP BY realty_type
    ORDER BY count DESC
""").show()

# By listing type
print("\nBy Listing Type:")
spark.sql("""
    SELECT listing_type, COUNT(*) as count
    FROM exports.homesoverseas
    GROUP BY listing_type
""").show()

# Photos coverage
print("\nPhoto Coverage:")
spark.sql("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN SIZE(photo_urls) > 0 THEN 1 ELSE 0 END) AS with_photos,
        ROUND(100.0 * SUM(CASE WHEN SIZE(photo_urls) > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
    FROM exports.homesoverseas
""").show()

# Russian translations coverage
print("\nRussian Translation Coverage:")
spark.sql("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN title_ru IS NOT NULL AND title_ru != '' THEN 1 ELSE 0 END) AS with_title_ru,
        SUM(CASE WHEN description_ru IS NOT NULL AND description_ru != '' THEN 1 ELSE 0 END) AS with_desc_ru,
        SUM(CASE WHEN annotation_ru IS NOT NULL AND annotation_ru != '' THEN 1 ELSE 0 END) AS with_annot_ru
    FROM exports.homesoverseas
""").show()

# Location mapping coverage
print("\nLocation Mapping Coverage:")
spark.sql(f"""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN region != {cyprus_region_id} THEN 1 ELSE 0 END) AS mapped_to_city_or_district,
        SUM(CASE WHEN region = {cyprus_region_id} THEN 1 ELSE 0 END) AS fallback_to_country,
        COUNT(DISTINCT region) AS distinct_regions
    FROM exports.homesoverseas
""").show()

# Show unmapped cities (if any) for future mapping updates
print("\nUnmapped Cities (fallback to country-level):")
spark.sql(f"""
    SELECT city_name, district_name, COUNT(*) as count
    FROM exports.homesoverseas
    WHERE region = {cyprus_region_id}
      AND city_name IS NOT NULL AND city_name != ''
    GROUP BY city_name, district_name
    ORDER BY count DESC
    LIMIT 20
""").show(truncate=False)

# Sample rows
print("\nSample Export Rows:")
spark.sql("""
    SELECT objectid, ref, listing_type, realty_type, sale_price, currency, region,
           bedrooms, size_house, SIZE(photo_urls) AS num_photos,
           CASE WHEN title_ru != '' THEN 'Y' ELSE 'N' END AS has_ru,
           city_name
    FROM exports.homesoverseas
    LIMIT 10
""").show(truncate=False)

print("\n" + "=" * 80)
print(f"HomeOverseas Export Complete: {export_count} properties")
print("=" * 80)
