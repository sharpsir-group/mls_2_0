#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# =============================================================================
# SSL Setup for mls.sharpsir.group (Let's Encrypt)
# =============================================================================
# Obtains SSL certificates via certbot and configures .env for HTTPS.
# Requires: DNS for mls.sharpsir.group pointing to this server.
#
# Usage: sudo ./scripts/setup-ssl.sh
# =============================================================================

set -e

DOMAIN="mls.sharpsir.group"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$MLS2_ROOT/.env"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0"
    exit 1
fi

echo "=== SSL Setup for $DOMAIN ==="
echo ""

# Check certbot
if ! command -v certbot &>/dev/null; then
    echo "Installing certbot..."
    apt-get update -qq
    apt-get install -y certbot
fi

# Detect webroot for Apache/Nginx (Bitnami or standard)
WEBROOT=""
for dir in /opt/bitnami/apache/htdocs /var/www/html /usr/share/nginx/html; do
    if [ -d "$dir" ]; then
        WEBROOT="$dir"
        break
    fi
done

CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@sharpsir.group}"
echo "Obtaining certificate from Let's Encrypt (email: $CERTBOT_EMAIL)..."

if [ -n "$WEBROOT" ]; then
    echo "Using webroot: $WEBROOT"
    certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" --non-interactive --agree-tos --email "$CERTBOT_EMAIL" || {
        echo ""
        echo "Certbot webroot failed. Trying standalone (will need port 80 free)..."
        certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email "$CERTBOT_EMAIL" || {
            echo ""
            echo "Certbot failed. Common causes:"
            echo "  - DNS not pointing to this server"
            echo "  - Port 80 blocked by firewall"
            echo "  - Webroot not accessible from internet"
            exit 1
        }
    }
else
    echo "No webroot found, using standalone (port 80 must be free)..."
    certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email "$CERTBOT_EMAIL" || {
        echo ""
        echo "Certbot failed. Common causes:"
        echo "  - DNS not pointing to this server"
        echo "  - Port 80 blocked by firewall"
        echo "  - Another service using port 80"
        exit 1
    }
fi

CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    echo "Certificate files not found"
    exit 1
fi

# Update .env
if [ -f "$ENV_FILE" ]; then
    if grep -q "^RESO_SSL_CERTFILE=" "$ENV_FILE"; then
        sed -i "s|^RESO_SSL_CERTFILE=.*|RESO_SSL_CERTFILE=$CERT_PATH|" "$ENV_FILE"
    else
        echo "" >> "$ENV_FILE"
        echo "# SSL for HTTPS" >> "$ENV_FILE"
        echo "RESO_SSL_CERTFILE=$CERT_PATH" >> "$ENV_FILE"
    fi
    if grep -q "^RESO_SSL_KEYFILE=" "$ENV_FILE"; then
        sed -i "s|^RESO_SSL_KEYFILE=.*|RESO_SSL_KEYFILE=$KEY_PATH|" "$ENV_FILE"
    else
        echo "RESO_SSL_KEYFILE=$KEY_PATH" >> "$ENV_FILE"
    fi
    echo "Updated $ENV_FILE with SSL paths"
else
    echo "Create $ENV_FILE and add:"
    echo "  RESO_SSL_CERTFILE=$CERT_PATH"
    echo "  RESO_SSL_KEYFILE=$KEY_PATH"
fi

# Restart API
echo ""
echo "Starting API with SSL..."
if command -v pm2 &>/dev/null; then
    cd "$MLS2_ROOT" && pm2 start reso-web-api 2>/dev/null || pm2 restart reso-web-api
elif [ -f "$MLS2_ROOT/node_modules/.bin/pm2" ]; then
    cd "$MLS2_ROOT" && "$MLS2_ROOT/node_modules/.bin/pm2" start ecosystem.config.js 2>/dev/null || "$MLS2_ROOT/node_modules/.bin/pm2" restart reso-web-api
fi

echo ""
echo "=== Done ==="
echo "Test: curl -v https://$DOMAIN:3900/health"
echo ""
echo "Auto-renewal: add to crontab -e:"
echo "  0 3 * * * certbot renew --quiet --deploy-hook 'pm2 restart reso-web-api'"
