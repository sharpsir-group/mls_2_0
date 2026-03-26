#!/usr/bin/env python3
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
MLS 2.0 Deployment Validator & Schema Bootstrapper

Reads the proven schema definition from scripts/schema.json (extracted from
the working mls2 catalog) and recreates an identical catalog/schema/table
structure on any Databricks workspace.

Usage:
    python3 scripts/validate_deployment.py              # validate + bootstrap
    python3 scripts/validate_deployment.py --check      # validate only (no changes)
    python3 scripts/validate_deployment.py --verbose     # show column details

Run from: mls_2_0/ directory (or any — the script locates .env automatically).
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate project files
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
MLS2_ROOT = SCRIPT_DIR.parent
SCHEMA_FILE = SCRIPT_DIR / "schema.json"

# Load .env
ENV_FILE = MLS2_ROOT / ".env"
if not ENV_FILE.exists():
    ENV_FILE = MLS2_ROOT / "api" / ".env"

if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ---------------------------------------------------------------------------
# Configuration from .env
# ---------------------------------------------------------------------------
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "").strip().rstrip("/")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "").strip()
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "").strip()
CATALOG = os.getenv("DATABRICKS_CATALOG", "mls_2_0").strip()

if DATABRICKS_HOST and not DATABRICKS_HOST.startswith("https://"):
    DATABRICKS_HOST = f"https://{DATABRICKS_HOST}"

# ---------------------------------------------------------------------------
# Load schema definition (source of truth extracted from working mls2 catalog)
# ---------------------------------------------------------------------------
def load_schema() -> dict:
    if not SCHEMA_FILE.exists():
        print(f"  [FAIL] {SCHEMA_FILE} not found")
        sys.exit(1)
    return json.loads(SCHEMA_FILE.read_text())


# ---------------------------------------------------------------------------
# Databricks SQL HTTP API helper
# ---------------------------------------------------------------------------
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class DatabricksSQL:
    """Minimal sync client for Databricks SQL Statements API."""

    def __init__(self, host: str, token: str, warehouse_id: str):
        self.url = f"{host}/api/2.0/sql/statements"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.warehouse_id = warehouse_id

    def execute(self, sql: str, timeout: int = 60) -> dict:
        payload = {
            "warehouse_id": self.warehouse_id,
            "statement": sql,
            "wait_timeout": "30s",
            "on_wait_timeout": "CONTINUE",
        }
        body = json.dumps(payload)

        if HAS_HTTPX:
            resp = httpx.post(self.url, headers=self.headers, content=body, timeout=timeout)
            result = resp.json()
        elif HAS_REQUESTS:
            resp = requests.post(self.url, headers=self.headers, data=body, timeout=timeout)
            result = resp.json()
        else:
            raise RuntimeError("Neither httpx nor requests is installed")

        status = result.get("status", {}).get("state", "")
        statement_id = result.get("statement_id", "")

        while status in ("PENDING", "RUNNING"):
            time.sleep(1)
            poll_url = f"{self.url}/{statement_id}"
            if HAS_HTTPX:
                pr = httpx.get(poll_url, headers=self.headers, timeout=timeout)
                result = pr.json()
            else:
                pr = requests.get(poll_url, headers=self.headers, timeout=timeout)
                result = pr.json()
            status = result.get("status", {}).get("state", "")

        if status == "FAILED":
            err = result.get("status", {}).get("error", {}).get("message", "Unknown error")
            raise RuntimeError(f"SQL failed: {err}")
        if status == "CANCELED":
            raise RuntimeError("SQL canceled (timeout)")

        columns = [c["name"] for c in result.get("manifest", {}).get("schema", {}).get("columns", [])]
        data = result.get("result", {}).get("data_array", [])
        return {"columns": columns, "data": data}


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------
class Reporter:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.created = 0
        self.warnings = 0

    def ok(self, msg: str):
        self.passed += 1
        print(f"  [PASS] {msg}")

    def fail(self, msg: str):
        self.failed += 1
        print(f"  [FAIL] {msg}")

    def warn(self, msg: str):
        self.warnings += 1
        print(f"  [WARN] {msg}")

    def info(self, msg: str):
        print(f"  [INFO] {msg}")

    def made(self, msg: str):
        self.created += 1
        print(f"  [CREATED] {msg}")

    def summary(self) -> int:
        print()
        print("=" * 64)
        print(f"  PASS: {self.passed}  |  CREATED: {self.created}  |  WARN: {self.warnings}  |  FAIL: {self.failed}")
        print("=" * 64)
        if self.failed:
            print("\n  Deployment is NOT ready. Fix the failures above and re-run.")
            return 1
        if self.created:
            print("\n  Schema bootstrapped. Run the ETL pipeline to populate data:")
            print("    ./scripts/run_pipeline.sh all")
            return 0
        print("\n  Deployment is ready.")
        return 0


