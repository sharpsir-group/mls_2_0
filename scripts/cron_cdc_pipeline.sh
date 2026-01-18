#!/bin/bash
# MLS 2.0 CDC Pipeline - Cron Job Wrapper
# Runs daily at 3:00 AM MSK (0:00 UTC), sends HTML email report
# Usage: Called by cron, not manually

# Set PATH for cron environment (databricks CLI is in ~/.local/bin)
export PATH="/home/bitnami/.local/bin:/home/bitnami/.nvm/versions/node/v20.19.5/bin:/opt/bitnami/python/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$MLS2_ROOT/logs"
EMAIL_TO="sseregin@sharp-sothebys-realty.com"
HOSTNAME=$(hostname)
DATE=$(date '+%Y-%m-%d')
START_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
START_SECONDS=$(date +%s)

# Ensure log directory exists
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/cdc_pipeline_${DATE}.log"
API_TEST_LOG="$LOG_DIR/api_test_${DATE}.log"

# API Test results (will be populated after running tests)
API_TEST_STATUS="SKIPPED"
API_PROP_COUNT="--"
API_PROP_DATA="--"
API_MEDIA="--"
API_MEMBERS="--"
API_CONTACTS="--"
API_TRANSFORM="--"
API_TYPES="--"
API_URLS="--"

