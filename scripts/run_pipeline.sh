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
    local needs_creds="$3"
    local job_start_time=$(date +%s)
    
    echo "🚀 Running: $name"
    
    if [ "$needs_creds" = "true" ]; then
        local json='{
          "run_name": "'"$name"'",
          "tasks": [{
            "task_key": "task",
            "notebook_task": {
              "notebook_path": "'"$path"'",
              "base_parameters": {
                "QOBRIX_API_USER": "'"$QOBRIX_API_USER"'",
                "QOBRIX_API_KEY": "'"$QOBRIX_API_KEY"'",
                "QOBRIX_API_BASE_URL": "'"$QOBRIX_API_BASE_URL"'"
              }
            }
          }]
        }'
    else
        local json='{
          "run_name": "'"$name"'",
          "tasks": [{
            "task_key": "task",
            "notebook_task": {
              "notebook_path": "'"$path"'"
            }
          }]
        }'
    fi
    
    local result=$(databricks runs submit --json "$json" 2>&1 | grep -v "^WARN:")
    local run_id=$(echo "$result" | grep -o '"run_id": [0-9]*' | grep -o '[0-9]*')
    
    if [ -z "$run_id" ]; then
        echo "   ❌ Failed to submit job"
        echo "   $result"
        return 1
    fi
    
    echo "   Run ID: $run_id"
    
    local last_state=""
    while true; do
        local status_json=$(databricks runs get --run-id "$run_id" 2>&1 | grep -v "^WARN:")
        local state=$(echo "$status_json" | grep -o '"life_cycle_state": "[^"]*"' | head -1 | cut -d'"' -f4)
        local result_state=$(echo "$status_json" | grep -o '"result_state": "[^"]*"' | head -1 | cut -d'"' -f4)
        
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
        run_notebook "MLS 2.0 - Qobrix Bronze Full Refresh" "/Shared/mls_2_0/00_full_refresh_qobrix_bronze" "true"
        ;;
    silver-property)
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "/Shared/mls_2_0/02_silver_qobrix_property_etl" "false"
        ;;
    silver-agent)
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "/Shared/mls_2_0/02a_silver_qobrix_agent_etl" "false"
        ;;
    silver-contact)
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "/Shared/mls_2_0/02b_silver_qobrix_contact_etl" "false"
        ;;
    silver-media)
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "/Shared/mls_2_0/02c_silver_qobrix_media_etl" "false"
        ;;
    silver-viewing)
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "/Shared/mls_2_0/02d_silver_qobrix_viewing_etl" "false"
        ;;
    silver|silver-all)
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "/Shared/mls_2_0/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "/Shared/mls_2_0/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "/Shared/mls_2_0/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "/Shared/mls_2_0/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "/Shared/mls_2_0/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🎉 All Silver tables created!"
        ;;
    gold-property)
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" "false"
        ;;
    gold-member)
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "/Shared/mls_2_0/03a_gold_reso_member_etl" "false"
        ;;
    gold-office)
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "/Shared/mls_2_0/03b_gold_reso_office_etl" "false"
        ;;
    gold-media)
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" "false"
        ;;
    gold-contacts)
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "/Shared/mls_2_0/03d_gold_reso_contacts_etl" "false"
        ;;
    gold-showing)
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "/Shared/mls_2_0/03e_gold_reso_showingappointment_etl" "false"
        ;;
    gold|gold-all)
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "/Shared/mls_2_0/03a_gold_reso_member_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "/Shared/mls_2_0/03b_gold_reso_office_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "/Shared/mls_2_0/03d_gold_reso_contacts_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "/Shared/mls_2_0/03e_gold_reso_showingappointment_etl" "false"
        echo ""
        echo "🎉 All RESO Gold tables created!"
        ;;
    integrity)
        run_notebook "MLS 2.0 - Qobrix vs RESO Integrity Test" "/Shared/mls_2_0/10_verify_data_integrity_qobrix_vs_reso" "true"
        ;;
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CDC COMMANDS (incremental sync - every 15-30 min)
    # ═══════════════════════════════════════════════════════════════════════════
    cdc-bronze)
        echo "🔄 CDC Mode: Incremental bronze sync"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "/Shared/mls_2_0/00a_cdc_qobrix_bronze" "true"
        ;;
    cdc-silver)
        echo "🔄 CDC Mode: Incremental silver sync"
        run_notebook "MLS 2.0 - Qobrix CDC Silver Property" "/Shared/mls_2_0/02_cdc_silver_property_etl" "false"
        ;;
    cdc-gold)
        echo "🔄 CDC Mode: Incremental gold sync"
        run_notebook "MLS 2.0 - RESO CDC Gold Property" "/Shared/mls_2_0/03_cdc_gold_reso_property_etl" "false"
        ;;
    cdc-all)
        echo "🔄 CDC Mode: Full incremental pipeline (ALL entities - forced)"
        echo ""
        echo "📦 Stage 1: CDC Bronze (incremental data from API)"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "/Shared/mls_2_0/00a_cdc_qobrix_bronze" "true"
        echo ""
        echo "🔄 Stage 2: Silver (all entities)"
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "/Shared/mls_2_0/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "/Shared/mls_2_0/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "/Shared/mls_2_0/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "/Shared/mls_2_0/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "/Shared/mls_2_0/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🏆 Stage 3: Gold (all RESO entities)"
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "/Shared/mls_2_0/03a_gold_reso_member_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "/Shared/mls_2_0/03b_gold_reso_office_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "/Shared/mls_2_0/03d_gold_reso_contacts_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "/Shared/mls_2_0/03e_gold_reso_showingappointment_etl" "false"
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
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "/Shared/mls_2_0/00a_cdc_qobrix_bronze" "true"
        
        # Get CDC changes from notebook output
        echo ""
        echo "📊 Checking which entities changed..."
        
        # Query cdc_metadata table to get recent changes
        CDC_QUERY='SELECT entity_name, SUM(records_processed) as total FROM mls2.qobrix_bronze.cdc_metadata WHERE sync_completed_at >= CURRENT_TIMESTAMP() - INTERVAL 5 MINUTES GROUP BY entity_name'
        CDC_RESULT=$(databricks jobs run-now --job-id 0 2>/dev/null || echo "")
        
        # For now, check the cdc_metadata table via SQL API
        # Parse changes from a temp file approach
        CHANGES_FILE=$(mktemp)
        # Remove https:// if already present in DATABRICKS_HOST
        DB_HOST="${DATABRICKS_HOST#https://}"
        curl -s -X POST "https://${DB_HOST}/api/2.0/sql/statements" \
            -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{
                "warehouse_id": "'"${DATABRICKS_WAREHOUSE_ID}"'",
                "statement": "SELECT entity_name, records_processed FROM mls2.qobrix_bronze.cdc_metadata WHERE sync_completed_at >= CURRENT_TIMESTAMP() - INTERVAL 2 MINUTES ORDER BY sync_completed_at DESC",
                "wait_timeout": "30s"
            }' 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    data = d.get('result', {}).get('data_array', [])
    changes = {}
    for row in data:
        entity = row[0]
        count = int(row[1]) if row[1] else 0
        if entity not in changes:
            changes[entity] = count
    # Output entity=count format
    for e, c in changes.items():
        print(f'{e}={c}')
