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

EMAIL_TO="${NOTIFY_EMAILS:-sseregin@sharp-sothebys-realty.com}"

echo "╔══════════════════════════════════════════════════════════════╗" | tee "$LOG_FILE"
echo "║  MLS 2.0 FULL REFRESH - One-time Fix                         ║" | tee -a "$LOG_FILE"
echo "║  $START_TIME                                  ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"

cd "$MLS2_ROOT"

# Run full refresh
if "$SCRIPT_DIR/run_pipeline.sh" all >> "$LOG_FILE" 2>&1; then
    STATUS="SUCCESS"
    STATUS_COLOR="#10b981"
    STATUS_ICON="&#10003;"
else
    STATUS="FAILED"
    STATUS_COLOR="#ef4444"
    STATUS_ICON="&#10007;"
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

# Build HTML email
STATUS_BG=$([ "$STATUS" = "SUCCESS" ] && echo "#ecfdf5" || echo "#fef2f2")
html_body=$(cat << HTMLEOF
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
  <tr><td style="padding:40px;text-align:center;border-bottom:1px solid #e5e5e5;">
    <h2 style="margin:20px 0 0;font-size:22px;color:#5b9a9a;">MLS 2.0 Full Refresh</h2>
    <p style="margin:5px 0 0;color:#888;">One-time Data Sync</p>
  </td></tr>
  <tr><td style="padding:30px;text-align:center;background:${STATUS_BG};">
    <span style="display:inline-block;width:50px;height:50px;line-height:50px;border-radius:50%;background:$STATUS_COLOR;color:#fff;font-size:24px;">$STATUS_ICON</span>
    <h3 style="margin:15px 0 0;color:$STATUS_COLOR;">$STATUS</h3>
  </td></tr>
  <tr><td style="padding:30px;">
    <table width="100%">
      <tr><td width="50%"><p style="margin:0;font-size:12px;color:#888;">STARTED</p><p style="margin:5px 0;font-size:14px;">$START_TIME</p></td>
          <td width="50%"><p style="margin:0;font-size:12px;color:#888;">COMPLETED</p><p style="margin:5px 0;font-size:14px;">$END_TIME</p></td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:0 30px 30px;">
    <h4 style="margin:0 0 15px;color:#5b9a9a;border-bottom:2px solid #5b9a9a;padding-bottom:10px;">API Integrity Test Results</h4>
    <pre style="background:#1a1a2e;color:#e5e5e5;padding:15px;border-radius:4px;font-size:11px;overflow-x:auto;white-space:pre-wrap;">$API_OUTPUT</pre>
  </td></tr>
  <tr><td style="padding:20px 30px;background:#1a1a2e;border-radius:0 0 8px 8px;text-align:center;">
    <p style="margin:0;font-size:12px;color:#888;">Server: $(hostname)</p>
    <p style="margin:10px 0 0;font-size:11px;color:#666;">Sharp Sotheby's International Realty</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>
HTMLEOF
)

# Send via Resend API
subject="[MLS 2.0] Full Refresh $STATUS - $(date '+%Y-%m-%d')"
resend_key="${RESEND_API_KEY:-}"
if [ -z "$resend_key" ]; then
    echo "RESEND_API_KEY not set, cannot send email"
    exit 1
fi

json_payload=$(python3 -c "
import json, sys
html = sys.stdin.read()
recipients = [e.strip() for e in '$EMAIL_TO'.split(',') if e.strip()]
print(json.dumps({
    'from': 'MLS Pipeline <noreply@intranet.sharpsir.group>',
    'to': recipients,
    'subject': '$subject',
    'html': html
}))
" <<< "$html_body")

response=$(curl -s -w "\n%{http_code}" -X POST "https://api.resend.com/emails" \
    -H "Authorization: Bearer $resend_key" \
    -H "Content-Type: application/json" \
    -d "$json_payload" 2>&1)

http_code=$(echo "$response" | tail -1)
if [ "$http_code" = "200" ]; then
    echo "Email sent to $EMAIL_TO"
else
    echo "Failed to send email (HTTP $http_code): $(echo "$response" | head -1)"
fi
