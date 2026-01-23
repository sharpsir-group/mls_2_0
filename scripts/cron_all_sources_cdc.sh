#!/bin/bash
# MLS 2.0 CDC Pipeline - All Sources
# Runs daily at 3:00 AM MSK (0:00 UTC)
# Processes: Cyprus (Qobrix API), Hungary (DASH FILE), Kazakhstan (DASH API)
# Sends HTML email report on completion

export PATH="/home/bitnami/.local/bin:/home/bitnami/.nvm/versions/node/v20.19.5/bin:/opt/bitnami/python/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$MLS2_ROOT/logs"
DATE=$(date '+%Y-%m-%d')
START_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
START_SECONDS=$(date +%s)
HOSTNAME=$(hostname)

# Email configuration
EMAIL_TO="sseregin@sharp-sothebys-realty.com"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/all_sources_cdc_${DATE}.log"
API_TEST_LOG="$LOG_DIR/api_test_${DATE}.log"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    set -a
    source "$MLS2_ROOT/.env"
    set +a
fi

# Source status tracking
CY_STATUS="PENDING"
HU_STATUS="PENDING"
KZ_STATUS="PENDING"
CY_CHANGES="0"
HU_RECORDS="0"
KZ_RECORDS="0"

# API Test results
API_TEST_STATUS="SKIPPED"
API_PROP_COUNT="--"
API_PROP_DATA="--"
API_MEDIA="--"
API_MEMBERS="--"
API_CONTACTS="--"
API_TRANSFORM="--"
API_TYPES="--"
API_URLS="--"

# Function to format duration
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
        echo "${hours}h ${mins}m"
    fi
}

# Function to extract API test results
extract_api_results() {
    local log="$1"
    
    if [ ! -f "$log" ]; then
        return
    fi
    
    API_PROP_COUNT=$(grep "Property Count:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_PROP_DATA=$(grep "Property Data:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_MEDIA=$(grep "Media Count:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_MEMBERS=$(grep -E "RESO Member:" "$log" 2>/dev/null | head -1 | grep -q "✅" && echo "PASS" || echo "WARN")
    API_CONTACTS=$(grep "Contact Count:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_TRANSFORM=$(grep "Field Transformations:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_TYPES=$(grep "RESO Type Compliance:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_URLS=$(grep "Media URL Full Path:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    
    # Set defaults
    API_PROP_COUNT=${API_PROP_COUNT:-"--"}
    API_PROP_DATA=${API_PROP_DATA:-"--"}
    API_MEDIA=${API_MEDIA:-"--"}
    API_MEMBERS=${API_MEMBERS:-"--"}
    API_CONTACTS=${API_CONTACTS:-"--"}
    API_TRANSFORM=${API_TRANSFORM:-"--"}
    API_TYPES=${API_TYPES:-"--"}
    API_URLS=${API_URLS:-"--"}
    
    if grep -q "ALL INTEGRITY TESTS PASSED" "$log" 2>/dev/null; then
        API_TEST_STATUS="PASS"
    elif grep -q "issues found" "$log" 2>/dev/null; then
        API_TEST_STATUS="WARN"
    else
        API_TEST_STATUS="FAIL"
    fi
}

# Function to get status HTML
get_status_html() {
    local status="$1"
    case "$status" in
        PASS|SUCCESS|✅)
            echo '<span style="color: #10b981; font-weight: 600;">✓ PASS</span>'
            ;;
        FAIL|FAILED|❌)
            echo '<span style="color: #ef4444; font-weight: 600;">✗ FAIL</span>'
            ;;
        WARN|WARNING|⚠️)
            echo '<span style="color: #f59e0b; font-weight: 600;">⚠ WARN</span>'
            ;;
        SKIP|SKIPPED|⏭️)
            echo '<span style="color: #888;">⏭ SKIP</span>'
            ;;
        *)
            echo '<span style="color: #888;">--</span>'
            ;;
    esac
}

# Function to get source status icon
get_source_status() {
    local status="$1"
    case "$status" in
        SUCCESS) echo "✅" ;;
        FAILED) echo "❌" ;;
        SKIPPED) echo "⏭️" ;;
        *) echo "⏳" ;;
    esac
}

