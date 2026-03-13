#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Qobrix Full Refresh -> Bronze (DBML-aligned, non-flattened)
#
# Purpose:
# - Fetch raw data from Qobrix API
# - Store it in bronze Delta tables named exactly as in DBML:
#   qobrix_api_properties, qobrix_api_agents, qobrix_api_projects, ...
# - Do NOT pandas-flatten the JSON; keep structures reasonable so we avoid
#   hundreds of useless columns.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

import os
import requests
from typing import List, Dict, Optional

from pyspark.sql import DataFrame, functions as F

catalog = "mls2"
schema = "qobrix_bronze"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

timeout_seconds = 30

# Widgets / env vars for Qobrix API
dbutils.widgets.text("QOBRIX_API_USER", "")
dbutils.widgets.text("QOBRIX_API_KEY", "")
dbutils.widgets.text("QOBRIX_API_BASE_URL", "")

qobrix_api_user = os.getenv("QOBRIX_API_USER") or dbutils.widgets.get("QOBRIX_API_USER")
qobrix_api_key = os.getenv("QOBRIX_API_KEY") or dbutils.widgets.get("QOBRIX_API_KEY")
api_base_url = os.getenv("QOBRIX_API_BASE_URL") or dbutils.widgets.get("QOBRIX_API_BASE_URL")

if not qobrix_api_user or not qobrix_api_key or not api_base_url:
    raise ValueError("Set QOBRIX_API_USER, QOBRIX_API_KEY, and QOBRIX_API_BASE_URL (env vars or widgets).")

headers = {
    "X-Api-User": qobrix_api_user,
    "X-Api-Key": qobrix_api_key,
}

# Optional test mode
test_mode = True
max_properties = 50 if test_mode else None
max_contacts = 200 if test_mode else None
max_projects = 100 if test_mode else None
max_viewings = 100 if test_mode else None
max_opportunities = 200 if test_mode else None

