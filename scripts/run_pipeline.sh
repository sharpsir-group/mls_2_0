#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# MLS 2.0 Pipeline Runner
# Usage: ./scripts/run_pipeline.sh [bronze|silver|gold|integrity|all]
# Run from: mls_2_0/ directory

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MLS2_ROOT")"

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

export MLS2_ROOT
# Unity Catalog for all Delta tables (isolated namespace; see scripts/sql/init_uc_catalog_mls_2_0.sql)
DATABRICKS_CATALOG="${DATABRICKS_CATALOG:-mls_2_0}"
# Workspace folder for notebooks (match import: MLS_NOTEBOOK_BASE=/mls_etl/notebooks in .env if needed)
MLS_NOTEBOOK_BASE="${MLS_NOTEBOOK_BASE:-/Shared/mls_2_0}"
export DATABRICKS_CATALOG MLS_NOTEBOOK_BASE
echo "📚 UC catalog: $DATABRICKS_CATALOG | Notebook base: $MLS_NOTEBOOK_BASE"

# Suppress CLI warning
export DATABRICKS_CLI_DO_NOT_SHOW_UPGRADE_MESSAGE=1

# Track script start time
SCRIPT_START_TIME=$(date +%s)

# Format duration in human-readable format
format_duration() {
    local seconds=$1
    if [ "$seconds" -lt 60 ]; then
        echo "${seconds}s"
    elif [ "$seconds" -lt 3600 ]; then
        local mins=$((seconds / 60))
        local secs=$((seconds % 60))
        echo "${mins}m ${secs}s"
    else
        local hours=$((seconds / 3600))
        local mins=$(((seconds % 3600) / 60))
        local secs=$((seconds % 60))
        echo "${hours}h ${mins}m ${secs}s"
    fi
}