# ---------------------------------------------------------------------------
# Validation steps
# ---------------------------------------------------------------------------
def _mask(val: str) -> str:
    if not val:
        return ""
    return val[:8] + "..." if len(val) > 12 else "***"


def check_env(r: Reporter):
    print("\n1. Environment (.env)")
    print("-" * 40)

    if not ENV_FILE.exists():
        r.fail(".env not found — copy .env.example to .env and fill in values")
        return False

    r.ok(f".env loaded from {ENV_FILE}")

    ok = True
    for var, val in [
        ("DATABRICKS_HOST", DATABRICKS_HOST),
        ("DATABRICKS_TOKEN", DATABRICKS_TOKEN),
        ("DATABRICKS_WAREHOUSE_ID", DATABRICKS_WAREHOUSE_ID),
    ]:
        if val:
            r.ok(f"{var} = {_mask(val)}")
        else:
            r.fail(f"{var} is not set — add it to .env")
            ok = False

    r.info(f"DATABRICKS_CATALOG = {CATALOG}")
    return ok


def check_connectivity(r: Reporter, db: DatabricksSQL):
    print("\n2. Databricks connectivity")
    print("-" * 40)
    try:
        result = db.execute("SELECT 1 AS ok")
        if result["data"] and result["data"][0][0] == "1":
            r.ok("SQL warehouse reachable (SELECT 1)")
            return True
        r.fail("SELECT 1 returned unexpected result")
        return False
    except Exception as e:
        r.fail(f"Cannot reach SQL warehouse: {e}")
        return False


def check_catalog(r: Reporter, db: DatabricksSQL, check_only: bool):
    print(f"\n3. Catalog: {CATALOG}")
    print("-" * 40)
    try:
        result = db.execute(f"SHOW CATALOGS LIKE '{CATALOG}'")
        if result["data"]:
            r.ok(f"Catalog '{CATALOG}' exists")
            return True
        if check_only:
            r.fail(f"Catalog '{CATALOG}' does not exist")
            return False
        db.execute(
            f"CREATE CATALOG IF NOT EXISTS {CATALOG} "
            f"COMMENT 'MLS 2.0 datamart: Qobrix/Dash -> bronze/silver -> RESO gold'"
        )
        r.made(f"Catalog '{CATALOG}'")
        return True
    except Exception as e:
        r.fail(f"Catalog check failed: {e}")
        r.info("You may need to create the catalog via the Databricks Account Console")
        return False


