#!/bin/bash
# One-time full refresh with email report

export PATH="/home/bitnami/.local/bin:/home/bitnami/.nvm/versions/node/v20.19.5/bin:/opt/bitnami/python/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$MLS2_ROOT/logs/full_refresh_$(date +%Y-%m-%d).log"
START_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    set -a
    source "$MLS2_ROOT/.env"
    set +a
fi
EMAIL_TO="${RESEND_EMAIL_TO:-sseregin@sharp-sothebys-realty.com}"

echo "╔══════════════════════════════════════════════════════════════╗" | tee "$LOG_FILE"
echo "║  MLS 2.0 FULL REFRESH - One-time Fix                         ║" | tee -a "$LOG_FILE"
echo "║  $START_TIME                                  ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"

cd "$MLS2_ROOT"

# Run full refresh
if "$SCRIPT_DIR/run_pipeline.sh" all >> "$LOG_FILE" 2>&1; then
    STATUS="SUCCESS"
else
    STATUS="FAILED"
fi

END_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')

# Run API integrity test
echo "" >> "$LOG_FILE"
echo "Running API Integrity Tests..." >> "$LOG_FILE"
API_OUTPUT=$("$SCRIPT_DIR/verify_api_integrity.sh" 2>&1)
echo "$API_OUTPUT" >> "$LOG_FILE"

# Extract counts from log
PROPS_TOTAL=$(grep -oP 'properties\s*\|\s*\K\d+' "$LOG_FILE" | head -1 || echo "0")
CONTACTS_TOTAL=$(grep -oP 'contacts\s*\|\s*\K\d+' "$LOG_FILE" | head -1 || echo "0")

# Escape API output for HTML
API_OUTPUT_HTML=$(echo "$API_OUTPUT" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')

INNER_BODY=$(cat << BODYEOF
                    <tr>
                        <td style="padding: 30px 40px 20px 40px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td width="50%" style="padding: 10px 0;">
                                        <p style="margin: 0; font-size: 12px; color: #888; text-transform: uppercase;">Started</p>
                                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #1a1a2e;">$START_TIME</p>
                                    </td>
                                    <td width="50%" style="padding: 10px 0;">
                                        <p style="margin: 0; font-size: 12px; color: #888; text-transform: uppercase;">Completed</p>
                                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #1a1a2e;">$END_TIME</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h4 style="margin: 0 0 15px 0; font-size: 14px; color: #5b9a9a; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #5b9a9a; padding-bottom: 10px;">API Integrity Test Results</h4>
                            <pre style="background: #1a1a2e; color: #e5e5e5; padding: 15px; border-radius: 4px; font-size: 11px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;">$API_OUTPUT_HTML</pre>
                        </td>
                    </tr>
BODYEOF
)

python3 "$SCRIPT_DIR/send_email.py" \
    --subject "[MLS 2.0] Full Refresh $STATUS - $(date '+%Y-%m-%d')" \
    --status "$STATUS" \
    --body-html "$INNER_BODY"

echo "Email sent to $EMAIL_TO"
