#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Qobrix CDC -> Bronze (App Model, Incremental)
#
# Purpose: Fetch only NEW and CHANGED records from Qobrix API since last sync; MERGE into
# sharp.mls2.qobrix_api_* tables. Use after 00b full refresh for ongoing incremental syncs.
#
# How it works:
# 1. Reads last_sync from sharp.mls2.cdc_metadata (per entity).
# 2. Calls API with search: modified>=last_sync and created>=last_sync; dedupes by id.
# 3. Normalizes records like 00b (dict/list -> JSON string, None -> "") and adds _cdc_updated_at.
# 4. DELETE from bronze where id IN (changed ids); APPEND new rows (schema evolution adds _cdc_updated_at).
#
# When to use:
# - After initial load: run 00b once, then run this (00c) on a schedule (e.g. every 15–30 min).
# - After each 00c: run silver (02e, 02f, …) and gold (03e, 03f, …) to refresh downstream.

# COMMAND ----------

import os
import json as _json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

catalog = "sharp"
schema = "mls2"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

timeout_seconds = 30
dbutils.widgets.text("QOBRIX_API_USER", "")
dbutils.widgets.text("QOBRIX_API_KEY", "")
dbutils.widgets.text("QOBRIX_API_BASE_URL", "")

qobrix_api_user = os.getenv("QOBRIX_API_USER") or dbutils.widgets.get("QOBRIX_API_USER")
qobrix_api_key = os.getenv("QOBRIX_API_KEY") or dbutils.widgets.get("QOBRIX_API_KEY")
api_base_url = (os.getenv("QOBRIX_API_BASE_URL") or dbutils.widgets.get("QOBRIX_API_BASE_URL") or "").rstrip("/")

if not qobrix_api_user or not qobrix_api_key or not api_base_url:
    raise ValueError("Set QOBRIX_API_USER, QOBRIX_API_KEY, QOBRIX_API_BASE_URL.")

headers = {"X-Api-User": qobrix_api_user, "X-Api-Key": qobrix_api_key}

print("=" * 80)
print("🔄 CDC MODE - Incremental Bronze (App Model)")
print("=" * 80)

# COMMAND ----------

# CDC metadata in same catalog/schema as bronze
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.cdc_metadata (
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
    result = spark.sql(f"""
        SELECT last_modified_timestamp FROM {catalog}.{schema}.cdc_metadata
        WHERE entity_name = '{entity}' AND sync_status = 'SUCCESS'
        ORDER BY sync_completed_at DESC LIMIT 1
    """).collect()
    if result and result[0][0]:
        return result[0][0]
    default = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"   No previous sync for {entity}, using {default}")
    return default

def update_sync_metadata(entity: str, records: int, max_modified: str, status: str, started_at: datetime):
    completed_at = datetime.utcnow()
    spark.sql(f"""
        INSERT INTO {catalog}.{schema}.cdc_metadata VALUES (
            '{entity}', CURRENT_TIMESTAMP(), '{max_modified}', {records}, '{status}',
            TIMESTAMP('{started_at.strftime("%Y-%m-%d %H:%M:%S")}'),
            TIMESTAMP('{completed_at.strftime("%Y-%m-%d %H:%M:%S")}')
        )
    """)

# COMMAND ----------

def fetch_records_by_filter(endpoint: str, search_param: str, page_size: int = 100) -> List[Dict]:
    all_records: List[Dict] = []
    page = 1
    has_more = True
    while has_more:
        url = f"{api_base_url}{endpoint}"
        params = {"search": search_param, "limit": page_size, "page": page}
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
            print(f"   Error: {e}")
            has_more = False
    return all_records

def fetch_modified_records(endpoint: str, since_timestamp: str, page_size: int = 100) -> List[Dict]:
    modified_param = f"modified>='{since_timestamp}'"
    modified_records = fetch_records_by_filter(endpoint, modified_param, page_size)
    created_param = f"created>='{since_timestamp}'"
    created_records = fetch_records_by_filter(endpoint, created_param, page_size)
    seen = set()
    out = []
    for r in modified_records + created_records:
        rid = r.get("id")
        if rid and rid not in seen:
            seen.add(rid)
            out.append(r)
    return out