# Function to send HTML email report
send_email_report() {
    local overall_status="$1"
    local status_color="#10b981"
    local status_bg="#ecfdf5"
    local status_icon="&#10003;"
    
    if [ "$overall_status" = "FAILED" ]; then
        status_color="#ef4444"
        status_bg="#fef2f2"
        status_icon="&#10007;"
    elif [ "$overall_status" = "WARNING" ]; then
        status_color="#f59e0b"
        status_bg="#fffbeb"
        status_icon="&#9888;"
    fi
    
    local subject="[MLS 2.0] All Sources CDC ${overall_status} - ${DATE}"
    
    # Calculate duration
    END_SECONDS=$(date +%s)
    DURATION=$((END_SECONDS - START_SECONDS))
    DURATION_FMT=$(format_duration $DURATION)
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
    
    # Extract API test results
    extract_api_results "$API_TEST_LOG"
    
    # Get status HTML for API tests
    API_PROP_COUNT_HTML=$(get_status_html "$API_PROP_COUNT")
    API_PROP_DATA_HTML=$(get_status_html "$API_PROP_DATA")
    API_MEDIA_HTML=$(get_status_html "$API_MEDIA")
    API_MEMBERS_HTML=$(get_status_html "$API_MEMBERS")
    API_CONTACTS_HTML=$(get_status_html "$API_CONTACTS")
    API_TRANSFORM_HTML=$(get_status_html "$API_TRANSFORM")
    API_TYPES_HTML=$(get_status_html "$API_TYPES")
    API_URLS_HTML=$(get_status_html "$API_URLS")
    
    # API test overall status styling
    local api_status_color="#10b981"
    local api_status_bg="#ecfdf5"
    if [ "$API_TEST_STATUS" = "FAIL" ]; then
        api_status_color="#ef4444"
        api_status_bg="#fef2f2"
    elif [ "$API_TEST_STATUS" = "WARN" ]; then
        api_status_color="#f59e0b"
        api_status_bg="#fffbeb"
    elif [ "$API_TEST_STATUS" = "SKIPPED" ]; then
        api_status_color="#888"
        api_status_bg="#f5f5f5"
    fi
    
    # Source status colors
    CY_COLOR=$( [ "$CY_STATUS" = "SUCCESS" ] && echo "#10b981" || echo "#ef4444" )
    HU_COLOR=$( [ "$HU_STATUS" = "SUCCESS" ] && echo "#10b981" || ( [ "$HU_STATUS" = "SKIPPED" ] && echo "#888" || echo "#ef4444" ) )
    KZ_COLOR=$( [ "$KZ_STATUS" = "SUCCESS" ] && echo "#10b981" || ( [ "$KZ_STATUS" = "SKIPPED" ] && echo "#888" || echo "#ef4444" ) )
    
    # System IDs
    CY_SYSTEM_ID="${SRC_1_SYSTEM_ID:-QOBRIX_CY}"
    HU_SYSTEM_ID="${SRC_2_SYSTEM_ID:-DASH_HU}"
    KZ_SYSTEM_ID="${SRC_3_SYSTEM_ID:-DASH_KZ_SANDBOX}"
    
    # Escape log content for HTML (last 200 lines)
    LOG_CONTENT=$(tail -200 "$LOG_FILE" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')
    
    # Build HTML email
    cat << EOF | mail -a "Content-Type: text/html; charset=UTF-8" -s "$subject" "$EMAIL_TO"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px 40px; text-align: center; border-bottom: 1px solid #e5e5e5;">
                            <h1 style="margin: 0; font-size: 28px; font-weight: 300; color: #1a1a2e;">
                                Sharp <span style="font-weight: 600;">| Sotheby's</span>
                            </h1>
                            <p style="margin: 5px 0 0 0; font-size: 11px; color: #666; letter-spacing: 2px; text-transform: uppercase;">International Realty</p>
                            <div style="width: 60px; height: 2px; background-color: #5b9a9a; margin: 20px auto;"></div>
                            <h2 style="margin: 0; font-size: 22px; font-weight: 400; font-style: italic; color: #5b9a9a;">MLS 2.0 Pipeline</h2>
                            <p style="margin: 5px 0 0 0; font-size: 14px; color: #5b9a9a;">All Sources CDC Report</p>
                        </td>
                    </tr>
                    
                    <!-- Status Banner -->
                    <tr>
                        <td style="padding: 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: ${status_bg};">
                                <tr>
                                    <td style="padding: 20px 40px; text-align: center;">
                                        <span style="display: inline-block; width: 40px; height: 40px; line-height: 40px; border-radius: 50%; background-color: ${status_color}; color: white; font-size: 20px; font-weight: bold;">${status_icon}</span>
                                        <h3 style="margin: 10px 0 0 0; font-size: 18px; color: ${status_color}; font-weight: 600;">${overall_status}</h3>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Timing Info -->
                    <tr>
                        <td style="padding: 30px 40px 20px 40px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td width="50%" style="padding: 10px 0;">
                                        <p style="margin: 0; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Started</p>
                                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #1a1a2e;">${START_TIME}</p>
                                    </td>
                                    <td width="50%" style="padding: 10px 0;">
                                        <p style="margin: 0; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Duration</p>
                                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #1a1a2e; font-weight: 600;">${DURATION_FMT}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Sources Status Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">Data Sources</h4>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 6px;">
                                <tr>
                                    <td style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0; border-radius: 6px 0 0 0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Source</span></td>
                                    <td style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Type</span></td>
                                    <td align="center" style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Status</span></td>
                                    <td align="right" style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0; border-radius: 0 6px 0 0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Records</span></td>
                                </tr>
                                <tr>
                                    <td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;">
                                        <span style="font-size: 14px; color: #1a1a2e; font-weight: 500;">🇨🇾 Cyprus</span><br>
                                        <span style="font-size: 11px; color: #888;">SHARPSIR-CY-001</span><br>
                                        <span style="font-size: 10px; color: #5b9a9a; font-family: monospace;">${CY_SYSTEM_ID}</span>
                                    </td>
                                    <td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #666;">Qobrix API</span></td>
                                    <td align="center" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="color: ${CY_COLOR}; font-weight: 600;">${CY_STATUS}</span></td>
                                    <td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #5b9a9a; font-weight: 600;">${CY_CHANGES} changed</span></td>
                                </tr>
                                <tr>
                                    <td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;">
                                        <span style="font-size: 14px; color: #1a1a2e; font-weight: 500;">🇭🇺 Hungary</span><br>
                                        <span style="font-size: 11px; color: #888;">SHARPSIR-HU-001</span><br>
                                        <span style="font-size: 10px; color: #5b9a9a; font-family: monospace;">${HU_SYSTEM_ID}</span>
                                    </td>
                                    <td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #666;">DASH FILE</span></td>
                                    <td align="center" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="color: ${HU_COLOR}; font-weight: 600;">${HU_STATUS}</span></td>
                                    <td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #5b9a9a; font-weight: 600;">${HU_RECORDS} records</span></td>
                                </tr>
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <span style="font-size: 14px; color: #1a1a2e; font-weight: 500;">🇰🇿 Kazakhstan</span><br>
                                        <span style="font-size: 11px; color: #888;">SHARPSIR-KZ-001</span><br>
                                        <span style="font-size: 10px; color: #5b9a9a; font-family: monospace;">${KZ_SYSTEM_ID}</span>
                                    </td>
                                    <td style="padding: 15px 20px;"><span style="font-size: 13px; color: #666;">DASH API</span></td>
                                    <td align="center" style="padding: 15px 20px;"><span style="color: ${KZ_COLOR}; font-weight: 600;">${KZ_STATUS}</span></td>
                                    <td align="right" style="padding: 15px 20px;"><span style="font-size: 14px; color: #5b9a9a; font-weight: 600;">${KZ_RECORDS} records</span></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- API Integration Tests Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">API Integration Tests (Cyprus)</h4>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: ${api_status_bg}; border-radius: 6px; margin-bottom: 15px;">
                                <tr>
                                    <td style="padding: 15px 20px; text-align: center;">
                                        <span style="font-size: 16px; color: ${api_status_color}; font-weight: 600;">Overall: ${API_TEST_STATUS}</span>
                                    </td>
                                </tr>
                            </table>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 6px;">
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Property Count</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_PROP_COUNT_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Property Data</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_PROP_DATA_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Media Count</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_MEDIA_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Members</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_MEMBERS_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Contacts</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_CONTACTS_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Field Transforms</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_TRANSFORM_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">RESO Types</span></td><td align="right" style="padding: 10px 20px; border-bottom: 1px solid #e5e5e5;">${API_TYPES_HTML}</td></tr>
                                <tr><td style="padding: 10px 20px;"><span style="font-size: 13px; color: #1a1a2e;">Media URLs</span></td><td align="right" style="padding: 10px 20px;">${API_URLS_HTML}</td></tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Log Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <details style="background-color: #f9fafb; border-radius: 6px; padding: 15px;">
                                <summary style="cursor: pointer; font-size: 14px; color: #5b9a9a; font-weight: 600;">View Full Log</summary>
                                <pre style="margin: 15px 0 0 0; padding: 15px; background-color: #1a1a2e; color: #e5e5e5; border-radius: 4px; font-size: 11px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;">${LOG_CONTENT}</pre>
                            </details>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; background-color: #1a1a2e; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #888;">Server: ${HOSTNAME}</p>
                            <p style="margin: 10px 0 0 0; font-size: 11px; color: #666;">Sharp Sotheby's International Realty - $(date '+%Y')</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
EOF
}

# ════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ════════════════════════════════════════════════════════════════════════════

echo "╔══════════════════════════════════════════════════════════════╗" | tee "$LOG_FILE"
echo "║  MLS 2.0 All Sources CDC Pipeline                            ║" | tee -a "$LOG_FILE"
echo "║  ${START_TIME}                                  ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "📊 Sources configured:" | tee -a "$LOG_FILE"
echo "  1. Cyprus (CY):     ${SRC_1_OFFICE_KEY:-SHARPSIR-CY-001} - Qobrix API" | tee -a "$LOG_FILE"
echo "  2. Hungary (HU):    ${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001} - DASH FILE" | tee -a "$LOG_FILE"
echo "  3. Kazakhstan (KZ): ${SRC_3_OFFICE_KEY:-SHARPSIR-KZ-001} - DASH API" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

OVERALL_STATUS="SUCCESS"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Cyprus - Qobrix CDC (existing pipeline)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 1: Cyprus (Qobrix API) CDC" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

cd "$MLS2_ROOT"
if "$SCRIPT_DIR/run_pipeline.sh" cdc >> "$LOG_FILE" 2>&1; then
    CY_STATUS="SUCCESS"
    echo "✅ Cyprus CDC completed" | tee -a "$LOG_FILE"
    # Extract changes count
    CY_CHANGES=$(grep -oP "Properties: \K[0-9]+" "$LOG_FILE" 2>/dev/null | tail -1 || echo "0")
else
    CY_STATUS="FAILED"
    OVERALL_STATUS="FAILED"
    echo "❌ Cyprus CDC failed" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Kazakhstan - Fetch from DASH API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 2: Kazakhstan (DASH API) Fetch & Load" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

if [ -n "$SRC_3_DASH_API_KEY" ]; then
    echo "🔄 Fetching Kazakhstan listings from DASH API..." | tee -a "$LOG_FILE"
    KZ_START_LINE=$(wc -l < "$LOG_FILE")
    if python3 "$SCRIPT_DIR/fetch_dash_api.py" --source "${SRC_3_OFFICE_KEY:-SHARPSIR-KZ-001}" >> "$LOG_FILE" 2>&1; then
        KZ_STATUS="SUCCESS"
        echo "✅ Kazakhstan fetch & load completed" | tee -a "$LOG_FILE"
        # Extract records count from KZ section only (lines after KZ_START_LINE)
        KZ_RECORDS=$(tail -n +$KZ_START_LINE "$LOG_FILE" | grep -oP "Saved \K[0-9]+" | tail -1 || echo "0")
        [ "$KZ_RECORDS" = "0" ] && KZ_RECORDS=$(tail -n +$KZ_START_LINE "$LOG_FILE" | grep -oP "Unique listings fetched: \K[0-9]+" | tail -1 || echo "0")
    else
        KZ_STATUS="FAILED"
        OVERALL_STATUS="WARNING"
        echo "⚠️ Kazakhstan fetch had issues" | tee -a "$LOG_FILE"
    fi
else
    KZ_STATUS="SKIPPED"
    echo "⏭️ Kazakhstan source not configured (skipping)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Hungary - Process DASH FILE (if new files)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 3: Hungary (DASH FILE) Check for new files" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

HU_SOURCE_DIR="${SRC_2_DIR:-$MLS2_ROOT/dash_hsir_source}"
if [ -d "$HU_SOURCE_DIR" ]; then
    echo "📁 Checking $HU_SOURCE_DIR for new files..." | tee -a "$LOG_FILE"
    HU_START_LINE=$(wc -l < "$LOG_FILE")
    if python3 "$SCRIPT_DIR/load_dash_bronze.py" --source "${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001}" >> "$LOG_FILE" 2>&1; then
        HU_STATUS="SUCCESS"
        echo "✅ Hungary processing completed" | tee -a "$LOG_FILE"
        # Extract records count from HU section only (lines after HU_START_LINE)
        HU_SECTION=$(tail -n +$HU_START_LINE "$LOG_FILE")
        if echo "$HU_SECTION" | grep -q "No new files to process"; then
            # No new files - query Databricks for total count
            HU_RECORDS=$(curl -s -X POST "https://${DATABRICKS_HOST#https://}/api/2.0/sql/statements" \
                -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
                -H "Content-Type: application/json" \
                -d '{"warehouse_id": "'"${DATABRICKS_WAREHOUSE_ID}"'", "statement": "SELECT COUNT(*) FROM mls2.dash_bronze.properties WHERE office_key = '\''SHARPSIR-HU-001'\''", "wait_timeout": "10s"}' \
                2>/dev/null | grep -oP '"data_array":\[\["\K[0-9]+' || echo "0")
            HU_RECORDS="${HU_RECORDS:-0} (no change)"
        else
            HU_RECORDS=$(echo "$HU_SECTION" | grep -oP "Found \K[0-9]+" | tail -1 || echo "0")
            [ "$HU_RECORDS" = "0" ] && HU_RECORDS=$(echo "$HU_SECTION" | grep -oP "[0-9]+ total" | head -1 | grep -oP "^[0-9]+" || echo "0")
        fi
    else
        HU_STATUS="FAILED"
        OVERALL_STATUS="WARNING"
        echo "⚠️ Hungary processing had issues" | tee -a "$LOG_FILE"
    fi
else
    HU_STATUS="SKIPPED"
    echo "⏭️ Hungary source directory not found (skipping)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4: API Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "STEP 4: API Integration Tests" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

echo "Running API Integration Tests..." | tee -a "$LOG_FILE"
if "$SCRIPT_DIR/verify_api_integrity.sh" > "$API_TEST_LOG" 2>&1; then
    echo "✅ API Tests: PASSED" | tee -a "$LOG_FILE"
    # Copy summary to main log
    grep -A 20 "^SUMMARY" "$API_TEST_LOG" >> "$LOG_FILE" 2>/dev/null || true
else
    echo "⚠️ API Tests: COMPLETED WITH WARNINGS" | tee -a "$LOG_FILE"
fi
cat "$API_TEST_LOG" >> "$LOG_FILE" 2>/dev/null || true
echo "" | tee -a "$LOG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 5: Summary & Email Report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "SUMMARY" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "Started:  $START_TIME" | tee -a "$LOG_FILE"
echo "Finished: $END_TIME" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Source Status:" | tee -a "$LOG_FILE"
echo "  🇨🇾 Cyprus (${SRC_1_SYSTEM_ID:-QOBRIX_CY}):       $CY_STATUS (${CY_CHANGES:-0} changes)" | tee -a "$LOG_FILE"
echo "  🇭🇺 Hungary (${SRC_2_SYSTEM_ID:-DASH_HU}):        $HU_STATUS (${HU_RECORDS:-0} records)" | tee -a "$LOG_FILE"
echo "  🇰🇿 Kazakhstan (${SRC_3_SYSTEM_ID:-DASH_KZ_SANDBOX}): $KZ_STATUS (${KZ_RECORDS:-0} records)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Determine final status
if [ "$CY_STATUS" = "FAILED" ]; then
    OVERALL_STATUS="FAILED"
fi

echo "✅ All Sources CDC Pipeline Complete! Status: $OVERALL_STATUS" | tee -a "$LOG_FILE"

# Send email report
echo "" | tee -a "$LOG_FILE"
echo "📧 Sending email report to $EMAIL_TO..." | tee -a "$LOG_FILE"
if send_email_report "$OVERALL_STATUS"; then
    echo "✅ Email sent successfully" | tee -a "$LOG_FILE"
else
    echo "⚠️ Failed to send email" | tee -a "$LOG_FILE"
fi

exit 0
