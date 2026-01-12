#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
#
# Dash Data Loader Orchestration Script
#
# Auto-processes all new/changed JSON files from DASH_SOURCE_DIR,
# loads to bronze, transforms through silver, and updates unified gold.
#
# Usage:
#   ./scripts/load_dash_data.sh           # Auto-process new files
#   ./scripts/load_dash_data.sh --force   # Reprocess all files

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load credentials
if [ -f "$MLS2_ROOT/.env" ]; then
    set -a
    source "$MLS2_ROOT/.env"
    set +a
else
    echo "❌ Error: $MLS2_ROOT/.env not found"
    echo "   Copy .env.example to .env and fill in your values."
    exit 1
fi

# Suppress CLI warning
export DATABRICKS_CLI_DO_NOT_SHOW_UPGRADE_MESSAGE=1

# Parse arguments
FORCE_FLAG=""
if [ "$1" = "--force" ]; then
    FORCE_FLAG="--force"
fi

# Validate required env vars
if [ -z "$DASH_SOURCE_DIR" ]; then
    echo "❌ Error: DASH_SOURCE_DIR not set in .env"
    exit 1
fi

if [ ! -d "$DASH_SOURCE_DIR" ]; then
    echo "❌ Error: Source directory not found: $DASH_SOURCE_DIR"
    exit 1
fi

echo "================================================================================"
echo "DASH DATA LOADER"
echo "================================================================================"
echo "📁 Source directory: $DASH_SOURCE_DIR"
echo "🏢 Office key: ${DASH_OFFICE_KEY:-HSIR}"
if [ -n "$FORCE_FLAG" ]; then
    echo "⚠️  Force mode: reprocessing all files"
fi
echo ""

# Track start time
START_TIME=$(date +%s)

# Function to run Databricks notebook
run_notebook() {
    local notebook_name="$1"
    local notebook_path="$2"
    local timeout="${3:-600}"
    
    echo "📓 Running: $notebook_name"
    echo "   Path: $notebook_path"
    
    # Import notebook first
    local local_notebook="$MLS2_ROOT/notebooks/$(basename "$notebook_path").py"
    if [ -f "$local_notebook" ]; then
        echo "   📤 Importing notebook..."
        databricks workspace import "$local_notebook" "$notebook_path" --language PYTHON --overwrite 2>&1 | grep -v "^WARN:" || true
    fi
    
    # Run notebook using jobs API
    local run_output
    run_output=$(databricks jobs run-now \
        --job-id "$(databricks jobs list --output json 2>/dev/null | python3 -c "
import sys, json
try:
    jobs = json.load(sys.stdin).get('jobs', [])
    for job in jobs:
        if job.get('settings', {}).get('name', '') == 'MLS 2.0 - Manual Run':
            print(job['job_id'])
            break
except:
    pass
" 2>/dev/null || echo "")" \
        --notebook-task "{\"notebook_path\": \"$notebook_path\"}" \
        2>&1 | grep -v "^WARN:" || true)
    
    if echo "$run_output" | grep -q "run_id"; then
        local run_id=$(echo "$run_output" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null || echo "")
        echo "   ✅ Started (Run ID: $run_id)"
        
        # Wait for completion
        sleep 5
    else
        echo "   ⚠️  Could not start via jobs API, trying direct execution..."
        # Fall back to running locally if jobs API fails
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Load Bronze data (auto-scan source directory)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Load Dash Bronze Data"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$MLS2_ROOT"
python3 scripts/load_dash_bronze.py $FORCE_FLAG

if [ $? -ne 0 ]; then
    echo "❌ Failed to load bronze data"
    exit 1
fi

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Run Silver ETLs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Run Dash Silver ETLs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Import and run Silver Property ETL
run_notebook "Dash Silver Property ETL" "/Shared/mls_2_0/01_dash_silver_property_etl" 300

# Import and run Silver Features ETL (NEW - parses features JSON)
run_notebook "Dash Silver Features ETL" "/Shared/mls_2_0/01b_dash_silver_features_etl" 300

# Import and run Silver Media ETL
run_notebook "Dash Silver Media ETL" "/Shared/mls_2_0/01_dash_silver_media_etl" 300

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Run Gold ETLs (unified - includes both Qobrix and Dash)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Run Unified RESO Gold ETLs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run unified Gold Property ETL (UNION of Qobrix + Dash)
run_notebook "RESO Gold Property ETL (Unified)" "/Shared/mls_2_0/03_gold_reso_property_etl" 600

# Run Gold Media ETL
run_notebook "RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" 300

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4: Verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📊 Verifying data in RESO Gold..."
echo ""
echo "Run this query in Databricks to verify:"
echo ""
echo "SELECT Country, OriginatingSystemOfficeKey, X_DataSource, COUNT(*) as count"
echo "FROM mls2.reso_gold.property"
echo "GROUP BY Country, OriginatingSystemOfficeKey, X_DataSource"
echo "ORDER BY Country, OriginatingSystemOfficeKey;"
echo ""

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Dash Data Load Complete!"
echo "⏱️  Duration: ${MINUTES}m ${SECONDS}s"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