# Get detailed error from a failed run
get_error_details() {
    local run_id="$1"
    local status_json="$2"
    
    # For multi-task jobs, get the failed task run ID
    local task_run_id=$(echo "$status_json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tasks = d.get('tasks', [])
    for t in tasks:
        state = t.get('state', {}).get('result_state', '')
        if state and state != 'SUCCESS':
            rid = t.get('run_id', '')
            if rid:
                print(rid)
                break
except: pass
" 2>/dev/null)
    
    # Use task run ID if available, otherwise use main run ID
    local target_run_id="${task_run_id:-$run_id}"
    
    # Get full output from runs get-output
    local output_json=$(databricks runs get-output --run-id "$target_run_id" 2>&1 | grep -v "^WARN:")
    
    # Parse and display detailed error info
    echo "$output_json" | python3 -c "
import sys, json, re

try:
    d = json.load(sys.stdin)
    
    # Extract metadata
    meta = d.get('metadata', {})
    task = meta.get('task', {}).get('notebook_task', {})
    
    # Print notebook info
    notebook_path = task.get('notebook_path', 'N/A')
    run_url = meta.get('run_page_url', '')
    
    print(f'Notebook: {notebook_path}')
    if run_url:
        print(f'Run URL:  {run_url}')
    print('')
    
    # Print error
    error = d.get('error', '')
    if error:
        print(f'Error: {error}')
        print('')
    
    # Print stack trace (cleaned up)
    trace = d.get('error_trace', '')
    if trace:
        # Remove ANSI color codes
        trace = re.sub(r'\x1b\[[0-9;]*m', '', trace)
        # Get last N lines of traceback for readability
        lines = [l for l in trace.split('\n') if l.strip()]
        # Show last 15 lines or full trace if shorter
        relevant_lines = lines[-15:] if len(lines) > 15 else lines
        print('Stack Trace:')
        for line in relevant_lines:
            print(f'  {line}')

except Exception as e:
    # If parsing fails, show raw output
    print(f'(Could not parse error: {e})')
" 2>/dev/null
}

run_notebook() {
    local name="$1"
    local path="$2"
    local notebook_type="$3"  # "bronze" (needs API creds), "gold" (needs office key), or "false" (no params)
    local job_start_time=$(date +%s)
    
    echo "🚀 Running: $name"
    
    if [ "$notebook_type" = "true" ] || [ "$notebook_type" = "bronze" ]; then
        # Bronze notebooks: need Qobrix API credentials (SRC_1 = Cyprus)
        local api_user="${SRC_1_API_USER:-$QOBRIX_API_USER}"
        local api_key="${SRC_1_API_KEY:-$QOBRIX_API_KEY}"
        local api_url="${SRC_1_API_URL:-$QOBRIX_API_BASE_URL}"
        local test_limit="${CDC_TEST_LIMIT:-0}"
        local json='{
          "run_name": "'"$name"'",
          "tasks": [{
            "task_key": "task",
            "notebook_task": {
              "notebook_path": "'"$path"'",
              "base_parameters": {
                "QOBRIX_API_USER": "'"$api_user"'",
                "QOBRIX_API_KEY": "'"$api_key"'",
                "QOBRIX_API_BASE_URL": "'"$api_url"'",
                "DATABRICKS_CATALOG": "'"$DATABRICKS_CATALOG"'",
                "CDC_TEST_LIMIT": "'"$test_limit"'"
              }
            }
          }]
        }'
    elif [ "$notebook_type" = "gold" ]; then
        # Gold notebooks: need OriginatingSystemOfficeKey
        # Note: LIST_OFFICE_KEY is read directly by notebooks from env
        local office_key="${SRC_1_OFFICE_KEY:-SHARPSIR-CY-001}"
        local dash_office_key="${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001}"
        local json='{
          "run_name": "'"$name"'",
          "tasks": [{
            "task_key": "task",
            "notebook_task": {
              "notebook_path": "'"$path"'",
              "base_parameters": {
                "QOBRIX_OFFICE_KEY": "'"$office_key"'",
                "DASH_OFFICE_KEY": "'"$dash_office_key"'",
                "DATABRICKS_CATALOG": "'"$DATABRICKS_CATALOG"'"
              }
            }
          }]
        }'
    else
        # Silver/other notebooks: UC catalog only
        local json='{
          "run_name": "'"$name"'",
          "tasks": [{
            "task_key": "task",
            "notebook_task": {
              "notebook_path": "'"$path"'",
              "base_parameters": {
                "DATABRICKS_CATALOG": "'"$DATABRICKS_CATALOG"'"
              }
            }
          }]
        }'
    fi
    
    local result=$(databricks runs submit --json "$json" 2>&1 | grep -v "^WARN:")
    local run_id=$(echo "$result" | grep -o '"run_id":[[:space:]]*[0-9]*' | grep -o '[0-9]*')
    
    if [ -z "$run_id" ]; then
        echo "   ❌ Failed to submit job"
        echo "   $result"
        return 1
    fi
    
    echo "   Run ID: $run_id"
    
    local last_state=""
    while true; do
        local status_json=$(databricks runs get --run-id "$run_id" 2>&1 | grep -v "^WARN:")
        local state=$(echo "$status_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state',d.get('status',{})).get('life_cycle_state','') if isinstance(d.get('state',d.get('status',{})),dict) else '')" 2>/dev/null)
        local result_state=$(echo "$status_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state',d.get('status',{})).get('result_state','') if isinstance(d.get('state',d.get('status',{})),dict) else '')" 2>/dev/null)
        
        # Show state changes
        if [ "$state" != "$last_state" ]; then
            case "$state" in
                PENDING)   echo "   ⏳ Pending..." ;;
                RUNNING)   echo "   ⚙️  Running..." ;;
                TERMINATING) echo "   🔄 Terminating..." ;;
            esac
            last_state="$state"
        fi
        
        if [ "$state" = "TERMINATED" ]; then
            local job_end_time=$(date +%s)
            local job_duration=$((job_end_time - job_start_time))
            local job_duration_fmt=$(format_duration $job_duration)
            
            if [ "$result_state" = "SUCCESS" ]; then
                echo "   ✅ $name completed successfully (${job_duration_fmt})"
                return 0
            else
                echo "   ❌ $name failed: $result_state (${job_duration_fmt})"
                echo ""
                echo "   ┌─────────────────────────────────────────────────────────────────"
                echo "   │ ERROR DETAILS"
                echo "   ├─────────────────────────────────────────────────────────────────"
                # Get and display detailed error
                get_error_details "$run_id" "$status_json" | sed 's/^/   │ /'
                echo "   └─────────────────────────────────────────────────────────────────"
                echo ""
                return 1
            fi
        fi
        sleep 5
    done
}

if [ -z "$1" ]; then
    set -- "--help"
fi

