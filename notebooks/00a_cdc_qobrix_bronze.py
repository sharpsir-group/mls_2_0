# Databricks notebook source
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# COMMAND ----------

# MAGIC %md
# MAGIC # MLS 2.0 - Qobrix CDC -> Bronze Layer (Incremental)
# MAGIC 
# MAGIC **Purpose:** Fetches ONLY changed property data from Qobrix API since last sync.
# MAGIC 
# MAGIC **How it works:**
# MAGIC 1. Reads last sync timestamp from `cdc_metadata` table
# MAGIC 2. Queries Qobrix API for records modified since that timestamp
# MAGIC 3. MERGEs changed records into bronze tables (insert/update)
# MAGIC 4. Updates metadata with new sync timestamp
# MAGIC 
# MAGIC **Tables Updated (Every CDC Run):**
# MAGIC | Table | Method |
# MAGIC |-------|--------|
# MAGIC | `properties` | Incremental (`modified >= last_sync`) |
# MAGIC | `agents` | Incremental (`modified >= last_sync`) |
# MAGIC | `contacts` | Incremental (`modified >= last_sync`) |
# MAGIC | `viewings` | Incremental (`modified >= last_sync`) |
# MAGIC | `opportunities` | Incremental (`modified >= last_sync`) |
# MAGIC | `property_media` | Re-fetched for changed properties |
# MAGIC | `users` | Incremental (`modified >= last_sync`) |
# MAGIC | `projects` | Incremental (`modified >= last_sync`) |
# MAGIC | `project_features` | Incremental (`modified >= last_sync`) |
# MAGIC | `property_types` | Incremental (`modified >= last_sync`) |
# MAGIC | `property_subtypes` | Incremental (`modified >= last_sync`) |
# MAGIC | `locations` | Incremental (`modified >= last_sync`) |
# MAGIC | `media_categories` | Incremental (`modified >= last_sync`) |
# MAGIC | `portal_locations` | Skipped (static lookups, full refresh only) |
# MAGIC 
# MAGIC **When to use:**
# MAGIC - Regular sync (every 15-30 min): Run this notebook
# MAGIC - Initial load or recovery: Run 00_full_refresh_qobrix_bronze.py
# MAGIC 
# MAGIC **Credentials:** Requires `QOBRIX_API_USER`, `QOBRIX_API_KEY`, `QOBRIX_API_BASE_URL`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os
import requests
import pandas as pd
import json as _json
from datetime import datetime, timedelta
from pyspark.sql.functions import lit, current_timestamp

catalog = "mls2"
schema = "qobrix_bronze"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

timeout_seconds = 30

# Widgets for credentials (can be passed via job parameters)
dbutils.widgets.text("QOBRIX_API_USER", "")
dbutils.widgets.text("QOBRIX_API_KEY", "")
dbutils.widgets.text("QOBRIX_API_BASE_URL", "")

# Priority: env vars > widgets > empty (will fail validation)
qobrix_api_user = os.getenv("QOBRIX_API_USER") or dbutils.widgets.get("QOBRIX_API_USER")
qobrix_api_key = os.getenv("QOBRIX_API_KEY") or dbutils.widgets.get("QOBRIX_API_KEY")
api_base_url = os.getenv("QOBRIX_API_BASE_URL") or dbutils.widgets.get("QOBRIX_API_BASE_URL")

if not qobrix_api_user or not qobrix_api_key or not api_base_url:
    raise ValueError("Set QOBRIX_API_USER, QOBRIX_API_KEY, and QOBRIX_API_BASE_URL (env vars or widgets) before running.")

headers = {
    "X-Api-User": qobrix_api_user,
    "X-Api-Key": qobrix_api_key,
}

print("=" * 80)
print("🔄 CDC MODE - Incremental Sync")
print("=" * 80)

# Track changes for each entity (used to determine which Silver/Gold ETLs to run)
cdc_changes = {
    "properties": 0,
    "agents": 0,
    "contacts": 0,
    "viewings": 0,
    "opportunities": 0,
    "media": 0,
    "users": 0,
    "projects": 0,
    "project_features": 0,
    "property_types": 0,
    "property_subtypes": 0,
    "locations": 0,
    "media_categories": 0,
    "portal_locations": 0
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC Metadata Table

# COMMAND ----------

# Create CDC metadata table if not exists
spark.sql("""
    CREATE TABLE IF NOT EXISTS cdc_metadata (
        entity_name STRING,
        last_sync_timestamp TIMESTAMP,
        last_modified_timestamp STRING,
        records_processed INT,
        sync_status STRING,
        sync_started_at TIMESTAMP,
        sync_completed_at TIMESTAMP
    )
    USING DELTA
""")

def get_last_sync(entity: str) -> str:
    """Get the last sync timestamp for an entity."""
    result = spark.sql(f"""
        SELECT last_modified_timestamp 
        FROM cdc_metadata 
        WHERE entity_name = '{entity}' AND sync_status = 'SUCCESS'
        ORDER BY sync_completed_at DESC 
        LIMIT 1
    """).collect()
    
    if result and result[0][0]:
        return result[0][0]
    
    # Default: 24 hours ago (first run will get recent data)
    default_time = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"   No previous sync found for {entity}, using default: {default_time}")
    return default_time


