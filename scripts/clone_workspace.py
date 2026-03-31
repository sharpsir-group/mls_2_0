#!/usr/bin/env python3
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
MLS 2.0 Cross-Workspace Clone Tool

Replicates all tables from a source Databricks workspace into your
local workspace.  By default copies every table (bronze, silver, gold,
exports) directly for an exact clone.  Use --bronze-only to replicate
only bronze and regenerate derived layers via ETL notebooks.

Requires CLONE_SOURCE_* vars in .env (see .env.example section 6).
Your workspace uses the standard DATABRICKS_* vars.

Usage:
    python3 scripts/clone_workspace.py                 # full clone (all tables)
    python3 scripts/clone_workspace.py --resume        # retry only failed/mismatched
    python3 scripts/clone_workspace.py --bronze-only   # bronze + regenerate derived
    python3 scripts/clone_workspace.py --verify-only   # compare counts
    python3 scripts/clone_workspace.py --tables t1,t2  # specific tables
"""
import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' package required.  pip install requests")

# ---------------------------------------------------------------------------
# Locate project files
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
MLS2_ROOT = SCRIPT_DIR.parent
SCHEMA_FILE = SCRIPT_DIR / "schema.json"

for line in (MLS2_ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SOURCE = {
    "host": os.getenv("CLONE_SOURCE_HOST", "").strip().rstrip("/"),
    "token": os.getenv("CLONE_SOURCE_TOKEN", "").strip(),
    "warehouse_id": os.getenv("CLONE_SOURCE_WAREHOUSE_ID", "").strip(),
    "catalog": os.getenv("CLONE_SOURCE_CATALOG", "mls2").strip(),
}
TARGET = {
    "host": os.getenv("DATABRICKS_HOST", "").strip().rstrip("/"),
    "token": os.getenv("DATABRICKS_TOKEN", "").strip(),
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", "").strip(),
    "catalog": os.getenv("DATABRICKS_CATALOG", "mls_2_0").strip(),
}

for cfg_name, cfg in [("CLONE_SOURCE", SOURCE), ("DATABRICKS (target)", TARGET)]:
    if not cfg["host"] or not cfg["token"] or not cfg["warehouse_id"]:
        sys.exit(f"ERROR: {cfg_name} credentials incomplete in .env")

if not SOURCE["host"].startswith("https://"):
    SOURCE["host"] = f"https://{SOURCE['host']}"
if not TARGET["host"].startswith("https://"):
    TARGET["host"] = f"https://{TARGET['host']}"

BATCH_SIZE = 2000
SMALL_TABLE_THRESHOLD = 500


def batch_size_for(col_count):
    """Keep batches reasonable for upload chunking, even though EXTERNAL_LINKS
    removes the 25 MiB read limit."""
    if col_count > 300:
        return 500
    if col_count > 100:
        return 1000
    return BATCH_SIZE

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
BRONZE_PREFIXES = ("qobrix_bronze.", "dash_bronze.")
EXTRA_TABLES = ("exports.homesoverseas_id_map",)


def load_schema():
    return json.loads(SCHEMA_FILE.read_text())


def bronze_tables(schema_def, table_filter=None):
    """Return dict of {fq_name: {col: type}} for tables to replicate."""
    tables = schema_def.get("tables", {})
    result = {}
    for fq, cols in tables.items():
        if fq.startswith(BRONZE_PREFIXES) or fq in EXTRA_TABLES:
            if table_filter and fq not in table_filter:
                continue
            result[fq] = cols
    return result


def all_tables(schema_def):
    return schema_def.get("tables", {})


# ---------------------------------------------------------------------------
# Databricks SQL HTTP API
# ---------------------------------------------------------------------------
def exec_sql(cfg, stmt, poll_limit=600):
    url = f"{cfg['host']}/api/2.0/sql/statements"
    hdr = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
    r = requests.post(url, headers=hdr, json={
        "warehouse_id": cfg["warehouse_id"],
        "statement": stmt,
        "wait_timeout": "50s",
    }, timeout=120)
    r.raise_for_status()
    d = r.json()
    st = d.get("status", {}).get("state", "")
    if st in ("PENDING", "RUNNING"):
        sid = d["statement_id"]
        for _ in range(poll_limit):
            time.sleep(5)
            p = requests.get(f"{url}/{sid}", headers=hdr, timeout=60)
            p.raise_for_status()
            d = p.json()
            st = d.get("status", {}).get("state", "")
            if st not in ("PENDING", "RUNNING"):
                break
    if st != "SUCCEEDED":
        msg = d.get("status", {}).get("error", {}).get("message", "?")[:400]
        raise RuntimeError(f"SQL {st}: {msg}")
    return d


def row_count(cfg, full_table):
    d = exec_sql(cfg, f"SELECT COUNT(*) FROM {full_table}")
    return int(d["result"]["data_array"][0][0])


def read_batch(cfg, full_table, col_names, offset, limit):
    """Read rows using EXTERNAL_LINKS disposition (no 25 MiB result limit)."""
    col_list = ", ".join(f"`{c}`" for c in col_names)
    stmt = f"SELECT {col_list} FROM {full_table} LIMIT {limit} OFFSET {offset}"
    url = f"{cfg['host']}/api/2.0/sql/statements"
    hdr = {"Authorization": f"Bearer {cfg['token']}",
           "Content-Type": "application/json"}

    r = requests.post(url, headers=hdr, json={
        "warehouse_id": cfg["warehouse_id"],
        "statement": stmt,
        "wait_timeout": "50s",
        "disposition": "EXTERNAL_LINKS",
        "format": "JSON_ARRAY",
    }, timeout=120)
    r.raise_for_status()
    d = r.json()

    st = d.get("status", {}).get("state", "")
    sid = d["statement_id"]
    if st in ("PENDING", "RUNNING"):
        for _ in range(600):
            time.sleep(5)
            p = requests.get(f"{url}/{sid}", headers=hdr, timeout=60)
            p.raise_for_status()
            d = p.json()
            st = d.get("status", {}).get("state", "")
            if st not in ("PENDING", "RUNNING"):
                break
    if st != "SUCCEEDED":
        msg = d.get("status", {}).get("error", {}).get("message", "?")[:400]
        raise RuntimeError(f"SQL {st}: {msg}")

    rows = []
    ext_links = d.get("result", {}).get("external_links", [])
    for lnk in ext_links:
        dl_url = lnk.get("external_link")
        if dl_url:
            resp = requests.get(dl_url, timeout=300)
            resp.raise_for_status()
            chunk = resp.json()
            if isinstance(chunk, list):
                rows.extend(chunk)

    next_link = (ext_links[0].get("next_chunk_internal_link")
                 if ext_links else None)
    while next_link:
        cr = requests.get(f"{cfg['host']}{next_link}", headers={
            "Authorization": f"Bearer {cfg['token']}"}, timeout=300)
        cr.raise_for_status()
        cd = cr.json()
        for lnk in cd.get("external_links", []):
            dl_url = lnk.get("external_link")
            if dl_url:
                resp = requests.get(dl_url, timeout=300)
                resp.raise_for_status()
                chunk = resp.json()
                if isinstance(chunk, list):
                    rows.extend(chunk)
        next_link = cd.get("external_links", [{}])[0].get(
            "next_chunk_internal_link") if cd.get("external_links") else None
    return rows


# ---------------------------------------------------------------------------
# Data transfer helpers
# ---------------------------------------------------------------------------
def rows_to_jsonl(col_names, rows):
    lines = []
    for row in rows:
        obj = {}
        for i, col in enumerate(col_names):
            v = row[i] if i < len(row) else None
            obj[col] = str(v) if v is not None else None
        lines.append(json.dumps(obj, ensure_ascii=False))
    return ("\n".join(lines) + "\n").encode("utf-8")


def upload_file(cfg, vol_path, data):
    r = requests.put(
        f"{cfg['host']}/api/2.0/fs/files{vol_path}?overwrite=true",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/octet-stream",
        },
        data=data, timeout=300,
    )
    r.raise_for_status()


def rm_volume_dir(cfg, vol_path):
    requests.delete(
        f"{cfg['host']}/api/2.0/fs/directories{vol_path}/",
        headers={"Authorization": f"Bearer {cfg['token']}"},
        timeout=60,
    )


def escape_val(val, col_type):
    """Escape a value for INSERT INTO ... VALUES (small-table fallback)."""
    if val is None:
        return "NULL"
    s = str(val)
    up = col_type.upper()
    if s == "" and "STRING" not in up:
        return "NULL"
    if any(t in up for t in ("INT", "LONG", "BIGINT")):
        return s if s not in ("", "None", "null") else "NULL"
    if any(t in up for t in ("TIMESTAMP", "DATE")):
        return f"'{s}'" if s not in ("", "None", "null") else "NULL"
    if any(t in up for t in ("BOOLEAN",)):
        return s if s.lower() in ("true", "false") else "NULL"
    return f"'{s.replace(chr(39), chr(39)+chr(39))}'"


COMPLEX_TYPE_PREFIXES = ("ARRAY", "MAP", "STRUCT")


def _cast_expr(col, col_type):
    """Build a SELECT expression that converts a STRING staging column to its
    real type.  Uses from_json for complex types (ARRAY, MAP, STRUCT) because
    SQL CAST cannot handle those conversions."""
    up = col_type.upper()
    if up == "STRING":
        return f"`{col}`"
    if any(up.startswith(p) for p in COMPLEX_TYPE_PREFIXES):
        return f"from_json(`{col}`, '{col_type}') AS `{col}`"
    return f"CAST(`{col}` AS {col_type}) AS `{col}`"


# ---------------------------------------------------------------------------
# Transfer strategies
# ---------------------------------------------------------------------------
def transfer_small(fq, cols, src_catalog, tgt_catalog):
    """INSERT INTO ... VALUES for tables under SMALL_TABLE_THRESHOLD rows."""
    full_src = f"{src_catalog}.{fq}"
    full_tgt = f"{tgt_catalog}.{fq}"
    col_names = list(cols.keys())
    col_types = list(cols.values())

    src_cnt = row_count(SOURCE, full_src)
    print(f"  {fq}: {src_cnt} rows (small-table INSERT)")
    sys.stdout.flush()

    col_items = list(cols.items())
    exec_sql(TARGET, f"DROP TABLE IF EXISTS {full_tgt}")
    real_cols = ", ".join(f"`{c}` {t}" for c, t in col_items)
    exec_sql(TARGET, f"CREATE TABLE {full_tgt} ({real_cols}) USING delta")

    rows = read_batch(SOURCE, full_src, col_names, 0, src_cnt + 100)
    if not rows:
        tgt_cnt = row_count(TARGET, full_tgt)
        return src_cnt, tgt_cnt

    chunk = 50
    for i in range(0, len(rows), chunk):
        batch = rows[i:i + chunk]
        value_rows = []
        for row in batch:
            vals = []
            for j, cn in enumerate(col_names):
                v = row[j] if j < len(row) else None
                vals.append(escape_val(v, col_types[j]))
            value_rows.append(f"({', '.join(vals)})")
        col_list = ", ".join(f"`{c}`" for c in col_names)
        exec_sql(TARGET,
                 f"INSERT INTO {full_tgt} ({col_list}) VALUES {', '.join(value_rows)}")

    tgt_cnt = row_count(TARGET, full_tgt)
    return src_cnt, tgt_cnt


def transfer_large(fq, cols, src_catalog, tgt_catalog):
    """JSONL + all-STRING staging table + INSERT with CAST."""
    full_src = f"{src_catalog}.{fq}"
    full_tgt = f"{tgt_catalog}.{fq}"
    col_names = list(cols.keys())
    col_items = list(cols.items())

    schema_name = fq.split(".")[0]
    safe = fq.replace(".", "_")
    run_id = str(int(time.time()))
    stage_dir = f"/Volumes/{tgt_catalog}/{schema_name}/staging/{safe}_{run_id}"
    staging_tbl = f"{tgt_catalog}.{schema_name}._stg_{safe}"

    src_cnt = row_count(SOURCE, full_src)
    batch = batch_size_for(len(col_names))
    print(f"  {fq}: {src_cnt} rows, {len(col_names)} cols (JSONL+staging, batch={batch})")
    sys.stdout.flush()

    # Ensure staging volume exists
    try:
        exec_sql(TARGET, f"CREATE VOLUME IF NOT EXISTS {tgt_catalog}.{schema_name}.staging")
    except Exception:
        pass

    # Step 1: Upload JSONL
    rm_volume_dir(TARGET, stage_dir)
    off, part, tot = 0, 0, 0
    t0 = time.time()
    while off < src_cnt:
        rows = read_batch(SOURCE, full_src, col_names, off, batch)
        if not rows:
            break
        upload_file(TARGET, f"{stage_dir}/p{part:06d}.jsonl",
                    rows_to_jsonl(col_names, rows))
        tot += len(rows)
        off += len(rows)
        part += 1
        el = time.time() - t0
        rate = tot / el if el > 0 else 0
        eta = (src_cnt - tot) / rate if rate > 0 else 0
        print(f"    upload [{tot:>8}/{src_cnt}] {rate:.0f} r/s ETA {eta:.0f}s")
        sys.stdout.flush()

    # Step 2: Create all-STRING staging table
    col_defs = ", ".join(f"`{c}` STRING" for c in col_names)
    exec_sql(TARGET, f"DROP TABLE IF EXISTS {staging_tbl}")
    exec_sql(TARGET, f"CREATE TABLE {staging_tbl} ({col_defs}) USING delta")

    # Step 3: COPY INTO staging (zero type conflicts)
    print(f"    COPY INTO staging...")
    sys.stdout.flush()
    exec_sql(TARGET, f"""
        COPY INTO {staging_tbl}
        FROM '{stage_dir}'
        FILEFORMAT = JSON
        FORMAT_OPTIONS ('primitivesAsString' = 'true')
        COPY_OPTIONS ('force' = 'true')
    """, poll_limit=1200)

    # Step 4: Verify staging count, then DROP + CREATE real table and INSERT with CAST
    stg_cnt = row_count(TARGET, staging_tbl)
    if stg_cnt != src_cnt:
        print(f"    WARNING: staging has {stg_cnt} rows, expected {src_cnt}")
    print(f"    INSERT with CAST into target...")
    sys.stdout.flush()
    exec_sql(TARGET, f"DROP TABLE IF EXISTS {full_tgt}")
    real_cols = ", ".join(f"`{c}` {t}" for c, t in col_items)
    exec_sql(TARGET, f"CREATE TABLE {full_tgt} ({real_cols}) USING delta")
    casts = ", ".join(_cast_expr(c, t) for c, t in col_items)
    exec_sql(TARGET, f"INSERT INTO {full_tgt} SELECT {casts} FROM {staging_tbl}",
             poll_limit=1200)

    # Step 5: Cleanup
    exec_sql(TARGET, f"DROP TABLE IF EXISTS {staging_tbl}")
    rm_volume_dir(TARGET, stage_dir)

    tgt_cnt = row_count(TARGET, full_tgt)
    return src_cnt, tgt_cnt


def replicate_table(fq, cols, src_catalog, tgt_catalog):
    """Pick the right transfer strategy and return (src_count, tgt_count)."""
    full_src = f"{src_catalog}.{fq}"
    try:
        cnt = row_count(SOURCE, full_src)
    except Exception as e:
        print(f"  {fq}: SKIP (source error: {e})")
        return -1, -1

    if cnt <= SMALL_TABLE_THRESHOLD:
        return transfer_small(fq, cols, src_catalog, tgt_catalog)
    else:
        return transfer_large(fq, cols, src_catalog, tgt_catalog)


# ---------------------------------------------------------------------------
# Derived layer regeneration
# ---------------------------------------------------------------------------
PIPELINE_SCRIPT = MLS2_ROOT / "scripts" / "run_pipeline.sh"


def run_pipeline_stage(stage):
    """Run a run_pipeline.sh stage (silver, gold, export-homesoverseas)."""
    print(f"\n  Running: run_pipeline.sh {stage}")
    sys.stdout.flush()
    result = subprocess.run(
        ["bash", str(PIPELINE_SCRIPT), stage],
        cwd=str(MLS2_ROOT),
        timeout=3600,
    )
    if result.returncode != 0:
        print(f"  WARNING: run_pipeline.sh {stage} exited with {result.returncode}")
    return result.returncode == 0


def run_notebook_direct(name, notebook_path, catalog):
    """Submit a Databricks notebook job and wait for completion."""
    print(f"\n  Running notebook: {name}")
    sys.stdout.flush()
    payload = {
        "run_name": name,
        "tasks": [{
            "task_key": "task",
            "notebook_task": {
                "notebook_path": notebook_path,
                "base_parameters": {"DATABRICKS_CATALOG": catalog},
            },
        }],
    }
    url = f"{TARGET['host']}/api/2.0/jobs/runs/submit"
    hdr = {"Authorization": f"Bearer {TARGET['token']}",
           "Content-Type": "application/json"}
    r = requests.post(url, headers=hdr, json=payload, timeout=60)
    r.raise_for_status()
    run_id = r.json().get("run_id")
    if not run_id:
        print(f"  WARNING: Could not submit {name}")
        return False

    print(f"    Run ID: {run_id}")
    while True:
        time.sleep(10)
        p = requests.get(
            f"{TARGET['host']}/api/2.0/jobs/runs/get?run_id={run_id}",
            headers=hdr, timeout=60)
        p.raise_for_status()
        state = p.json().get("state", {})
        lcs = state.get("life_cycle_state", "")
        if lcs == "TERMINATED":
            rs = state.get("result_state", "")
            if rs == "SUCCESS":
                print(f"    {name}: SUCCESS")
                return True
            else:
                print(f"    {name}: FAILED ({rs})")
                return False


def regenerate_derived(catalog):
    """Run silver, gold, and export ETL stages."""
    nb_base = os.getenv("MLS_NOTEBOOK_BASE", "/Shared/mls_2_0")

    print("\n" + "=" * 60)
    print("Phase 3a: Qobrix Silver")
    print("=" * 60)
    run_pipeline_stage("silver")

    print("\n" + "=" * 60)
    print("Phase 3b: Dash Silver")
    print("=" * 60)
    for nb in [
        ("Dash Silver Property ETL", f"{nb_base}/01_dash_silver_property_etl"),
        ("Dash Silver Features ETL", f"{nb_base}/01b_dash_silver_features_etl"),
        ("Dash Silver Media ETL", f"{nb_base}/01_dash_silver_media_etl"),
    ]:
        run_notebook_direct(nb[0], nb[1], catalog)

    print("\n" + "=" * 60)
    print("Phase 3c: RESO Gold")
    print("=" * 60)
    run_pipeline_stage("gold")

    print("\n" + "=" * 60)
    print("Phase 3d: Exports")
    print("=" * 60)
    run_pipeline_stage("export-homesoverseas")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify_all(schema_def, src_catalog, tgt_catalog):
    """Compare row counts for every table between source and target."""
    tables = schema_def.get("tables", {})
    print(f"\n{'Table':<45} {'Source':>10} {'Target':>10} {'Status':>10}")
    print("-" * 78)

    mismatches = 0
    errors = 0
    for fq in sorted(tables):
        full_src = f"{src_catalog}.{fq}"
        full_tgt = f"{tgt_catalog}.{fq}"
        try:
            s = row_count(SOURCE, full_src)
        except Exception:
            s = -1
        try:
            t = row_count(TARGET, full_tgt)
        except Exception:
            t = -1

        if s < 0 or t < 0:
            status = "ERROR"
            errors += 1
        elif s == t:
            status = "OK"
        else:
            diff = t - s
            status = f"{diff:+d}"
            mismatches += 1
        print(f"  {fq:<43} {s:>10} {t:>10} {status:>10}")

    print("-" * 78)
    ok = len(tables) - mismatches - errors
    print(f"  OK: {ok}  |  Mismatches: {mismatches}  |  Errors: {errors}")
    return mismatches == 0 and errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="MLS 2.0 Cross-Workspace Clone Tool"
    )
    parser.add_argument(
        "--bronze-only", action="store_true",
        help="Replicate only bronze tables, then regenerate derived via ETL",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only compare row counts (no data transfer)",
    )
    parser.add_argument(
        "--tables",
        help="Comma-separated list of specific tables to replicate",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip tables where source and target row counts already match",
    )
    args = parser.parse_args()

    schema_def = load_schema()
    src_cat = SOURCE["catalog"]
    tgt_cat = TARGET["catalog"]

    print()
    print("=" * 60)
    print("  MLS 2.0 Cross-Workspace Clone")
    print("=" * 60)
    print(f"  Source: {SOURCE['host']}  catalog={src_cat}")
    print(f"  Target: {TARGET['host']}  catalog={tgt_cat}")

    # -- Verify only --
    if args.verify_only:
        print(f"\n  Mode: VERIFY ONLY")
        print("=" * 60)
        ok = verify_all(schema_def, src_cat, tgt_cat)
        return 0 if ok else 1

    # -- Build replication list --
    table_filter = None
    if args.tables:
        table_filter = set(t.strip() for t in args.tables.split(","))

    if args.bronze_only:
        to_replicate = bronze_tables(schema_def, table_filter)
    else:
        tbl = all_tables(schema_def)
        to_replicate = {fq: cols for fq, cols in tbl.items()
                        if not table_filter or fq in table_filter}

    print(f"\n  Tables to replicate: {len(to_replicate)}")
    mode_parts = []
    if args.resume:
        mode_parts.append("RESUME (skip matched)")
    if args.bronze_only:
        mode_parts.append("BRONZE ONLY + regenerate derived")
    else:
        mode_parts.append("FULL CLONE (all tables)")
    print(f"  Mode: {' | '.join(mode_parts)}")
    print("=" * 60)

    print(f"\nPhase 1: Bootstrap (validate_deployment.py)")
    print("-" * 40)
    vd = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_deployment.py")],
        cwd=str(MLS2_ROOT),
    )
    if vd.returncode != 0:
        print("WARNING: validate_deployment.py reported issues")

    label = "Bronze" if args.bronze_only else "All"
    print(f"\nPhase 2: Replicate {label} ({len(to_replicate)} tables)")
    print("-" * 40)

    results = {}
    skipped = 0
    t_start = time.time()
    for fq in sorted(to_replicate):
        cols = to_replicate[fq]

        if args.resume:
            full_src = f"{src_cat}.{fq}"
            full_tgt = f"{tgt_cat}.{fq}"
            try:
                s = row_count(SOURCE, full_src)
                t = row_count(TARGET, full_tgt)
                if s == t and s >= 0:
                    results[fq] = (s, t, "OK")
                    print(f"  {fq}: {s} rows  [SKIP - already matches]")
                    sys.stdout.flush()
                    skipped += 1
                    continue
            except Exception:
                pass

        try:
            src_cnt, tgt_cnt = replicate_table(fq, cols, src_cat, tgt_cat)
            match = "OK" if src_cnt == tgt_cnt else "MISMATCH"
            results[fq] = (src_cnt, tgt_cnt, match)
            print(f"    -> src={src_cnt} tgt={tgt_cnt} [{match}]")
        except Exception as e:
            results[fq] = (-1, -1, f"FAILED: {e}")
            print(f"    -> FAILED: {e}")
        sys.stdout.flush()

    elapsed = time.time() - t_start
    print(f"\n  Replication done in {elapsed:.0f}s")
    if skipped:
        print(f"  Skipped (already matched): {skipped}")

    failed = [fq for fq, (_, _, s) in results.items() if s != "OK"]
    if failed:
        print(f"\n  WARNING: {len(failed)} table(s) had issues:")
        for fq in failed:
            print(f"    {fq}: {results[fq][2]}")

    # -- Regenerate derived layers (only in bronze-only mode) --
    if args.bronze_only and not args.tables:
        print(f"\nPhase 3: Regenerate Derived Layers")
        print("-" * 40)
        regenerate_derived(tgt_cat)

    # -- Fallback: regenerate failed derived tables from bronze --
    if failed and not args.bronze_only:
        nb_base = os.getenv("MLS_NOTEBOOK_BASE", "/Shared/mls_2_0")
        etl_for_table = {
            "dash_silver.media": ("Dash Silver Media ETL",
                                  f"{nb_base}/01_dash_silver_media_etl"),
            "dash_silver.property": ("Dash Silver Property ETL",
                                     f"{nb_base}/01_dash_silver_property_etl"),
            "dash_silver.property_features": ("Dash Silver Features ETL",
                                              f"{nb_base}/01b_dash_silver_features_etl"),
            "exports.homesoverseas": ("Export HomeOverseas",
                                      f"{nb_base}/04a_export_homesoverseas_etl"),
        }
        regen = [fq for fq in failed if fq in etl_for_table]
        if regen:
            print(f"\nPhase 3: Regenerate {len(regen)} failed derived table(s)")
            print("-" * 40)
            for fq in regen:
                name, path = etl_for_table[fq]
                ok = run_notebook_direct(name, path, tgt_cat)
                if ok:
                    results[fq] = (results[fq][0], -1, "REGENERATED")
                    print(f"    {fq}: regenerated from bronze")
            failed = [fq for fq, (_, _, s) in results.items()
                      if s not in ("OK", "REGENERATED")]

    # -- Verify --
    print(f"\nPhase 4: Verification")
    print("-" * 40)
    if args.tables:
        print("  (Skipping full verification -- specific tables mode)")
        for fq, (s, t, status) in sorted(results.items()):
            print(f"  {fq}: src={s} tgt={t} [{status}]")
    else:
        verify_all(schema_def, src_cat, tgt_cat)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