if test_mode:
    print("🧪 TEST MODE ENABLED")
    print(f"Max properties:   {max_properties}")
    print(f"Max contacts:     {max_contacts}")
    print(f"Max projects:     {max_projects}")
    print(f"Max viewings:     {max_viewings}")
    print(f"Max opportunities:{max_opportunities}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helpers (API & Bronze writers)

# COMMAND ----------


def fetch_paginated(endpoint: str, max_records: Optional[int] = None, page_size: int = 100) -> List[Dict]:
    """Fetch all records from a paginated Qobrix endpoint (similar to 00_full_refresh_qobrix_bronze)."""
    all_records: List[Dict] = []
    page = 1
    has_more = True

    while has_more:
        if max_records is not None and len(all_records) >= max_records:
            break

        limit = page_size
        if max_records is not None:
            remaining = max_records - len(all_records)
            if remaining <= 0:
                break
            limit = min(page_size, remaining)

        url = f"{api_base_url}{endpoint}"
        params = {"limit": limit, "page": page}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("data", []) or []

            all_records.extend(records)

            pagination = data.get("pagination", {}) or {}
            has_more = bool(pagination.get("has_next_page", False))
            page += 1

        except Exception as e:
            print(f"   Error fetching {endpoint} page {page}: {e}")
            has_more = False

    return all_records


def records_to_df(records: List[Dict]) -> Optional[DataFrame]:
    """Convert list[dict] -> Spark DataFrame without pandas.json_normalize."""
    if not records:
        return None
    return spark.createDataFrame(records)


def overwrite_table(df: DataFrame, full_table_name: str):
    """CREATE OR REPLACE a Delta table from the DataFrame."""
    if df is None or df.rdd.isEmpty():
        print(f"   ⚠️ No data for {full_table_name}, skipping.")
        return

    df.write.format("delta").mode("overwrite").saveAsTable(full_table_name)
    row_count = df.count()
    col_count = len(df.columns)
    print(f"   ✅ {full_table_name}: {row_count} rows, {col_count} columns")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch core Qobrix entities

# COMMAND ----------

print("=" * 80)
print("📥 FETCHING QOBRIX DATA FOR BRONZE (DBML qobrix_api_*)")
print("=" * 80)

print("\n1️⃣  Properties (/properties)...")
raw_properties = fetch_paginated("/properties", max_records=max_properties)
print(f"   Fetched: {len(raw_properties)}")

print("\n2️⃣  Agents (/agents)...")
raw_agents = fetch_paginated("/agents")
print(f"   Fetched: {len(raw_agents)}")

print("\n3️⃣  Projects (/projects)...")
raw_projects = fetch_paginated("/projects", max_records=max_projects)
print(f"   Fetched: {len(raw_projects)}")

print("\n4️⃣  Project Features (/project-features)...")
raw_project_features = fetch_paginated("/project-features")
print(f"   Fetched: {len(raw_project_features)}")

print("\n5️⃣  Property Types (/property-types)...")
raw_property_types = fetch_paginated("/property-types")
print(f"   Fetched: {len(raw_property_types)}")

print("\n6️⃣  Property Subtypes (/property-subtypes)...")
raw_property_subtypes = fetch_paginated("/property-subtypes")
print(f"   Fetched: {len(raw_property_subtypes)}")

print("\n7️⃣  Contacts (/contacts)...")
raw_contacts = fetch_paginated("/contacts", max_records=max_contacts)
print(f"   Fetched: {len(raw_contacts)}")

print("\n8️⃣  Users (/users)...")
raw_users = fetch_paginated("/users")
print(f"   Fetched: {len(raw_users)}")

print("\n9️⃣  Property Viewings (/property-viewings)...")
raw_property_viewings = fetch_paginated("/property-viewings", max_records=max_viewings)
print(f"   Fetched: {len(raw_property_viewings)}")

print("\n🔟 Opportunities (/opportunities)...")
raw_opportunities = fetch_paginated("/opportunities", max_records=max_opportunities)
print(f"   Fetched: {len(raw_opportunities)}")

print("\n1️⃣1️⃣ Media Categories (/media/categories)...")
raw_media_categories = fetch_paginated("/media/categories")
print(f"   Fetched: {len(raw_media_categories)}")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch property + project media (for media/media_files tables)

# COMMAND ----------


def fetch_media_for_entity(entity: str, ids: List[str], categories=("photos", "documents", "floorplans")) -> List[Dict]:
    """
    Fetch media for given Qobrix entity type ('Properties' or 'Projects').
    Returns list of media JSON records from API (with file structs).
    """
    all_media: List[Dict] = []
    base_url = api_base_url.replace("/api/v2", "")  # for building absolute href

    for i, entity_id in enumerate(ids):
        for category in categories:
            try:
                url = f"{api_base_url}/media/by-category/{category}/{entity}/{entity_id}"
                resp = requests.get(url, headers=headers, timeout=timeout_seconds)
                if resp.status_code == 200:
                    media_data = resp.json().get("data", []) or []
                    for m in media_data:
                        m["related_model"] = entity
                        m["related_id"] = entity_id
                        m["media_category"] = category
                        # Make file.href absolute
                        if m.get("file", {}).get("href"):
                            href = m["file"]["href"]
                            if href.startswith("/"):
                                m["file"]["href"] = f"{base_url}{href}"
                    all_media.extend(media_data)
            except Exception as e:
                print(f"   Error fetching media for {entity} {entity_id}: {e}")

        if (i + 1) % 25 == 0:
            print(f"   Media progress {entity}: {i + 1}/{len(ids)}, total media {len(all_media)}")

    return all_media


print("\n1️⃣2️⃣ Property + Project Media ...")

property_ids = [p.get("id") for p in raw_properties if p.get("id")]
project_ids = [p.get("id") for p in raw_projects if p.get("id")]

property_media = fetch_media_for_entity("Properties", property_ids)
project_media = fetch_media_for_entity("Projects", project_ids)

all_media_raw = property_media + project_media
print(f"   Total media items: {len(all_media_raw)}")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Write DBML bronze tables: qobrix_api_*

# COMMAND ----------

print("\n" + "=" * 80)
print("💾 WRITING BRONZE TABLES (DBML qobrix_api_*)")
print("=" * 80)

# 1. Simple 1:1 tables: properties, agents, projects, etc.
overwrite_table(records_to_df(raw_properties), "qobrix_api_properties")
overwrite_table(records_to_df(raw_agents), "qobrix_api_agents")
overwrite_table(records_to_df(raw_projects), "qobrix_api_projects")
overwrite_table(records_to_df(raw_project_features), "qobrix_api_project_features")
overwrite_table(records_to_df(raw_property_types), "qobrix_api_property_types")
overwrite_table(records_to_df(raw_property_subtypes), "qobrix_api_property_subtypes")
overwrite_table(records_to_df(raw_contacts), "qobrix_api_contacts")
overwrite_table(records_to_df(raw_users), "qobrix_api_users")
overwrite_table(records_to_df(raw_property_viewings), "qobrix_api_property_viewings")
overwrite_table(records_to_df(raw_opportunities), "qobrix_api_opportunities")
overwrite_table(records_to_df(raw_media_categories), "qobrix_api_media_categories")

# 2. Media: split into qobrix_api_media_files + qobrix_api_media
media_df = records_to_df(all_media_raw)

if media_df is not None and not media_df.rdd.isEmpty():
    files_df = (
        media_df
        .select("file.*")
        .dropDuplicates(["id"])
    )
    overwrite_table(files_df, "qobrix_api_media_files")

    media_links_df = (
        media_df
        .select(
            F.col("id").alias("id"),
            F.col("category_id"),
            F.col("related_model"),
            F.col("related_id"),
            F.col("media_type"),
            F.col("reference_id"),
            F.col("display_order"),
            F.col("file.id").alias("file_id"),
            F.col("created"),
            F.col("modified"),
        )
    )
    overwrite_table(media_links_df, "qobrix_api_media")
else:
    print("   ⚠️ No media returned, skipping media tables.")

print("\n" + "=" * 80)
print("✅ QOBRIX BRONZE (DBML qobrix_api_*) COMPLETE")
print("=" * 80)

