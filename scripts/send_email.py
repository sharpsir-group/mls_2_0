#!/usr/bin/env python3
"""Shared branded email sender for MLS 2.0 pipeline notifications.

Usage:
    python3 scripts/send_email.py \
        --subject "[MLS 2.0] CDC RECOVERY MODE" \
        --status "RECOVERY" \
        --body-html "<p>Pipeline body here</p>"

Reads RESEND_API_KEY, RESEND_EMAIL_FROM, RESEND_EMAIL_TO from env vars.
Falls back to loading from .env in the repo root if present.
"""

import argparse
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' package not installed. Run: pip3 install requests")


STATUS_COLORS = {
    "SUCCESS":  {"color": "#10b981", "bg": "#ecfdf5", "icon": "&#10003;"},
    "WARNING":  {"color": "#f59e0b", "bg": "#fffbeb", "icon": "&#9888;"},
    "FAILED":   {"color": "#ef4444", "bg": "#fef2f2", "icon": "&#10007;"},
    "RECOVERY": {"color": "#f97316", "bg": "#fff7ed", "icon": "&#9888;"},
}


def load_dotenv(env_path: Path):
    """Minimal .env loader -- sets vars not already in the environment."""
    if not env_path.is_file():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def wrap_html(body_html: str, status: str, subject: str) -> str:
    """Wrap inner body HTML in the branded Sharp Sotheby's template."""
    st = STATUS_COLORS.get(status.upper(), STATUS_COLORS["WARNING"])
    hostname = platform.node()
    year = datetime.now().strftime("%Y")

    return f"""\
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
                        </td>
                    </tr>
                    <!-- Status Banner -->
                    <tr>
                        <td style="padding: 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {st['bg']};">
                                <tr>
                                    <td style="padding: 20px 40px; text-align: center;">
                                        <span style="display: inline-block; width: 40px; height: 40px; line-height: 40px; border-radius: 50%; background-color: {st['color']}; color: white; font-size: 20px; font-weight: bold;">{st['icon']}</span>
                                        <h3 style="margin: 10px 0 0 0; font-size: 18px; color: {st['color']}; font-weight: 600;">{status.upper()}</h3>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Body Content (caller supplies <tr> rows) -->
{body_html}
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; background-color: #1a1a2e; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #888;">Server: {hostname}</p>
                            <p style="margin: 10px 0 0 0; font-size: 11px; color: #666;">Sharp Sotheby&rsquo;s International Realty &ndash; {year}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def send_email(subject: str, html: str, api_key: str, email_from: str, email_to: str):
    """Send an email via the Resend API."""
    recipients = [e.strip() for e in email_to.split(",") if e.strip()]
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"from": email_from, "to": recipients, "subject": subject, "html": html},
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"Email sent ({subject})")
    else:
        print(f"Resend API returned HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Send branded MLS 2.0 pipeline email")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--status", required=True, choices=["SUCCESS", "WARNING", "FAILED", "RECOVERY"],
                        help="Pipeline status (controls banner color)")
    parser.add_argument("--body-html", required=True, help="Inner HTML body content")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")

    api_key = os.environ.get("RESEND_API_KEY", "")
    email_from = os.environ.get("RESEND_EMAIL_FROM", "")
    email_to = os.environ.get("RESEND_EMAIL_TO", "")

    if not api_key:
        sys.exit("ERROR: RESEND_API_KEY not set")
    if not email_from:
        sys.exit("ERROR: RESEND_EMAIL_FROM not set")
    if not email_to:
        sys.exit("ERROR: RESEND_EMAIL_TO not set")

    full_html = wrap_html(args.body_html, args.status, args.subject)
    send_email(args.subject, full_html, api_key, email_from, email_to)


if __name__ == "__main__":
    main()
