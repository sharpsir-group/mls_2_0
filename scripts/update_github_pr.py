#!/usr/bin/env python3
"""PATCH an open GitHub PR (title + body). Uses GITHUB_TOKEN or GH_TOKEN from the environment.

Example:
  export GITHUB_TOKEN=ghp_...
  python3 scripts/update_github_pr.py

  # Or another PR:
  python3 scripts/update_github_pr.py --pr 7
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "sharpsir-group"
REPO = "mls_2_0"

DEFAULT_TITLE = "Full sync clear version"

DEFAULT_BODY = """## Summary

This PR bundles **pipeline notifications (Resend)** and **full-sync resilience** so scheduled runs finish reliably and operators always get a report.

### Email & configuration
- **`NOTIFY_EMAILS`** in `.env` (comma-separated); documented in `.env.example`.
- **`cron_all_sources_cdc.sh`**, **`cron_cdc_pipeline.sh`**, **`onetime_full_refresh.sh`**: reports via **Resend** (verified sender domain), multi-recipient JSON payloads.

### Full sync wrapper
- **`run_full_sync_with_report.sh`**: runs `run_pipeline.sh all`, **`trap ... EXIT`** so email is sent on **any** exit (success, failure, signal); **`timeout 43200`** (12h) so long **Bronze Full Refresh** (~8h) is not killed at 6h; cron self-removal after run.

### Pipeline runner
- **`run_pipeline.sh`**: `PATH` prefers `~/bin` (new Databricks CLI); default **`MLS_NOTEBOOK_BASE=/mls_etl/notebooks`**; poll loop treats **`INTERNAL_ERROR`** and **`SKIPPED`** as terminal (no infinite wait); clearer failure line (`state=` + `result=`).

### Gold ETL (schema drift)
- **`03_gold_reso_property_etl.py`**: **`bcol()`** and **`_safe_bronze_sql()`** — missing bronze columns (e.g. `investment_type`) are padded with **`NULL`** via a safe subquery so **`UNRESOLVED_COLUMN`** does not break the job.

### Tests
- **`tests/test_pipeline_resilience.py`**: 19 pytest checks (column safety, poll states, email/trap/timeout, SQL sanity).

## Commits (vs `main`)

1. `Pipeline reports: NOTIFY_EMAILS in .env, Resend for all cron scripts`
2. `Full sync pipeline: resilience fixes + TDD tests`

## Files changed (high level)

| Path | Change |
|------|--------|
| `.env.example` | `NOTIFY_EMAILS` placeholder |
| `notebooks/03_gold_reso_property_etl.py` | Safe bronze column handling |
| `scripts/cron_all_sources_cdc.sh` | Resend + recipients from env |
| `scripts/cron_cdc_pipeline.sh` | Resend + recipients from env |
| `scripts/onetime_full_refresh.sh` | Resend + `.env` load |
| `scripts/run_full_sync_with_report.sh` | **New** — trap EXIT, 12h timeout, email always |
| `scripts/run_pipeline.sh` | PATH, notebook base, poll terminal states |
| `tests/test_pipeline_resilience.py` | **New** — 19 tests |

## How to verify

```bash
python3 -m pytest tests/test_pipeline_resilience.py -v
```

- Full pipeline: Bronze → Silver → Gold → Exports → Integrity (production run ~8h+ total is expected for full refresh).
- Data: bronze property row count should match `reso_gold.property` for Qobrix slice after successful run.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Update GitHub PR title and body")
    parser.add_argument("--pr", type=int, default=5, help="Pull request number")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="PR title")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print(
            "Set GITHUB_TOKEN or GH_TOKEN in the environment (PAT with repo scope).",
            file=sys.stderr,
        )
        return 1

    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{args.pr}"
    payload = json.dumps({"title": args.title, "body": DEFAULT_BODY}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1

    print(f"Updated PR #{data['number']}: {data['title']}")
    print(data["html_url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