case "$1" in
    # ═══════════════════════════════════════════════════════════════════════════
    # FULL REFRESH COMMANDS (initial load, recovery)
    # ═══════════════════════════════════════════════════════════════════════════
    bronze)
        run_notebook "MLS 2.0 - Qobrix Bronze Full Refresh" "${MLS_NOTEBOOK_BASE}/00_full_refresh_qobrix_bronze" "true"
        ;;
    silver-property)
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "${MLS_NOTEBOOK_BASE}/02_silver_qobrix_property_etl" "false"
        ;;
    silver-agent)
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "${MLS_NOTEBOOK_BASE}/02a_silver_qobrix_agent_etl" "false"
        ;;
    silver-contact)
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "${MLS_NOTEBOOK_BASE}/02b_silver_qobrix_contact_etl" "false"
        ;;
    silver-media)
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "${MLS_NOTEBOOK_BASE}/02c_silver_qobrix_media_etl" "false"
        ;;
    silver-viewing)
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "${MLS_NOTEBOOK_BASE}/02d_silver_qobrix_viewing_etl" "false"
        ;;
    silver|silver-all)
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "${MLS_NOTEBOOK_BASE}/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "${MLS_NOTEBOOK_BASE}/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "${MLS_NOTEBOOK_BASE}/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "${MLS_NOTEBOOK_BASE}/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "${MLS_NOTEBOOK_BASE}/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🎉 All Silver tables created!"
        ;;
    gold-property)
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "${MLS_NOTEBOOK_BASE}/03_gold_reso_property_etl" "gold"
        ;;
    gold-member)
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "${MLS_NOTEBOOK_BASE}/03a_gold_reso_member_etl" "gold"
        ;;
    gold-office)
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "${MLS_NOTEBOOK_BASE}/03b_gold_reso_office_etl" "gold"
        ;;
    gold-media)
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "${MLS_NOTEBOOK_BASE}/03c_gold_reso_media_etl" "gold"
        ;;
    gold-contacts)
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "${MLS_NOTEBOOK_BASE}/03d_gold_reso_contacts_etl" "gold"
        ;;
    gold-showing)
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "${MLS_NOTEBOOK_BASE}/03e_gold_reso_showingappointment_etl" "gold"
        ;;
    gold|gold-all)
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "${MLS_NOTEBOOK_BASE}/03_gold_reso_property_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "${MLS_NOTEBOOK_BASE}/03a_gold_reso_member_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "${MLS_NOTEBOOK_BASE}/03b_gold_reso_office_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "${MLS_NOTEBOOK_BASE}/03c_gold_reso_media_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "${MLS_NOTEBOOK_BASE}/03d_gold_reso_contacts_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "${MLS_NOTEBOOK_BASE}/03e_gold_reso_showingappointment_etl" "gold"
        echo ""
        echo "🎉 All RESO Gold tables created!"
        ;;
    integrity)
        run_notebook "MLS 2.0 - Qobrix vs RESO Integrity Test" "${MLS_NOTEBOOK_BASE}/10_verify_data_integrity_qobrix_vs_reso" "true"
        ;;
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CDC COMMANDS (incremental sync - every 15-30 min)
    # ═══════════════════════════════════════════════════════════════════════════
    cdc-bronze)
        echo "🔄 CDC Mode: Incremental bronze sync"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "${MLS_NOTEBOOK_BASE}/00a_cdc_qobrix_bronze" "true"
        ;;
    cdc-silver)
        echo "🔄 CDC Mode: Incremental silver sync"
        run_notebook "MLS 2.0 - Qobrix CDC Silver Property" "${MLS_NOTEBOOK_BASE}/02_cdc_silver_property_etl" "false"
        ;;
    cdc-gold)
        echo "🔄 CDC Mode: Incremental gold sync"
        run_notebook "MLS 2.0 - RESO CDC Gold Property" "${MLS_NOTEBOOK_BASE}/03_cdc_gold_reso_property_etl" "gold"
        run_notebook "MLS 2.0 - RESO CDC Gold Contacts" "${MLS_NOTEBOOK_BASE}/03d_cdc_gold_reso_contacts_etl" "gold"
        ;;
    cdc-gold-contacts)
        echo "🔄 CDC Mode: Incremental gold contacts sync"
        run_notebook "MLS 2.0 - RESO CDC Gold Contacts" "${MLS_NOTEBOOK_BASE}/03d_cdc_gold_reso_contacts_etl" "gold"
        ;;
    test-cdc)
        echo "🧪 TEST MODE: CDC with ${2:-10} records per entity"
        echo ""
        export CDC_TEST_LIMIT="${2:-10}"
        exec "$0" cdc
        ;;
    cdc-catchup)
        echo "🔄 CDC Catchup: Resetting sync metadata → full re-fetch from API"
        echo ""
        echo "⚠️  This clears CDC metadata so the next bronze run fetches ALL records."
        echo "   Use after: new catalog, missed runs, or data corruption."
        echo ""
        DB_HOST="${DATABRICKS_HOST#https://}"
        echo "🗑️  Clearing cdc_metadata table..."
        curl -s -X POST "https://${DB_HOST}/api/2.0/sql/statements" \
            -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"warehouse_id\": \"${DATABRICKS_WAREHOUSE_ID}\", \"statement\": \"DELETE FROM ${DATABRICKS_CATALOG}.qobrix_bronze.cdc_metadata\", \"wait_timeout\": \"50s\"}" \
            2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
