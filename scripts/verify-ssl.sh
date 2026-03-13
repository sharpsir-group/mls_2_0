#!/bin/bash
# Verify SSL configuration for mls.sharpsir.group
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== SSL Configuration Check ==="
[ -f "$MLS2_ROOT/.env" ] && set -a && source "$MLS2_ROOT/.env" 2>/dev/null && set +a

echo "RESO_SSL_CERTFILE: ${RESO_SSL_CERTFILE:-<not set>}"
echo "RESO_SSL_KEYFILE:  ${RESO_SSL_KEYFILE:-<not set>}"

if [ -z "$RESO_SSL_CERTFILE" ] || [ -z "$RESO_SSL_KEYFILE" ]; then
    echo ""
    echo "Add to .env:"
    echo "  RESO_SSL_CERTFILE=/etc/letsencrypt/live/mls.sharpsir.group/fullchain.pem"
    echo "  RESO_SSL_KEYFILE=/etc/letsencrypt/live/mls.sharpsir.group/privkey.pem"
    echo ""
    echo "Then run: sudo ./scripts/setup-ssl.sh  (to obtain certs)"
    exit 1
fi

if [ ! -f "$RESO_SSL_CERTFILE" ]; then
    echo "ERROR: Certificate file not found: $RESO_SSL_CERTFILE"
    exit 1
fi
if [ ! -f "$RESO_SSL_KEYFILE" ]; then
    echo "ERROR: Key file not found: $RESO_SSL_KEYFILE"
    exit 1
fi

echo ""
echo "Files OK. Restart API to apply: ./scripts/pm2-manage.sh restart"

echo ""
echo "Test: curl -v https://mls.sharpsir.group:3900/health"