# Function to extract metrics from log
extract_metrics() {
    local log="$1"
    
    # Extract total records and CDC changes from the table output in log
    PROPS_TOTAL=$(grep -E "^\| properties\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    AGENTS_TOTAL=$(grep -E "^\| agents\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    CONTACTS_TOTAL=$(grep -E "^\| contacts\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    VIEWINGS_TOTAL=$(grep -E "^\| property_viewings\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    MEDIA_TOTAL=$(grep -E "^\| property_media\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    OPPS_TOTAL=$(grep -E "^\| opportunities\s" "$log" 2>/dev/null | awk -F'|' '{gsub(/[^0-9]/,"",$3); print $3}' | tail -1 || echo "0")
    
    # Extract CDC changes from the "X changed" lines
    PROPS_CHANGED=$(grep -oP "Properties: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    AGENTS_CHANGED=$(grep -oP "Agents: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    CONTACTS_CHANGED=$(grep -oP "Contacts: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    VIEWINGS_CHANGED=$(grep -oP "Viewings: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    MEDIA_CHANGED=$(grep -oP "Media: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    OPPS_CHANGED=$(grep -oP "Opportunities: \K[0-9]+" "$log" 2>/dev/null | tail -1 || echo "0")
    
    # Set defaults if empty
    PROPS_TOTAL=${PROPS_TOTAL:-0}
    AGENTS_TOTAL=${AGENTS_TOTAL:-0}
    CONTACTS_TOTAL=${CONTACTS_TOTAL:-0}
    VIEWINGS_TOTAL=${VIEWINGS_TOTAL:-0}
    MEDIA_TOTAL=${MEDIA_TOTAL:-0}
    OPPS_TOTAL=${OPPS_TOTAL:-0}
    PROPS_CHANGED=${PROPS_CHANGED:-0}
    AGENTS_CHANGED=${AGENTS_CHANGED:-0}
    CONTACTS_CHANGED=${CONTACTS_CHANGED:-0}
    VIEWINGS_CHANGED=${VIEWINGS_CHANGED:-0}
    MEDIA_CHANGED=${MEDIA_CHANGED:-0}
    OPPS_CHANGED=${OPPS_CHANGED:-0}
    
    # Count completed notebooks
    NOTEBOOKS_SUCCESS=$(grep -c "completed successfully" "$log" 2>/dev/null || echo "0")
    NOTEBOOKS_FAILED=$(grep -c "failed:" "$log" 2>/dev/null || echo "0")
}

# Function to extract API test results
extract_api_results() {
    local log="$1"
    
    if [ ! -f "$log" ]; then
        return
    fi
    
    # Parse SUMMARY section for pass/fail status
    API_PROP_COUNT=$(grep "Property Count:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_PROP_DATA=$(grep "Property Data:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_MEDIA=$(grep "Media Count:" "$log" 2>/dev/null | grep -q "PASS" && echo "PASS" || echo "FAIL")
    API_MEMBERS=$(grep -E "Agent.*Member|Member.*Agent" "$log" 2>/dev/null | head -1 | grep -q "PASS\|✅" && echo "PASS" || echo "WARN")
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
    
    # Overall status
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
        PASS)
            echo '<span style="color: #10b981; font-weight: 600;">PASS</span>'
            ;;
        FAIL)
            echo '<span style="color: #ef4444; font-weight: 600;">FAIL</span>'
            ;;
        WARN)
            echo '<span style="color: #f59e0b; font-weight: 600;">WARN</span>'
            ;;
        *)
            echo '<span style="color: #888;">--</span>'
            ;;
    esac
}

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
        local secs=$((seconds % 60))
        echo "${hours}h ${mins}m ${secs}s"
    fi
}

# Function to send HTML email report
send_report() {
    local status="$1"
    local status_color="#10b981"  # Green for success
    local status_bg="#ecfdf5"
    local status_icon="&#10003;"
    
    if [ "$status" = "FAILED" ]; then
        status_color="#ef4444"  # Red for failure
        status_bg="#fef2f2"
        status_icon="&#10007;"
    fi
    
    local subject="[MLS 2.0] CDC Pipeline ${status} - ${DATE}"
    
    # Calculate duration
    END_SECONDS=$(date +%s)
    DURATION=$((END_SECONDS - START_SECONDS))
    DURATION_FMT=$(format_duration $DURATION)
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
    
    # Extract metrics from log
    extract_metrics "$LOG_FILE"
    
    # Extract API test results
    extract_api_results "$API_TEST_LOG"
    
    # Calculate totals
    TOTAL_RECORDS=$((PROPS_TOTAL + AGENTS_TOTAL + CONTACTS_TOTAL + VIEWINGS_TOTAL + MEDIA_TOTAL + OPPS_TOTAL))
    TOTAL_CHANGES=$((PROPS_CHANGED + AGENTS_CHANGED + CONTACTS_CHANGED + VIEWINGS_CHANGED + MEDIA_CHANGED + OPPS_CHANGED))
    
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
    
    # Escape log content for HTML
    LOG_CONTENT=$(cat "$LOG_FILE" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')
    
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
                            <p style="margin: 5px 0 0 0; font-size: 14px; color: #5b9a9a;">CDC Sync Report</p>
                        </td>
                    </tr>
                    
                    <!-- Status Banner -->
                    <tr>
                        <td style="padding: 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: ${status_bg};">
                                <tr>
                                    <td style="padding: 20px 40px; text-align: center;">
                                        <span style="display: inline-block; width: 40px; height: 40px; line-height: 40px; border-radius: 50%; background-color: ${status_color}; color: white; font-size: 20px; font-weight: bold;">${status_icon}</span>
                                        <h3 style="margin: 10px 0 0 0; font-size: 18px; color: ${status_color}; font-weight: 600;">${status}</h3>
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
                    
                    <!-- Data Summary Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">Data Summary</h4>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 6px;">
                                <tr>
                                    <td style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0; border-radius: 6px 0 0 0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Entity</span></td>
                                    <td align="right" style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Total</span></td>
                                    <td align="right" style="padding: 12px 20px; border-bottom: 2px solid #e5e5e5; background-color: #f0f0f0; border-radius: 0 6px 0 0;"><span style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: 600;">Changed</span></td>
                                </tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Properties</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${PROPS_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${PROPS_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Agents</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${AGENTS_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${AGENTS_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Contacts</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${CONTACTS_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${CONTACTS_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Viewings</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${VIEWINGS_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${VIEWINGS_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Media</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${MEDIA_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${MEDIA_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #1a1a2e;">Opportunities</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 14px; color: #666;">${OPPS_TOTAL}</span></td><td align="right" style="padding: 15px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 16px; color: #5b9a9a; font-weight: 600;">${OPPS_CHANGED}</span></td></tr>
                                <tr><td style="padding: 15px 20px; background-color: #1a1a2e; border-radius: 0 0 0 6px;"><span style="font-size: 14px; color: #fff; font-weight: 600;">TOTAL</span></td><td align="right" style="padding: 15px 20px; background-color: #1a1a2e;"><span style="font-size: 18px; color: #fff; font-weight: 700;">${TOTAL_RECORDS}</span></td><td align="right" style="padding: 15px 20px; background-color: #1a1a2e; border-radius: 0 0 6px 0;"><span style="font-size: 18px; color: #5b9a9a; font-weight: 700;">${TOTAL_CHANGES}</span></td></tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- ETL Jobs Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">ETL Jobs</h4>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td width="50%" style="padding: 15px; background-color: #ecfdf5; border-radius: 6px 0 0 6px; text-align: center;">
                                        <p style="margin: 0; font-size: 28px; color: #10b981; font-weight: 700;">${NOTEBOOKS_SUCCESS}</p>
                                        <p style="margin: 5px 0 0 0; font-size: 12px; color: #666; text-transform: uppercase;">Successful</p>
                                    </td>
                                    <td width="50%" style="padding: 15px; background-color: #fef2f2; border-radius: 0 6px 6px 0; text-align: center;">
                                        <p style="margin: 0; font-size: 28px; color: #ef4444; font-weight: 700;">${NOTEBOOKS_FAILED}</p>
                                        <p style="margin: 5px 0 0 0; font-size: 12px; color: #666; text-transform: uppercase;">Failed</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- API Integration Tests Section -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">API Integration Tests</h4>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: ${api_status_bg}; border-radius: 6px; margin-bottom: 15px;">
                                <tr>
                                    <td style="padding: 15px 20px; text-align: center;">
                                        <span style="font-size: 16px; color: ${api_status_color}; font-weight: 600;">Overall: ${API_TEST_STATUS}</span>
                                    </td>
                                </tr>
                            </table>
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 6px;">
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Property Count</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_PROP_COUNT_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Property Data</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_PROP_DATA_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Media Count</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_MEDIA_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Members</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_MEMBERS_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Contacts</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_CONTACTS_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">Field Transforms</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_TRANSFORM_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;"><span style="font-size: 13px; color: #1a1a2e;">RESO Types</span></td><td align="right" style="padding: 12px 20px; border-bottom: 1px solid #e5e5e5;">${API_TYPES_HTML}</td></tr>
                                <tr><td style="padding: 12px 20px;"><span style="font-size: 13px; color: #1a1a2e;">Media URLs</span></td><td align="right" style="padding: 12px 20px;">${API_URLS_HTML}</td></tr>
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

# Run the CDC pipeline
echo "╔══════════════════════════════════════════════════════════════╗" | tee "$LOG_FILE"
echo "║  MLS 2.0 CDC Pipeline Starting                               ║" | tee -a "$LOG_FILE"
echo "║  ${START_TIME}                                  ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

cd "$MLS2_ROOT"

PIPELINE_STATUS="SUCCESS"
if ! "$SCRIPT_DIR/run_pipeline.sh" cdc >> "$LOG_FILE" 2>&1; then
    PIPELINE_STATUS="FAILED"
fi

echo "" | tee -a "$LOG_FILE"
echo "Pipeline ${PIPELINE_STATUS} at $(date '+%Y-%m-%d %H:%M:%S %Z')" | tee -a "$LOG_FILE"

# Run API integrity tests
echo "" | tee -a "$LOG_FILE"
echo "Running API Integration Tests..." | tee -a "$LOG_FILE"
if "$SCRIPT_DIR/verify_api_integrity.sh" > "$API_TEST_LOG" 2>&1; then
    echo "API Tests: PASSED" | tee -a "$LOG_FILE"
else
    echo "API Tests: COMPLETED WITH WARNINGS" | tee -a "$LOG_FILE"
fi

# Send report
send_report "$PIPELINE_STATUS"

if [ "$PIPELINE_STATUS" = "FAILED" ]; then
    exit 1
fi
exit 0
