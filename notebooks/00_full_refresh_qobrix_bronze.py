# Databricks notebook source
# MAGIC %md
# MAGIC # MLS 2.0 – Qobrix Full Refresh → Bronze Layer
# MAGIC 
# MAGIC **Purpose:** Fetches ALL property-related data from Qobrix API into bronze Delta tables.
# MAGIC 
# MAGIC **Tables Created:**
# MAGIC | Table | Description |
# MAGIC |-------|-------------|
# MAGIC | `properties` | Main property listings (241 fields) |
# MAGIC | `agents` | Real estate agents |
# MAGIC | `property_types` | Property type lookups |
# MAGIC | `property_subtypes` | Property subtype lookups |
# MAGIC | `projects` | Development projects |
# MAGIC | `project_features` | Project feature lookups |
# MAGIC | `contacts` | Sellers/buyers |
# MAGIC | `users` | System users |
# MAGIC | `locations` | Location/area lookups |
# MAGIC | `media_categories` | Media type definitions |
# MAGIC | `property_viewings` | Viewing appointments |
# MAGIC | `opportunities` | Leads/inquiries for properties |
# MAGIC | `bayut_locations` | Bayut portal location mappings |
# MAGIC | `bazaraki_locations` | Bazaraki portal location mappings |
# MAGIC | `spitogatos_locations` | Spitogatos portal location mappings |
# MAGIC | `property_finder_ae_locations` | Property Finder AE location mappings |
# MAGIC | `property_media` | Photos, documents, floorplans |
# MAGIC 
# MAGIC **Test Mode:** Set `test_mode = True` to limit records (default: 10 properties)
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

# Test mode settings
test_mode = True
max_properties = 10 if test_mode else None
max_contacts = 500 if test_mode else None
max_projects = 100 if test_mode else None
max_viewings = 100 if test_mode else None

if test_mode:
    print("=" * 80)
    print("🧪 TEST MODE ENABLED")
    print("=" * 80)
    print(f"Max Properties: {max_properties}")
    print(f"Max Contacts: {max_contacts}")
    print(f"Max Projects: {max_projects}")
    print(f"Max Viewings: {max_viewings}")
    print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def fetch_paginated(endpoint: str, max_records: int = None, page_size: int = 100) -> list:
    """Fetch all records from a paginated endpoint."""
    all_records = []
    page = 1
    has_more = True
    
    while has_more:
        limit = page_size
        if max_records:
            remaining = max_records - len(all_records)
            if remaining <= 0:
                break
            limit = min(page_size, remaining)
        
        url = f"{api_base_url}{endpoint}"
        params = {"limit": limit, "page": page}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("data", [])
            if max_records and len(all_records) + len(records) > max_records:
                records = records[:max_records - len(all_records)]
                has_more = False
            
            all_records.extend(records)
            
            if max_records and len(all_records) >= max_records:
                has_more = False
            
            pagination = data.get("pagination", {})
            has_more = has_more and bool(pagination.get("has_next_page", False))
            page += 1
            
        except Exception as e:
            print(f"   Error fetching {endpoint} page {page}: {e}")
            has_more = False
    
    return all_records


def fetch_media_for_properties(properties: list, categories: list = ["photos", "documents", "floorplans"]) -> list:
    """Fetch media for properties using correct endpoint: /media/by-category/{category}/Properties/{id}"""
    all_media = []
    
    for i, prop in enumerate(properties):
        prop_id = prop.get("id")
        if not prop_id:
            continue
        
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
            print(f"   Processed {i + 1}/{len(properties)} properties, {len(all_media)} media items")
    
    return all_media


def save_to_bronze(records: list, table_name: str, description: str):
    """Save records to a bronze Delta table."""
    if not records:
        print(f"   ⚠️  No {description} to save")
        return 0
    
    # Use Pandas to normalize nested structures
    pdf = pd.json_normalize(records, sep="_")
    
    # Convert ALL columns to strings to avoid schema conflicts on overwrite
    # This is the bronze layer - we preserve raw data as strings
    # IMPORTANT: Use empty string "" instead of None to avoid VOID type columns
    for col in pdf.columns:
        pdf[col] = pdf[col].apply(lambda x: _json.dumps(x) if isinstance(x, (list, dict)) else (str(x) if x is not None else ""))
    
    df = spark.createDataFrame(pdf)
    
    # Drop existing table to avoid schema merge conflicts
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")
    
    (
        df.write.format("delta")
        .mode("overwrite")
        .saveAsTable(table_name)
    )
    
    print(f"   ✅ {table_name}: {len(records)} records, {len(df.columns)} columns")
    return len(records)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch All Data

# COMMAND ----------

print("=" * 80)
print("📥 FETCHING ALL QOBRIX PROPERTY-RELATED DATA")
print("=" * 80)

# 1. Properties (main entity - 241 fields)
print("\n1️⃣  Properties...")
properties = fetch_paginated("/properties", max_records=max_properties, page_size=100)
print(f"   Fetched: {len(properties)}")

# 2. Agents
print("\n2️⃣  Agents...")
agents = fetch_paginated("/agents", max_records=None, page_size=100)
print(f"   Fetched: {len(agents)}")

# 3. Property Types
print("\n3️⃣  Property Types...")
property_types = fetch_paginated("/property-types", max_records=None, page_size=100)
print(f"   Fetched: {len(property_types)}")