state = d.get('status', {}).get('state', 'UNKNOWN')
if state == 'SUCCEEDED':
    print('   ✅ CDC metadata cleared')
else:
    print(f'   ⚠️  Status: {state}')
    err = d.get('status', {}).get('error', {}).get('message', '')
    if err: print(f'   {err}')
" 2>/dev/null
        echo ""
        echo "🚀 Running full CDC pipeline (will fetch all records from API)..."
        echo ""
        exec "$0" cdc
        ;;
    cdc-all)
        echo "🔄 CDC Mode: Full incremental pipeline (ALL entities - forced)"
        echo ""
        echo "📦 Stage 1: CDC Bronze (incremental data from API)"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "${MLS_NOTEBOOK_BASE}/00a_cdc_qobrix_bronze" "true"
        echo ""
        echo "🔄 Stage 2: Silver (all entities)"
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "${MLS_NOTEBOOK_BASE}/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "${MLS_NOTEBOOK_BASE}/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "${MLS_NOTEBOOK_BASE}/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "${MLS_NOTEBOOK_BASE}/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "${MLS_NOTEBOOK_BASE}/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🏆 Stage 3: Gold (all RESO entities - CDC where available)"
        run_notebook "MLS 2.0 - RESO CDC Gold Property" "${MLS_NOTEBOOK_BASE}/03_cdc_gold_reso_property_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "${MLS_NOTEBOOK_BASE}/03a_gold_reso_member_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "${MLS_NOTEBOOK_BASE}/03b_gold_reso_office_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "${MLS_NOTEBOOK_BASE}/03c_gold_reso_media_etl" "gold"
        run_notebook "MLS 2.0 - RESO CDC Gold Contacts" "${MLS_NOTEBOOK_BASE}/03d_cdc_gold_reso_contacts_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "${MLS_NOTEBOOK_BASE}/03e_gold_reso_showingappointment_etl" "gold"
        echo ""
        echo "📤 Stage 4: Exports"
        run_notebook "MLS 2.0 - Export HomeOverseas XML Feed" "${MLS_NOTEBOOK_BASE}/04a_export_homesoverseas_etl" "false"
        echo ""
        SCRIPT_END_TIME=$(date +%s)
        TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
        echo "🎉 CDC pipeline completed! All entities synced."
        echo ""
        echo "⏱️  Total time: $(format_duration $TOTAL_DURATION)"
        ;;
    cdc)
        echo "🔄 CDC Mode: Smart incremental pipeline (only changed entities)"
        echo ""
        echo "📦 Stage 1: CDC Bronze (incremental data from API)"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "${MLS_NOTEBOOK_BASE}/00a_cdc_qobrix_bronze" "true"
        
        # Show bronze table counts report with MOST RECENT CDC run data
        echo ""
        echo "📊 Current bronze table counts:"
        DB_HOST="${DATABRICKS_HOST#https://}"
        
        # Query for bronze table counts with most recent CDC changes PER ENTITY
        CHANGES_FILE=$(mktemp)
        CDC_PAYLOAD=$(python3 <<PY
import json, os
from pathlib import Path
root = Path(os.environ["MLS2_ROOT"])
uc = os.environ.get("DATABRICKS_CATALOG", "mls_2_0")
sql = (root / "scripts" / "sql" / "cdc_bronze_counts.sql").read_text().replace("__CATALOG__", uc)
print(json.dumps({
    "warehouse_id": os.environ["DATABRICKS_WAREHOUSE_ID"],
    "statement": sql,
    "wait_timeout": "30s",
}))
PY
)
        curl -s -X POST "https://${DB_HOST}/api/2.0/sql/statements" \
            -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "$CDC_PAYLOAD" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    data = d.get('result', {}).get('data_array', [])
    changes = {}
    if data:
        # Print table header
        print('+------------------------------+----------+-----------+')
        print('| table_name                   |total_rows|cdc_changed|')
        print('+------------------------------+----------+-----------+')
        for row in data:
            name = row[0] if row[0] else ''
            total = row[1] if row[1] else '0'
            changed = row[2] if row[2] else '0'
            print(f'| {name:<28} | {total:>8} | {changed:>9} |')
            # Also collect changes for later use
            if name:
                changes[name] = int(changed) if changed and changed != 'NULL' else 0
        print('+------------------------------+----------+-----------+')
    # Output entity=count for parsing
    for e, c in changes.items():
        print(f'CDC:{e}={c}', file=sys.stderr)