def check_schemas(r: Reporter, db: DatabricksSQL, schema_def: dict, check_only: bool):
    print(f"\n4. Schemas in {CATALOG}")
    print("-" * 40)

    try:
        result = db.execute(f"SHOW SCHEMAS IN {CATALOG}")
        existing = {row[0] for row in result["data"]} if result["data"] else set()
    except Exception as e:
        r.fail(f"Cannot list schemas: {e}")
        return False

    schema_comments = {
        "qobrix_bronze": "Raw Qobrix API (Delta)",
        "qobrix_silver": "Normalized Qobrix",
        "reso_gold": "RESO Data Dictionary gold",
        "exports": "Portal exports (e.g. HomeOverseas)",
        "dash_bronze": "Dash bronze — optional",
        "dash_silver": "Dash silver — optional",
    }

    all_ok = True
    for schema_name in sorted(schema_def.get("schemas", {})):
        if schema_name in existing:
            r.ok(f"{CATALOG}.{schema_name}")
        elif check_only:
            r.fail(f"{CATALOG}.{schema_name} does not exist")
            all_ok = False
        else:
            comment = schema_comments.get(schema_name, "")
            comment_sql = f" COMMENT '{comment}'" if comment else ""
            try:
                db.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema_name}{comment_sql}")
                r.made(f"{CATALOG}.{schema_name}")
            except Exception as e:
                r.fail(f"Cannot create {CATALOG}.{schema_name}: {e}")
                all_ok = False
    return all_ok


def check_tables(r: Reporter, db: DatabricksSQL, schema_def: dict, check_only: bool, verbose: bool):
    tables = schema_def.get("tables", {})
    print(f"\n5. Tables ({len(tables)} expected)")
    print("-" * 40)

    all_ok = True
    for fq_name in sorted(tables):
        cols = tables[fq_name]
        schema_part, table_part = fq_name.split(".")
        full_name = f"{CATALOG}.{fq_name}"

        try:
            result = db.execute(f"SHOW TABLES IN {CATALOG}.{schema_part} LIKE '{table_part}'")
            exists = bool(result["data"])
        except Exception:
            exists = False

        if exists:
            try:
                cnt = db.execute(f"SELECT COUNT(*) FROM {full_name}")
                rows = int(cnt["data"][0][0]) if cnt["data"] else 0
                r.ok(f"{full_name} ({rows:,} rows)")
            except Exception as e:
                r.warn(f"{full_name} exists but query failed: {e}")

            if verbose:
                try:
                    desc = db.execute(f"DESCRIBE TABLE {full_name}")
                    existing_cols = {row[0] for row in desc["data"]}
                    expected_cols = {c.strip("`") for c in cols}
                    missing = expected_cols - existing_cols
                    if missing:
                        r.warn(f"  Missing columns: {', '.join(sorted(missing))}")
                    extra = existing_cols - expected_cols - {"", None}
                    if extra:
                        r.info(f"  Extra columns (OK): {', '.join(sorted(extra))}")
                except Exception:
                    pass
        elif check_only:
            r.fail(f"{full_name} does not exist")
            all_ok = False
        else:
            cols_sql = ",\n        ".join(
                f"`{col}` {dtype}" if not col.startswith("`") else f"{col} {dtype}"
                for col, dtype in cols.items()
            )
            ddl = f"CREATE TABLE IF NOT EXISTS {full_name} (\n        {cols_sql}\n    ) USING DELTA"
            try:
                db.execute(ddl)
                r.made(f"{full_name}")
            except Exception as e:
                r.fail(f"Cannot create {full_name}: {e}")
                all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="MLS 2.0 Deployment Validator & Schema Bootstrapper"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Validate only — do not create missing objects"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show column-level details for existing tables"
    )
    args = parser.parse_args()

    schema_def = load_schema()
    source = schema_def.get("_source_catalog", "?")

    print()
    print("=" * 64)
    print("  MLS 2.0 Deployment Validator")
    if args.check:
        print("  Mode: CHECK ONLY (no changes)")
    else:
        print("  Mode: VALIDATE + BOOTSTRAP")
    print(f"  Target catalog: {CATALOG}")
    print(f"  Schema source:  {source} ({len(schema_def.get('tables', {}))} tables)")
    print("=" * 64)

    r = Reporter()

    if not check_env(r):
        print("\n  Fix .env and re-run. See .env.example for reference.")
        return r.summary()

    db = DatabricksSQL(DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID)

    if not check_connectivity(r, db):
        return r.summary()

    if not check_catalog(r, db, args.check):
        return r.summary()

    check_schemas(r, db, schema_def, args.check)
    check_tables(r, db, schema_def, args.check, args.verbose)

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