# 4. Property Subtypes
print("\n4️⃣  Property Subtypes...")
property_subtypes = fetch_paginated("/property-subtypes", max_records=None, page_size=100)
print(f"   Fetched: {len(property_subtypes)}")

# 5. Projects
print("\n5️⃣  Projects...")
projects = fetch_paginated("/projects", max_records=max_projects, page_size=100)
print(f"   Fetched: {len(projects)}")

# 6. Project Features
print("\n6️⃣  Project Features...")
project_features = fetch_paginated("/project-features", max_records=None, page_size=100)
print(f"   Fetched: {len(project_features)}")

# 7. Contacts (Sellers/Buyers)
print("\n7️⃣  Contacts...")
contacts = fetch_paginated("/contacts", max_records=max_contacts, page_size=100)
print(f"   Fetched: {len(contacts)}")

# 8. Users
print("\n8️⃣  Users...")
users = fetch_paginated("/users", max_records=None, page_size=100)
print(f"   Fetched: {len(users)}")

# 9. Locations
print("\n9️⃣  Locations...")
locations = fetch_paginated("/locations", max_records=None, page_size=100)
print(f"   Fetched: {len(locations)}")

# 10. Media Categories
print("\n🔟 Media Categories...")
media_categories = fetch_paginated("/media/categories", max_records=None, page_size=100)
print(f"   Fetched: {len(media_categories)}")

# 11. Property Viewings
print("\n1️⃣1️⃣ Property Viewings...")
property_viewings = fetch_paginated("/property-viewings", max_records=max_viewings, page_size=100)
print(f"   Fetched: {len(property_viewings)}")

# 12. Opportunities (leads/inquiries related to properties)
print("\n1️⃣2️⃣ Opportunities...")
max_opportunities = 100 if test_mode else None
opportunities = fetch_paginated("/opportunities", max_records=max_opportunities, page_size=100)
print(f"   Fetched: {len(opportunities)}")

# 13. Portal Location Mappings (for property syndication)
print("\n1️⃣3️⃣ Portal Location Mappings...")
bayut_locations = fetch_paginated("/bayut-locations", max_records=None, page_size=100)
print(f"   Bayut locations: {len(bayut_locations)}")
bazaraki_locations = fetch_paginated("/bazaraki-locations", max_records=None, page_size=100)
print(f"   Bazaraki locations: {len(bazaraki_locations)}")
spitogatos_locations = fetch_paginated("/spitogatos-locations", max_records=None, page_size=100)
print(f"   Spitogatos locations: {len(spitogatos_locations)}")
property_finder_ae_locations = fetch_paginated("/property-finder-a-e-locations", max_records=None, page_size=100)
print(f"   Property Finder AE locations: {len(property_finder_ae_locations)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Property Media

# COMMAND ----------

print("\n1️⃣3️⃣ Property Media (photos, documents, floorplans)...")
property_media = fetch_media_for_properties(properties, categories=["photos", "documents", "floorplans"])
print(f"   Total media items: {len(property_media)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save All to Bronze Tables

# COMMAND ----------

print("\n" + "=" * 80)
print("💾 SAVING TO BRONZE TABLES")
print("=" * 80)

total_records = 0

# Save all entities
total_records += save_to_bronze(properties, "properties", "properties")
total_records += save_to_bronze(agents, "agents", "agents")
total_records += save_to_bronze(property_types, "property_types", "property types")
total_records += save_to_bronze(property_subtypes, "property_subtypes", "property subtypes")
total_records += save_to_bronze(projects, "projects", "projects")
total_records += save_to_bronze(project_features, "project_features", "project features")
total_records += save_to_bronze(contacts, "contacts", "contacts")
total_records += save_to_bronze(users, "users", "users")
total_records += save_to_bronze(locations, "locations", "locations")
total_records += save_to_bronze(media_categories, "media_categories", "media categories")
total_records += save_to_bronze(property_viewings, "property_viewings", "property viewings")
total_records += save_to_bronze(opportunities, "opportunities", "opportunities")
total_records += save_to_bronze(bayut_locations, "bayut_locations", "Bayut locations")
total_records += save_to_bronze(bazaraki_locations, "bazaraki_locations", "Bazaraki locations")
total_records += save_to_bronze(spitogatos_locations, "spitogatos_locations", "Spitogatos locations")
total_records += save_to_bronze(property_finder_ae_locations, "property_finder_ae_locations", "Property Finder AE locations")
total_records += save_to_bronze(property_media, "property_media", "property media")

print("\n" + "=" * 80)
print(f"✅ BRONZE LAYER COMPLETE: {total_records} total records")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n📊 Bronze Tables Summary:")
print("-" * 50)

tables = [
    "properties", "agents", "property_types", "property_subtypes",
    "projects", "project_features", "contacts", "users",
    "locations", "media_categories", "property_viewings", "opportunities",
    "bayut_locations", "bazaraki_locations", "spitogatos_locations", 
    "property_finder_ae_locations", "property_media"
]

for table in tables:
    try:
        count = spark.sql(f"SELECT COUNT(*) FROM {table}").collect()[0][0]
        cols = len(spark.table(table).columns)
        print(f"   {table:25s} {count:>8} rows, {cols:>4} cols")
    except Exception as e:
        print(f"   {table:25s} (not created)")

print("-" * 50)