except Exception as ex:
    print(f'Error: {ex}', file=sys.stderr)
" 2> "$CHANGES_FILE"
        
        echo ""
        echo "📊 Checking which entities changed..."

        # Parse changes from the CDC output (with default 0 for empty/missing values)
        PROPS_CHANGED=$(grep "^CDC:properties=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        PROPS_CHANGED=${PROPS_CHANGED:-0}
        AGENTS_CHANGED=$(grep "^CDC:agents=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        AGENTS_CHANGED=${AGENTS_CHANGED:-0}
        CONTACTS_CHANGED=$(grep "^CDC:contacts=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        CONTACTS_CHANGED=${CONTACTS_CHANGED:-0}
        VIEWINGS_CHANGED=$(grep "^CDC:property_viewings=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        VIEWINGS_CHANGED=${VIEWINGS_CHANGED:-0}
        OPPS_CHANGED=$(grep "^CDC:opportunities=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        OPPS_CHANGED=${OPPS_CHANGED:-0}
        MEDIA_CHANGED=$(grep "^CDC:property_media=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2)
        MEDIA_CHANGED=${MEDIA_CHANGED:-0}
        rm -f "$CHANGES_FILE"
        
        echo "   Properties: $PROPS_CHANGED changed"
        echo "   Agents: $AGENTS_CHANGED changed"
        echo "   Contacts: $CONTACTS_CHANGED changed"
        echo "   Viewings: $VIEWINGS_CHANGED changed"
        echo "   Opportunities: $OPPS_CHANGED changed"
        echo "   Media: $MEDIA_CHANGED changed"
        
        # Calculate CDC changes (for reporting)
        TOTAL_CHANGES=$((PROPS_CHANGED + AGENTS_CHANGED + CONTACTS_CHANGED + VIEWINGS_CHANGED + OPPS_CHANGED + MEDIA_CHANGED))
        
        # Always run Silver/Gold ETLs to ensure full data consistency
        # Silver ETLs use CREATE OR REPLACE (full refresh) - fast and idempotent
        # This ensures Bronze->Silver->Gold sync even when CDC metadata misses changes
        echo ""
        echo "🔄 Stage 2: Silver (sync Bronze → Silver)"
        
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "${MLS_NOTEBOOK_BASE}/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "${MLS_NOTEBOOK_BASE}/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "${MLS_NOTEBOOK_BASE}/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "${MLS_NOTEBOOK_BASE}/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "${MLS_NOTEBOOK_BASE}/02d_silver_qobrix_viewing_etl" "false"
        
        echo ""
        echo "🏆 Stage 3: Gold (sync Silver → Gold RESO)"
        # Use full refresh ETLs (CREATE OR REPLACE) to avoid schema mismatch issues
        
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "${MLS_NOTEBOOK_BASE}/03_gold_reso_property_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "${MLS_NOTEBOOK_BASE}/03c_gold_reso_media_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "${MLS_NOTEBOOK_BASE}/03a_gold_reso_member_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "${MLS_NOTEBOOK_BASE}/03b_gold_reso_office_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "${MLS_NOTEBOOK_BASE}/03d_gold_reso_contacts_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "${MLS_NOTEBOOK_BASE}/03e_gold_reso_showingappointment_etl" "gold"
        
        echo ""
        echo "📤 Stage 4: Exports"
        run_notebook "MLS 2.0 - Export HomeOverseas XML Feed" "${MLS_NOTEBOOK_BASE}/04a_export_homesoverseas_etl" "false"
        
        SCRIPT_END_TIME=$(date +%s)
        TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
        echo ""
        if [ "$TOTAL_CHANGES" -eq 0 ]; then
            echo "🎉 CDC pipeline completed! (0 API changes, full sync done)"
        else
            echo "🎉 CDC pipeline completed! $TOTAL_CHANGES changes synced."
        fi
        echo ""
        echo "⏱️  Total time: $(format_duration $TOTAL_DURATION)"
        ;;
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORTS (XML feeds for portals)
    # ═══════════════════════════════════════════════════════════════════════════
    export-homesoverseas)
        run_notebook "MLS 2.0 - Export HomeOverseas XML Feed" "${MLS_NOTEBOOK_BASE}/04a_export_homesoverseas_etl" "false"
        ;;
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FULL PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════
    all)
        echo "📦 Stage 1: Bronze (raw data ingestion)"
        run_notebook "MLS 2.0 - Qobrix Bronze Full Refresh" "${MLS_NOTEBOOK_BASE}/00_full_refresh_qobrix_bronze" "true"
        echo ""
        echo "🔄 Stage 2: Silver (normalized data)"
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "${MLS_NOTEBOOK_BASE}/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "${MLS_NOTEBOOK_BASE}/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "${MLS_NOTEBOOK_BASE}/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "${MLS_NOTEBOOK_BASE}/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "${MLS_NOTEBOOK_BASE}/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🏆 Stage 3: Gold (RESO-compliant)"
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "${MLS_NOTEBOOK_BASE}/03_gold_reso_property_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "${MLS_NOTEBOOK_BASE}/03a_gold_reso_member_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "${MLS_NOTEBOOK_BASE}/03b_gold_reso_office_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "${MLS_NOTEBOOK_BASE}/03c_gold_reso_media_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "${MLS_NOTEBOOK_BASE}/03d_gold_reso_contacts_etl" "gold"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "${MLS_NOTEBOOK_BASE}/03e_gold_reso_showingappointment_etl" "gold"
        echo ""
        echo "📤 Stage 4: Exports"
        run_notebook "MLS 2.0 - Export HomeOverseas XML Feed" "${MLS_NOTEBOOK_BASE}/04a_export_homesoverseas_etl" "false"
        echo ""
        echo "✅ Stage 5: Integrity verification"
        run_notebook "MLS 2.0 - Qobrix vs RESO Integrity Test" "${MLS_NOTEBOOK_BASE}/10_verify_data_integrity_qobrix_vs_reso" "true"
        echo ""
        SCRIPT_END_TIME=$(date +%s)
        TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
        echo "🎉 Full pipeline completed!"
        echo ""
        echo "⏱️  Total time: $(format_duration $TOTAL_DURATION)"
        ;;
    --help|-h|*)
        echo "Usage: $0 <STAGE>"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "FULL REFRESH (initial load, recovery, weekly)"
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "  bronze              Raw data ingestion from Qobrix API"
        echo "  silver|silver-all   All silver transformations"
        echo "  silver-property     Silver property only"
        echo "  silver-agent        Silver agent only"
        echo "  silver-contact      Silver contact only"
        echo "  silver-media        Silver media only"
        echo "  silver-viewing      Silver viewing only"
        echo "  gold|gold-all       All RESO gold tables"
        echo "  gold-property       RESO Property only"
        echo "  gold-member         RESO Member only"
        echo "  gold-office         RESO Office only"
        echo "  gold-media          RESO Media only"
        echo "  gold-contacts       RESO Contacts only"
        echo "  gold-showing        RESO ShowingAppointment only"
        echo "  integrity           Data integrity verification"
        echo "  all                 Full pipeline (bronze → silver → gold → integrity)"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "EXPORTS (XML feeds for portals)"
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "  export-homesoverseas  HomeOverseas.ru XML feed (with RU translations)"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "CDC - INCREMENTAL SYNC (recommended for regular updates)"
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "  cdc                 Smart CDC - only run Silver/Gold for changed entities"
        echo "  test-cdc [N]        Test CDC with N records per entity (default: 10)"
        echo "  cdc-catchup         Reset CDC metadata + full re-fetch (recovery after outage)"
        echo "  cdc-all             Force CDC ALL entities (bronze -> silver -> gold)"
        echo "  cdc-bronze          CDC bronze only (fetch changed records from API)"
        echo "  cdc-silver          CDC silver property only (incremental transform)"
        echo "  cdc-gold            CDC gold (property + contacts) incremental RESO transform"
        echo "  cdc-gold-contacts   CDC gold contacts only (incremental RESO transform)"
        exit 1
        ;;
esac