def update_sync_metadata(entity: str, records: int, max_modified: str, status: str, started_at: datetime):
    """Update CDC metadata after sync."""
    completed_at = datetime.utcnow()
    
    # Insert new metadata record (append-only for audit trail)
    spark.sql(f"""
        INSERT INTO cdc_metadata VALUES (
            '{entity}',
            CURRENT_TIMESTAMP(),
            '{max_modified}',
            {records},
            '{status}',
            TIMESTAMP('{started_at.strftime('%Y-%m-%d %H:%M:%S')}'),
            TIMESTAMP('{completed_at.strftime('%Y-%m-%d %H:%M:%S')}')
        )
    """)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def fetch_modified_records(endpoint: str, since_timestamp: str, page_size: int = 100) -> list:
    """Fetch records modified since a given timestamp."""
    all_records = []
    page = 1
    has_more = True
    
    # URL encode the search parameter properly
    search_param = f"modified>='{since_timestamp}'"
    
    while has_more:
        url = f"{api_base_url}{endpoint}"
        params = {
            "search": search_param,
            "limit": page_size,
            "page": page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("data", [])
            all_records.extend(records)
            
            pagination = data.get("pagination", {})
            has_more = bool(pagination.get("has_next_page", False))
            page += 1
            
            if page % 5 == 0:
                print(f"   Fetched {len(all_records)} records so far...")
                
        except Exception as e:
            print(f"   Error fetching {endpoint} page {page}: {e}")
            has_more = False
    
    return all_records


def fetch_media_for_properties(property_ids: list, categories: list = ["photos", "documents", "floorplans"]) -> list:
    """Fetch media for specific properties."""
    all_media = []
    
    for i, prop_id in enumerate(property_ids):
        for category in categories:
            try:
                url = f"{api_base_url}/media/by-category/{category}/Properties/{prop_id}"
                response = requests.get(url, headers=headers, timeout=timeout_seconds)
                
                if response.status_code == 200:
                    media_data = response.json().get("data", [])
                    for m in media_data:
                        m["property_id"] = prop_id
                        m["media_category"] = category
                    all_media.extend(media_data)
                    
            except Exception as e:
                pass  # Skip errors silently for media
        
        if (i + 1) % 10 == 0:
            print(f"   Processed {i + 1}/{len(property_ids)} properties, {len(all_media)} media items")
    
    return all_media


def records_to_dataframe(records: list) -> "DataFrame":
    """Convert records to Spark DataFrame with string columns."""
    if not records:
        return None
    
    # Use Pandas to normalize nested structures
    pdf = pd.json_normalize(records, sep="_")
    
    # Convert ALL columns to strings (bronze layer = raw data as strings)
    for col in pdf.columns:
        pdf[col] = pdf[col].apply(lambda x: _json.dumps(x) if isinstance(x, (list, dict)) else (str(x) if x is not None else ""))
    
    return spark.createDataFrame(pdf)


def merge_to_bronze(records: list, table_name: str, key_column: str = "id") -> int:
    """MERGE records into a bronze table (upsert).
    
    Note: Due to schema evolution (API may return different nested fields),
    we use a simple DELETE + INSERT approach instead of MERGE.
    This ensures we always have the latest data without schema conflicts.
    """
    if not records:
        print(f"   ⚠️  No records to merge into {table_name}")
        return 0
    
    df = records_to_dataframe(records)
    if df is None:
        return 0
    
    # Add CDC metadata
    df = df.withColumn("_cdc_updated_at", current_timestamp())
    
    # Create temp view
    temp_view = f"_cdc_temp_{table_name}"
    df.createOrReplaceTempView(temp_view)
    
    # Check if table exists
    tables = [t.name for t in spark.catalog.listTables()]
    
    if table_name not in tables:
        # First run - create table
        print(f"   Creating new table: {table_name}")
        df.write.format("delta").mode("overwrite").saveAsTable(table_name)
    else:
        # DELETE + INSERT approach (avoids schema mismatch issues)
        # Get the IDs of records we're updating
        record_ids = [str(r.get(key_column, "")) for r in records if r.get(key_column)]
        
        if record_ids:
            # Delete existing records with these IDs
            ids_str = "', '".join(record_ids)
            delete_sql = f"DELETE FROM {table_name} WHERE {key_column} IN ('{ids_str}')"
            spark.sql(delete_sql)
            print(f"   Deleted {len(record_ids)} existing records")
        
        # Insert new records - need to match target schema
        # Get target columns and only insert matching columns
        target_cols = set([c.lower() for c in spark.table(table_name).columns])
        source_cols = set([c.lower() for c in df.columns])
        common_cols = target_cols.intersection(source_cols)
        
        # Select only common columns from source
        select_cols = [c for c in df.columns if c.lower() in common_cols]
        df_filtered = df.select(select_cols)
        
        # Append new records
        df_filtered.write.format("delta").mode("append").saveAsTable(table_name)
    
    print(f"   ✅ {table_name}: Merged {len(records)} records")
    return len(records)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Properties

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: PROPERTIES")
print("=" * 80)

started_at = datetime.utcnow()

# Get last sync timestamp
last_sync = get_last_sync("properties")
print(f"\n🕐 Last sync: {last_sync}")

# Fetch modified properties
print(f"\n1️⃣  Fetching properties modified since {last_sync}...")
modified_properties = fetch_modified_records("/properties", last_sync)
print(f"   Found: {len(modified_properties)} modified properties")

if modified_properties:
    # Get max modified timestamp for next sync
    max_modified = max(p.get("modified", "") for p in modified_properties)
    print(f"   Max modified timestamp: {max_modified}")
    
    # Merge into bronze
    print("\n2️⃣  Merging into bronze.properties...")
    merged_count = merge_to_bronze(modified_properties, "properties", "id")
    cdc_changes["properties"] = merged_count
    
    # Fetch and merge media for modified properties
    print("\n3️⃣  Fetching media for modified properties...")
    property_ids = [p.get("id") for p in modified_properties if p.get("id")]
    modified_media = fetch_media_for_properties(property_ids)
    
    if modified_media:
        print(f"   Found: {len(modified_media)} media items")
        cdc_changes["media"] = len(modified_media)
        # For media, we need to handle differently - delete old media for these properties first
        for prop_id in property_ids:
            spark.sql(f"DELETE FROM property_media WHERE property_id = '{prop_id}'")
        merge_to_bronze(modified_media, "property_media", "id")
    
    # Update metadata
    update_sync_metadata("properties", merged_count, max_modified, "SUCCESS", started_at)
    print(f"\n✅ Properties CDC complete: {merged_count} records updated")
else:
    print("\n✅ No property changes since last sync")
    update_sync_metadata("properties", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Agents

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: AGENTS")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("agents")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching agents modified since {last_sync}...")
modified_agents = fetch_modified_records("/agents", last_sync)
print(f"   Found: {len(modified_agents)} modified agents")

if modified_agents:
    max_modified = max(a.get("modified", "") for a in modified_agents)
    merged_count = merge_to_bronze(modified_agents, "agents", "id")
    cdc_changes["agents"] = merged_count
    update_sync_metadata("agents", merged_count, max_modified, "SUCCESS", started_at)
    print(f"\n✅ Agents CDC complete: {merged_count} records updated")
else:
    print("\n✅ No agent changes since last sync")
    update_sync_metadata("agents", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Contacts

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: CONTACTS")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("contacts")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching contacts modified since {last_sync}...")
modified_contacts = fetch_modified_records("/contacts", last_sync)
print(f"   Found: {len(modified_contacts)} modified contacts")

if modified_contacts:
    max_modified = max(c.get("modified", "") for c in modified_contacts)
    merged_count = merge_to_bronze(modified_contacts, "contacts", "id")
    cdc_changes["contacts"] = merged_count
    update_sync_metadata("contacts", merged_count, max_modified, "SUCCESS", started_at)
    print(f"\n✅ Contacts CDC complete: {merged_count} records updated")
else:
    print("\n✅ No contact changes since last sync")
    update_sync_metadata("contacts", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Property Viewings

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: PROPERTY VIEWINGS")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("property_viewings")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching viewings modified since {last_sync}...")
modified_viewings = fetch_modified_records("/property-viewings", last_sync)
print(f"   Found: {len(modified_viewings)} modified viewings")

if modified_viewings:
    max_modified = max(v.get("modified", "") for v in modified_viewings)
    merged_count = merge_to_bronze(modified_viewings, "property_viewings", "id")
    cdc_changes["viewings"] = merged_count
    update_sync_metadata("property_viewings", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("property_viewings", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Opportunities

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: OPPORTUNITIES")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("opportunities")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching opportunities modified since {last_sync}...")
modified_opportunities = fetch_modified_records("/opportunities", last_sync)
print(f"   Found: {len(modified_opportunities)} modified opportunities")

if modified_opportunities:
    max_modified = max(o.get("modified", "") for o in modified_opportunities)
    merged_count = merge_to_bronze(modified_opportunities, "opportunities", "id")
    cdc_changes["opportunities"] = merged_count
    update_sync_metadata("opportunities", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("opportunities", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Users

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: USERS")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("users")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching users modified since {last_sync}...")
modified_users = fetch_modified_records("/users", last_sync)
print(f"   Found: {len(modified_users)} modified users")

if modified_users:
    max_modified = max(u.get("modified", "") for u in modified_users)
    merged_count = merge_to_bronze(modified_users, "users", "id")
    cdc_changes["users"] = merged_count
    update_sync_metadata("users", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("users", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Projects

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: PROJECTS")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("projects")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching projects modified since {last_sync}...")
modified_projects = fetch_modified_records("/projects", last_sync)
print(f"   Found: {len(modified_projects)} modified projects")

if modified_projects:
    max_modified = max(p.get("modified", "") for p in modified_projects)
    merged_count = merge_to_bronze(modified_projects, "projects", "id")
    cdc_changes["projects"] = merged_count
    update_sync_metadata("projects", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("projects", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Project Features

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: PROJECT FEATURES")
print("=" * 80)

started_at = datetime.utcnow()
last_sync = get_last_sync("project_features")
print(f"\n🕐 Last sync: {last_sync}")

print(f"\n1️⃣  Fetching project features modified since {last_sync}...")
modified_features = fetch_modified_records("/project-features", last_sync)
print(f"   Found: {len(modified_features)} modified project features")

if modified_features:
    max_modified = max(f.get("modified", "") for f in modified_features)
    merged_count = merge_to_bronze(modified_features, "project_features", "id")
    cdc_changes["project_features"] = merged_count
    update_sync_metadata("project_features", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("project_features", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC: Lookups (Property Types, Subtypes, Locations, Media Categories)

# COMMAND ----------

print("\n" + "=" * 80)
print("📥 CDC: LOOKUPS")
print("=" * 80)

# Property Types
started_at = datetime.utcnow()
last_sync = get_last_sync("property_types")
print(f"\n1️⃣  Property Types (last sync: {last_sync})...")
modified_types = fetch_modified_records("/property-types", last_sync)
print(f"   Found: {len(modified_types)} modified")
if modified_types:
    max_modified = max(t.get("modified", "") for t in modified_types)
    merged_count = merge_to_bronze(modified_types, "property_types", "id")
    cdc_changes["property_types"] = merged_count
    update_sync_metadata("property_types", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("property_types", 0, last_sync, "SUCCESS", started_at)

# Property Subtypes
started_at = datetime.utcnow()
last_sync = get_last_sync("property_subtypes")
print(f"\n2️⃣  Property Subtypes (last sync: {last_sync})...")
modified_subtypes = fetch_modified_records("/property-subtypes", last_sync)
print(f"   Found: {len(modified_subtypes)} modified")
if modified_subtypes:
    max_modified = max(s.get("modified", "") for s in modified_subtypes)
    merged_count = merge_to_bronze(modified_subtypes, "property_subtypes", "id")
    cdc_changes["property_subtypes"] = merged_count
    update_sync_metadata("property_subtypes", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("property_subtypes", 0, last_sync, "SUCCESS", started_at)

# Locations
started_at = datetime.utcnow()
last_sync = get_last_sync("locations")
print(f"\n3️⃣  Locations (last sync: {last_sync})...")
modified_locations = fetch_modified_records("/locations", last_sync)
print(f"   Found: {len(modified_locations)} modified")
if modified_locations:
    max_modified = max(l.get("modified", "") for l in modified_locations)
    merged_count = merge_to_bronze(modified_locations, "locations", "id")
    cdc_changes["locations"] = merged_count
    update_sync_metadata("locations", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("locations", 0, last_sync, "SUCCESS", started_at)

# Media Categories
started_at = datetime.utcnow()
last_sync = get_last_sync("media_categories")
print(f"\n4️⃣  Media Categories (last sync: {last_sync})...")
modified_cats = fetch_modified_records("/media/categories", last_sync)
print(f"   Found: {len(modified_cats)} modified")
if modified_cats:
    max_modified = max(c.get("modified", "") for c in modified_cats)
    merged_count = merge_to_bronze(modified_cats, "media_categories", "id")
    cdc_changes["media_categories"] = merged_count
    update_sync_metadata("media_categories", merged_count, max_modified, "SUCCESS", started_at)
else:
    update_sync_metadata("media_categories", 0, last_sync, "SUCCESS", started_at)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Portal Locations (Skipped in CDC)
# MAGIC 
# MAGIC Portal location mappings (bayut, bazaraki, spitogatos, property_finder_ae) are static lookup tables
# MAGIC that don't support the `modified` timestamp filter. They're only refreshed during full pipeline runs.

# COMMAND ----------

print("\n" + "=" * 80)
print("ℹ️  PORTAL LOCATIONS (Skipped)")
print("=" * 80)
print("\n   Portal location mappings are static lookup tables.")
print("   They don't support incremental sync and are only refreshed during full pipeline runs.")
print("   Tables: bayut_locations, bazaraki_locations, spitogatos_locations, property_finder_ae_locations")
cdc_changes["portal_locations"] = 0

# COMMAND ----------

# MAGIC %md
# MAGIC ## Soft Delete Detection

# COMMAND ----------

print("\n" + "=" * 80)
print("🗑️  SOFT DELETE DETECTION")
print("=" * 80)

# Check for trashed properties (info only - trashed properties are filtered in Silver/Gold layers)
print("\n1️⃣  Checking for trashed properties...")
try:
    trashed_url = f"{api_base_url}/properties"
    params = {"trashed": "true", "limit": 100}
    response = requests.get(trashed_url, headers=headers, params=params, timeout=timeout_seconds)
    
    if response.status_code == 200:
        trashed_data = response.json().get("data", [])
        trashed_count = len(trashed_data)
        
        if trashed_count > 0:
            print(f"   ℹ️  Found {trashed_count} trashed properties in Qobrix")
            print(f"   ℹ️  These are excluded in Silver/Gold layers via status filter")
        else:
            print("   ✅ No trashed properties found")
    else:
        print(f"   ⚠️  Could not check trashed properties: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Error checking trashed properties: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## CDC Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 CDC SYNC SUMMARY")
print("=" * 80)

# Show recent sync history
print("\nRecent sync history:")
spark.sql("""
    SELECT 
        entity_name,
        records_processed,
        sync_status,
        sync_completed_at
    FROM cdc_metadata
    WHERE sync_completed_at >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
    ORDER BY sync_completed_at DESC
""").show(truncate=False)

# Show current table counts with CDC changes as Spark DataFrame
print("\nCurrent bronze table counts:")

# Map table names to cdc_changes keys
table_to_cdc = {
    "properties": "properties",
    "agents": "agents", 
    "contacts": "contacts",
    "property_viewings": "viewings",
    "property_media": "media",
    "opportunities": "opportunities",
    "users": "users",
    "projects": "projects",
    "project_features": "project_features",
    "property_types": "property_types",
    "property_subtypes": "property_subtypes",
    "locations": "locations",
    "media_categories": "media_categories",
    "bayut_locations": "portal_locations",
    "bazaraki_locations": "portal_locations",
    "spitogatos_locations": "portal_locations",
    "property_finder_ae_locations": "portal_locations"
}

tables = [
    "properties", "agents", "contacts", "property_viewings", "property_media",
    "opportunities", "users", "projects", "project_features",
    "property_types", "property_subtypes", "locations", "media_categories",
    "bayut_locations", "bazaraki_locations", "spitogatos_locations", "property_finder_ae_locations"
]

# Build data for DataFrame
table_data = []
for table in tables:
    try:
        count = spark.sql(f"SELECT COUNT(*) FROM {table}").collect()[0][0]
        cdc_key = table_to_cdc.get(table, table)
        changed = cdc_changes.get(cdc_key, 0)
        # For portal locations (skipped in CDC), show as skipped
        if table in ["bazaraki_locations", "spitogatos_locations", "property_finder_ae_locations"]:
            changed = None  # Will show as null/skipped
        table_data.append((table, count, changed))
    except:
        table_data.append((table, 0, None))

# Create and display DataFrame
from pyspark.sql.types import StructType, StructField, StringType, LongType, IntegerType
schema = StructType([
    StructField("table_name", StringType(), False),
    StructField("total_rows", LongType(), False),
    StructField("cdc_changed", IntegerType(), True)
])
df = spark.createDataFrame(table_data, schema)
df.show(20, truncate=False)

print("\n" + "=" * 80)
print("✅ CDC SYNC COMPLETE")
print("=" * 80)

