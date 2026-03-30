#!/bin/bash
# One-time full sync wrapper: runs pipeline + sends email report via Resend.
# Self-removes its cron entry after execution.
#
# Resilience guarantees:
#   - Email is ALWAYS sent (via trap EXIT) regardless of pipeline outcome
#   - Pipeline has a 6-hour timeout to prevent infinite hangs
#   - Cron entry is always cleaned up

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
DATE=$(date '+%Y-%m-%d')
LOG_FILE="$MLS2_ROOT/logs/full_sync_${DATE}.log"
STATUS="FAILED"

export PATH="$HOME/bin:$HOME/.local/bin:$PATH"
export DATABRICKS_CLI_DO_NOT_SHOW_UPGRADE_MESSAGE=1

if [ -f "$MLS2_ROOT/.env" ]; then
    set -a; source "$MLS2_ROOT/.env"; set +a
fi

mkdir -p "$MLS2_ROOT/logs"

# ── Trap: guarantee email + cron cleanup on ANY exit ──────────────────────────
send_report_and_cleanup() {
    echo "[$(date)] Sending email report (STATUS=$STATUS)..." >> "$LOG_FILE" 2>/dev/null || true

    python3 - "$STATUS" "$LOG_FILE" "$DATE" << 'PYEOF' || true
import json, os, sys, requests
from pathlib import Path

status, log_path, date = sys.argv[1], sys.argv[2], sys.argv[3]
api_key = os.environ.get("RESEND_API_KEY", "")
recipients = [e.strip() for e in os.environ.get("NOTIFY_EMAILS", "").split(",") if e.strip()]
if not api_key or not recipients:
    print("RESEND_API_KEY or NOTIFY_EMAILS not set, skipping email")
    sys.exit(0)

log = Path(log_path).read_text() if Path(log_path).exists() else "(no log)"
escaped = log[-4000:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
ok = status == "SUCCESS"
color, bg, icon = ("#10b981", "#ecfdf5", "&#10003;") if ok else ("#ef4444", "#fef2f2", "&#10007;")

html = f"""<html><body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" style="background:#f5f5f5;padding:40px 20px;"><tr><td align="center">
<table width="600" style="background:#fff;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
<tr><td style="padding:40px;text-align:center;border-bottom:1px solid #e5e5e5;">
<h2 style="margin:0;font-size:22px;color:#5b9a9a;">MLS 2.0 Full Sync</h2>
<p style="margin:5px 0 0;color:#888;font-size:14px;">{date}</p></td></tr>
<tr><td style="padding:30px;text-align:center;background:{bg};">
<span style="display:inline-block;width:50px;height:50px;line-height:50px;border-radius:50%;background:{color};color:#fff;font-size:24px;">{icon}</span>
<h3 style="margin:15px 0 0;color:{color};">{status}</h3></td></tr>
<tr><td style="padding:20px 30px;">
<pre style="background:#1a1a2e;color:#e5e5e5;padding:15px;border-radius:4px;font-size:11px;overflow-x:auto;white-space:pre-wrap;">{escaped}</pre></td></tr>
<tr><td style="padding:20px 30px;background:#1a1a2e;border-radius:0 0 8px 8px;text-align:center;">
<p style="margin:0;font-size:11px;color:#666;">Sharp Sotheby&#39;s International Realty</p></td></tr>
</table></td></tr></table></body></html>"""

resp = requests.post("https://api.resend.com/emails",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"from": "MLS Pipeline <noreply@intranet.sharpsir.group>",
          "to": recipients,
          "subject": f"[MLS 2.0] Full Sync {status} - {date}",
          "html": html},
    timeout=15)
print(f"Email: HTTP {resp.status_code}")
PYEOF

    # Self-remove cron entry
    crontab -l 2>/dev/null | grep -v 'run_full_sync_with_report' | crontab - 2>/dev/null || true
}

trap send_report_and_cleanup EXIT

# ── Run pipeline with 12-hour timeout (Bronze Full Refresh can take ~8h) ──────
if timeout 43200 "$SCRIPT_DIR/run_pipeline.sh" all >> "$LOG_FILE" 2>&1; then
    STATUS="SUCCESS"
else
    STATUS="FAILED"
    echo "[$(date)] Pipeline exited with non-zero status (or timed out)" >> "$LOG_FILE" 2>/dev/null || true
fi
