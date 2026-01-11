#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# Dash Data Loader Orchestration Script
# Usage: ./scripts/load_dash_data.sh <json_file_path> [--country CODE]
# Example: ./scripts/load_dash_data.sh tmp/dash_listings_hungary.json --country HU

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
JSON_FILE="$1"
COUNTRY_ARG=""
if [ "$2" = "--country" ] && [ -n "$3" ]; then
    COUNTRY_ARG="--country $3"
fi

if [ -z "$JSON_FILE" ]; then
    echo "❌ Error: JSON file path required"
    echo "Usage: $0 <json_file_path> [--country CODE]"
    echo "Example: $0 tmp/dash_listings_hungary.json --country HU"
    exit 1
fi

# Resolve absolute path
if [[ "$JSON_FILE" != /* ]]; then
    JSON_FILE="$MLS2_ROOT/$JSON_FILE"
fi

if [ ! -f "$JSON_FILE" ]; then
    echo "❌ Error: File not found: $JSON_FILE"
    exit 1
fi

echo "=" | tr -d '\n' | head -c 80
echo ""
echo "DASH DATA LOADER"
echo "=" | tr -d '\n' | head -c 80
echo ""
echo "📁 JSON File: $JSON_FILE"
if [ -n "$COUNTRY_ARG" ]; then
    echo "🌍 Country: $3"
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
    
    local run_output=$(databricks jobs run-now \
        --job-id "$(databricks jobs list --output json | python3 -c "
import sys, json
for job in json.load(sys.stdin):
    if job.get('settings', {}).get('name', '') == 'MLS 2.0 - Manual Run':
        print(job['job_id'])
        break
" 2>/dev/null || echo "")" \
        --notebook-task "{\"notebook_path\": \"$notebook_path\"}" \
        2>&1 | grep -v "^WARN:" || true)
    
    if echo "$run_output" | grep -q "run_id"; then
        local run_id=$(echo "$run_output" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null || echo "")
        echo "   ✅ Started (Run ID: $run_id)"
        
        # Wait for completion (simplified - in production use proper polling)
        sleep 5
    else
        echo "   ⚠️  Could not start notebook (may need manual run)"
        echo "   Run manually: databricks workspace import $notebook_path"
    fi
}

# Step 1: Load Bronze data
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Load Dash Bronze Data"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$MLS2_ROOT"
python3 scripts/load_dash_bronze.py "$JSON_FILE" $COUNTRY_ARG

if [ $? -ne 0 ]; then
    echo "❌ Failed to load bronze data"
    exit 1
fi

echo ""

# Step 2: Run Silver ETLs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Run Dash Silver ETLs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Import notebooks if needed
echo "📤 Importing Dash Silver notebooks to Databricks..."
databricks workspace import notebooks/01_dash_silver_property_etl.py "/Shared/mls_2_0/01_dash_silver_property_etl" --language PYTHON --overwrite 2>&1 | grep -v "^WARN:" || true
databricks workspace import notebooks/01_dash_silver_media_etl.py "/Shared/mls_2_0/01_dash_silver_media_etl" --language PYTHON --overwrite 2>&1 | grep -v "^WARN:" || true

# Run Silver Property ETL
run_notebook "Dash Silver Property ETL" "/Shared/mls_2_0/01_dash_silver_property_etl" 300

# Run Silver Media ETL
run_notebook "Dash Silver Media ETL" "/Shared/mls_2_0/01_dash_silver_media_etl" 300

echo ""

# Step 3: Run Gold ETLs (updated to include Dash)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Run RESO Gold ETLs (includes Dash data)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Import updated Gold notebooks
echo "📤 Importing updated Gold notebooks to Databricks..."
databricks workspace import notebooks/03_gold_reso_property_etl.py "/Shared/mls_2_0/03_gold_reso_property_etl" --language PYTHON --overwrite 2>&1 | grep -v "^WARN:" || true
databricks workspace import notebooks/03c_gold_reso_media_etl.py "/Shared/mls_2_0/03c_gold_reso_media_etl" --language PYTHON --overwrite 2>&1 | grep -v "^WARN:" || true

# Run Gold Property ETL
run_notebook "RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" 600

# Run Gold Media ETL
run_notebook "RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" 300

echo ""

# Step 4: Verification
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📊 Verifying data in RESO Gold..."
echo ""
echo "Run this query in Databricks to verify:"
echo ""
echo "SELECT Country, X_DataSource, COUNT(*) as count"
echo "FROM mls2.reso_gold.property"
echo "GROUP BY Country, X_DataSource"
echo "ORDER BY Country, X_DataSource;"
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