# Same normalization as 00b so schema matches
def records_to_df(records: List[Dict]) -> Optional[DataFrame]:
    if not records:
        return None
    normalized: List[Dict] = []
    for rec in records:
        out: Dict = {}
        for k, v in rec.items():
            if isinstance(v, (dict, list)):
                out[k] = _json.dumps(v, ensure_ascii=False)
            elif v is None:
                out[k] = ""
            else:
                out[k] = v
        normalized.append(out)
    return spark.createDataFrame(normalized)

def merge_to_bronze(records: List[Dict], table_name: str, key_column: str = "id") -> int:
    """DELETE existing rows by id, then APPEND new rows. Enables mergeSchema so _cdc_updated_at is added."""
    if not records:
        return 0
    df = records_to_df(records)
    if df is None:
        return 0
    df = df.withColumn("_cdc_updated_at", F.current_timestamp())
    full_name = f"{catalog}.{schema}.{table_name}"

    if not spark.catalog.tableExists(full_name):
        df.write.format("delta").mode("overwrite").saveAsTable(full_name)
        print(f"   ✅ {full_name}: created with {len(records)} rows")
        return len(records)

    ids = [str(r.get(key_column, "")) for r in records if r.get(key_column)]
    if ids:
        ids_escaped = "', '".join(i.replace("'", "''") for i in ids[:50000])
        spark.sql(f"DELETE FROM {full_name} WHERE {key_column} IN ('{ids_escaped}')")
    target_cols = {c.lower() for c in spark.table(full_name).columns}
    source_cols = [c for c in df.columns if c.lower() in target_cols or c == "_cdc_updated_at"]
    df_to_append = df.select(source_cols)
    df_to_append.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(full_name)
    print(f"   ✅ {full_name}: merged {len(records)} rows")
    return len(records)

# COMMAND ----------

# Entity config: (entity_name, api_endpoint, bronze_table_name)
CDC_ENTITIES = [
    ("properties", "/properties", "qobrix_api_properties"),
    ("agents", "/agents", "qobrix_api_agents"),
    ("projects", "/projects", "qobrix_api_projects"),
    ("project_features", "/project-features", "qobrix_api_project_features"),
    ("property_types", "/property-types", "qobrix_api_property_types"),
    ("property_subtypes", "/property-subtypes", "qobrix_api_property_subtypes"),
    ("contacts", "/contacts", "qobrix_api_contacts"),
    ("users", "/users", "qobrix_api_users"),
    ("property_viewings", "/property-viewings", "qobrix_api_property_viewings"),
    ("opportunities", "/opportunities", "qobrix_api_opportunities"),
    ("media_categories", "/media/categories", "qobrix_api_media_categories"),
]

cdc_changes = {}

for entity_name, endpoint, table_name in CDC_ENTITIES:
    print("\n" + "=" * 60)
    print(f"📥 CDC: {entity_name} -> {table_name}")
    print("=" * 60)
    started_at = datetime.utcnow()
    last_sync = get_last_sync(entity_name)
    modified = fetch_modified_records(endpoint, last_sync)
    if modified:
        max_modified = max((r.get("modified") or "") for r in modified)
        merged = merge_to_bronze(modified, table_name, "id")
        cdc_changes[entity_name] = merged
        update_sync_metadata(entity_name, merged, max_modified, "SUCCESS", started_at)
    else:
        cdc_changes[entity_name] = 0
        update_sync_metadata(entity_name, 0, last_sync, "SUCCESS", started_at)
        print("   No changes since last sync.")

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 CDC BRONZE SUMMARY")
print("=" * 80)
for entity, count in cdc_changes.items():
    print(f"   {entity}: {count} rows updated")
print("\n✅ Run silver (02e, 02f, …) and gold (03e, 03f, …) to refresh downstream.")
print("=" * 80)
