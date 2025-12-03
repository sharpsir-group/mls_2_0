#!/bin/bash
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

# Get error message from a failed run
get_error_message() {
    local run_id="$1"
    local status_json="$2"
    
    # Try to get task run IDs (multi-task jobs)
    local task_run_ids=$(echo "$status_json" | python3 -c "
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
except Exception as e:
    pass
" 2>/dev/null)
    
    if [ -n "$task_run_ids" ]; then
        # Get error from task run using runs get-output
        local output_json=$(databricks runs get-output --run-id "$task_run_ids" 2>&1 | grep -v "^WARN:")
        local error=$(echo "$output_json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    err = d.get('error', '')
    trace = d.get('error_trace', '')
    if err:
        # Show error message
        msg = err
        # Extract key part of traceback if available
        if trace:
            # Get last meaningful line from traceback
            lines = [l.strip() for l in trace.split('\n') if l.strip() and not l.startswith('[0;')]
            if lines:
                last_line = lines[-1] if len(lines[-1]) < 200 else lines[-1][:200] + '...'
                msg = err + '\n' + last_line
        print(msg[:800])
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null)
        if [ -n "$error" ]; then
            echo "$error"
            return
        fi
    fi
    
    # Fallback: get state_message from parent run
    local state_msg=$(echo "$status_json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    msg = d.get('state', {}).get('state_message', '')
    print(msg[:500] if msg else '')
except: pass
" 2>/dev/null)
    
    if [ -n "$state_msg" ]; then
        echo "$state_msg"
    fi
}

run_notebook() {
    local name="$1"
    local path="$2"
    local needs_creds="$3"
    
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
            if [ "$result_state" = "SUCCESS" ]; then
                echo "   ✅ $name completed successfully"
                return 0
            else
                echo "   ❌ $name failed: $result_state"
                
                # Get and display error message
                local error_msg=$(get_error_message "$run_id" "$status_json")
                if [ -n "$error_msg" ]; then
                    echo ""
                    echo "   ┌─ Error Details ─────────────────────────────────────────"
                    echo "$error_msg" | sed 's/^/   │ /'
                    echo "   └──────────────────────────────────────────────────────────"
                    echo ""
                fi
                return 1
            fi
        fi
        sleep 5
    done
}

case "${1:-all}" in
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
    cdc)
        echo "🔄 CDC Mode: Full incremental pipeline"
        echo ""
        echo "📦 Stage 1: CDC Bronze (incremental data from API)"
        run_notebook "MLS 2.0 - Qobrix CDC Bronze" "/Shared/mls_2_0/00a_cdc_qobrix_bronze" "true"
        echo ""
        echo "🔄 Stage 2: CDC Silver (incremental transform)"
        run_notebook "MLS 2.0 - Qobrix CDC Silver Property" "/Shared/mls_2_0/02_cdc_silver_property_etl" "false"
        echo ""
        echo "🏆 Stage 3: CDC Gold (incremental RESO transform)"
        run_notebook "MLS 2.0 - RESO CDC Gold Property" "/Shared/mls_2_0/03_cdc_gold_reso_property_etl" "false"
        echo ""
        echo "🎉 CDC pipeline completed!"
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
        echo "🎉 Full pipeline completed!"
        ;;
    *)
        echo "Usage: $0 [STAGE]"
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
        echo "CDC - INCREMENTAL SYNC (every 15-30 min)"
        echo "═══════════════════════════════════════════════════════════════════════"
        echo "  cdc                 Full CDC pipeline (bronze → silver → gold)"
        echo "  cdc-bronze          CDC bronze only (fetch changed records from API)"
        echo "  cdc-silver          CDC silver only (transform changed records)"
        echo "  cdc-gold            CDC gold only (RESO transform changed records)"
        exit 1
        ;;
esac