except Exception as ex:
    print(f'error={ex}', file=sys.stderr)
" > "$CHANGES_FILE" 2>/dev/null

        # Parse changes
        PROPS_CHANGED=$(grep "^properties=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2 || echo "0")
        AGENTS_CHANGED=$(grep "^agents=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2 || echo "0")
        CONTACTS_CHANGED=$(grep "^contacts=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2 || echo "0")
        VIEWINGS_CHANGED=$(grep "^property_viewings=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2 || echo "0")
        OPPS_CHANGED=$(grep "^opportunities=" "$CHANGES_FILE" 2>/dev/null | cut -d= -f2 || echo "0")
        rm -f "$CHANGES_FILE"
        
        echo "   Properties: $PROPS_CHANGED changed"
        echo "   Agents: $AGENTS_CHANGED changed"
        echo "   Contacts: $CONTACTS_CHANGED changed"
        echo "   Viewings: $VIEWINGS_CHANGED changed"
        echo "   Opportunities: $OPPS_CHANGED changed"
        
        # Calculate if anything changed
        TOTAL_CHANGES=$((PROPS_CHANGED + AGENTS_CHANGED + CONTACTS_CHANGED + VIEWINGS_CHANGED + OPPS_CHANGED))
        
        if [ "$TOTAL_CHANGES" -eq 0 ]; then
            echo ""
            echo "✨ No changes detected - skipping Silver/Gold ETLs"
            SCRIPT_END_TIME=$(date +%s)
            TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
            echo ""
            echo "🎉 CDC pipeline completed! (no updates needed)"
            echo ""
            echo "⏱️  Total time: $(format_duration $TOTAL_DURATION)"
        else
            echo ""
            echo "🔄 Stage 2: Silver (changed entities only)"
            
            if [ "$PROPS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "/Shared/mls_2_0/02_silver_qobrix_property_etl" "false"
                run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "/Shared/mls_2_0/02c_silver_qobrix_media_etl" "false"
            fi
            if [ "$AGENTS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "/Shared/mls_2_0/02a_silver_qobrix_agent_etl" "false"
            fi
            if [ "$CONTACTS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "/Shared/mls_2_0/02b_silver_qobrix_contact_etl" "false"
            fi
            if [ "$VIEWINGS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "/Shared/mls_2_0/02d_silver_qobrix_viewing_etl" "false"
            fi
            
            echo ""
            echo "🏆 Stage 3: Gold (changed entities only)"
            
            if [ "$PROPS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" "false"
                run_notebook "MLS 2.0 - RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" "false"
            fi
            if [ "$AGENTS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - RESO Gold Member ETL" "/Shared/mls_2_0/03a_gold_reso_member_etl" "false"
                run_notebook "MLS 2.0 - RESO Gold Office ETL" "/Shared/mls_2_0/03b_gold_reso_office_etl" "false"
            fi
            if [ "$CONTACTS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "/Shared/mls_2_0/03d_gold_reso_contacts_etl" "false"
            fi
            if [ "$VIEWINGS_CHANGED" -gt 0 ]; then
                run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "/Shared/mls_2_0/03e_gold_reso_showingappointment_etl" "false"
            fi
            
            SCRIPT_END_TIME=$(date +%s)
            TOTAL_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
            echo ""
            echo "🎉 CDC pipeline completed! Changed entities synced."
            echo ""
            echo "⏱️  Total time: $(format_duration $TOTAL_DURATION)"
        fi
        ;;
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FULL PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════
    all)
        echo "📦 Stage 1: Bronze (raw data ingestion)"
        run_notebook "MLS 2.0 - Qobrix Bronze Full Refresh" "/Shared/mls_2_0/00_full_refresh_qobrix_bronze" "true"
        echo ""
        echo "🔄 Stage 2: Silver (normalized data)"
        run_notebook "MLS 2.0 - Qobrix Silver Property ETL" "/Shared/mls_2_0/02_silver_qobrix_property_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Agent ETL" "/Shared/mls_2_0/02a_silver_qobrix_agent_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Contact ETL" "/Shared/mls_2_0/02b_silver_qobrix_contact_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Media ETL" "/Shared/mls_2_0/02c_silver_qobrix_media_etl" "false"
        run_notebook "MLS 2.0 - Qobrix Silver Viewing ETL" "/Shared/mls_2_0/02d_silver_qobrix_viewing_etl" "false"
        echo ""
        echo "🏆 Stage 3: Gold (RESO-compliant)"
        run_notebook "MLS 2.0 - RESO Gold Property ETL" "/Shared/mls_2_0/03_gold_reso_property_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Member ETL" "/Shared/mls_2_0/03a_gold_reso_member_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Office ETL" "/Shared/mls_2_0/03b_gold_reso_office_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Media ETL" "/Shared/mls_2_0/03c_gold_reso_media_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold Contacts ETL" "/Shared/mls_2_0/03d_gold_reso_contacts_etl" "false"
        run_notebook "MLS 2.0 - RESO Gold ShowingAppointment ETL" "/Shared/mls_2_0/03e_gold_reso_showingappointment_etl" "false"
        echo ""
        echo "✅ Stage 4: Integrity verification"
        run_notebook "MLS 2.0 - Qobrix vs RESO Integrity Test" "/Shared/mls_2_0/10_verify_data_integrity_qobrix_vs_reso" "true"
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
        echo "CDC - INCREMENTAL SYNC (recommended for regular updates)"
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "  cdc                 Smart CDC - only run Silver/Gold for changed entities"
        echo "  cdc-all             Force CDC ALL entities (bronze -> silver -> gold)"
        echo "  cdc-bronze          CDC bronze only (fetch changed records from API)"
        echo "  cdc-silver          CDC silver property only (incremental transform)"
        echo "  cdc-gold            CDC gold property only (incremental RESO transform)"
        exit 1
        ;;
esac

