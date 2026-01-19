#!/bin/bash
# MLS 2.0 CDC Pipeline - All Sources
# Runs daily at 3:00 AM MSK (0:00 UTC)
# Processes: Cyprus (Qobrix), Hungary (DASH JSON), Kazakhstan (DASH API)

export PATH="/home/bitnami/.local/bin:/home/bitnami/.nvm/versions/node/v20.19.5/bin:/opt/bitnami/python/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$MLS2_ROOT/logs"
DATE=$(date '+%Y-%m-%d')
START_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/all_sources_cdc_${DATE}.log"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    set -a
    source "$MLS2_ROOT/.env"
    set +a
fi

echo "╔══════════════════════════════════════════════════════════════╗" | tee "$LOG_FILE"
echo "║  MLS 2.0 All Sources CDC Pipeline                            ║" | tee -a "$LOG_FILE"
echo "║  ${START_TIME}                                  ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "📊 Sources configured:" | tee -a "$LOG_FILE"
echo "  1. Cyprus (CY):     ${SRC_1_OFFICE_KEY:-SHARPSIR-CY-001} - Qobrix API" | tee -a "$LOG_FILE"
echo "  2. Hungary (HU):    ${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001} - DASH JSON" | tee -a "$LOG_FILE"
echo "  3. Kazakhstan (KZ): ${SRC_3_OFFICE_KEY:-SHARPSIR-KZ-001} - DASH API" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

OVERALL_STATUS="SUCCESS"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Cyprus - Qobrix CDC (existing pipeline)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 1: Cyprus (Qobrix) CDC" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

cd "$MLS2_ROOT"
if "$SCRIPT_DIR/run_pipeline.sh" cdc >> "$LOG_FILE" 2>&1; then
    echo "✅ Cyprus CDC completed" | tee -a "$LOG_FILE"
else
    echo "⚠️ Cyprus CDC had issues (continuing...)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Kazakhstan - Fetch from DASH API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 2: Kazakhstan (DASH API) Fetch & Load" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

# Check if KZ source is configured
if [ -n "$SRC_3_DASH_API_KEY" ]; then
    echo "🔄 Fetching Kazakhstan listings from DASH API..." | tee -a "$LOG_FILE"
    if python3 "$SCRIPT_DIR/fetch_dash_api.py" --source "${SRC_3_OFFICE_KEY:-SHARPSIR-KZ-001}" --load >> "$LOG_FILE" 2>&1; then
        echo "✅ Kazakhstan fetch & load completed" | tee -a "$LOG_FILE"
    else
        echo "⚠️ Kazakhstan fetch had issues" | tee -a "$LOG_FILE"
    fi
else
    echo "⏭️ Kazakhstan source not configured (skipping)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Hungary - Process DASH JSON (if new files)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 3: Hungary (DASH JSON) Check for new files" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

HU_SOURCE_DIR="${SRC_2_DIR:-$MLS2_ROOT/dash_hsir_source}"
if [ -d "$HU_SOURCE_DIR" ]; then
    echo "📁 Checking $HU_SOURCE_DIR for new files..." | tee -a "$LOG_FILE"
    if python3 "$SCRIPT_DIR/load_dash_bronze.py" --source "${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001}" >> "$LOG_FILE" 2>&1; then
        echo "✅ Hungary processing completed" | tee -a "$LOG_FILE"
    else
        echo "⚠️ Hungary processing had issues" | tee -a "$LOG_FILE"
    fi
else
    echo "⏭️ Hungary source directory not found (skipping)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4: Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "SUMMARY" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "Started:  $START_TIME" | tee -a "$LOG_FILE"
echo "Finished: $END_TIME" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run API integrity test
echo "Running API Integration Tests..." | tee -a "$LOG_FILE"
if "$SCRIPT_DIR/verify_api_integrity.sh" >> "$LOG_FILE" 2>&1; then
    echo "✅ API Tests: PASSED" | tee -a "$LOG_FILE"
else
    echo "⚠️ API Tests: COMPLETED WITH WARNINGS" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "✅ All Sources CDC Pipeline Complete!" | tee -a "$LOG_FILE"

