#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# =============================================================================
# RESO Web API PM2 Manager
# =============================================================================
# Manage the RESO Web API via PM2
#
# Usage:
#   ./scripts/pm2-manage.sh start     # Start the API
#   ./scripts/pm2-manage.sh stop      # Stop the API
#   ./scripts/pm2-manage.sh restart   # Restart the API
#   ./scripts/pm2-manage.sh status    # Show status
#   ./scripts/pm2-manage.sh logs      # Show logs
#   ./scripts/pm2-manage.sh setup     # Initial setup (venv + deps)
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$MLS2_ROOT/api"
APP_NAME="reso-web-api"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    echo "RESO Web API PM2 Manager"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  start     Start the API via PM2"
    echo "  stop      Stop the API"
    echo "  restart   Restart the API"
    echo "  status    Show PM2 status"
    echo "  logs      Show live logs (Ctrl+C to exit)"
    echo "  logs-err  Show error logs only"
    echo "  setup     Initial setup (create venv, install deps)"
    echo "  health    Check API health"
    echo "  save      Save PM2 process list (for reboot persistence)"
    echo ""
}

setup_venv() {
    echo -e "${YELLOW}📦 Setting up virtual environment...${NC}"
    
    # Create venv if needed
    if [ ! -d "$API_DIR/venv" ]; then
        echo "   Creating venv..."
        python3 -m venv "$API_DIR/venv"
    fi
    
    # Install dependencies
    echo "   Installing dependencies..."
    "$API_DIR/venv/bin/pip" install -q -r "$API_DIR/requirements.txt"
    
    # Create logs directory
    mkdir -p "$API_DIR/logs"
    
    echo -e "${GREEN}✅ Setup complete${NC}"
}

# PM2: global или локальный из node_modules
get_pm2() {
    if command -v pm2 &>/dev/null; then
        echo "pm2"
        return
    fi
    if [ -f "$MLS2_ROOT/node_modules/.bin/pm2" ]; then
        echo "$MLS2_ROOT/node_modules/.bin/pm2"
        return
    fi
    return 1
}

check_health() {
    echo "Checking API health..."
    [ -f "$MLS2_ROOT/.env" ] && set -a && source "$MLS2_ROOT/.env" 2>/dev/null && set +a
    local port="${RESO_API_PORT:-3900}"
    local proto="http"
    if [ -n "$RESO_SSL_CERTFILE" ] && [ -n "$RESO_SSL_KEYFILE" ] && [ -f "$RESO_SSL_CERTFILE" ] 2>/dev/null; then
        proto="https"
    fi
    local response
    response=$(curl -sS --connect-timeout 5 "${proto}://127.0.0.1:${port}/health" 2>/dev/null) || response=""
    # Server may be HTTPS-only (e.g. PM2 started with cert paths not mirrored in this .env)
    if ! echo "$response" | grep -q "healthy"; then
        response=$(curl -skS --connect-timeout 5 "https://127.0.0.1:${port}/health" 2>/dev/null) || response=""
    fi
    [ -n "$response" ] || response="error"
    
    if echo "$response" | grep -q "healthy"; then
        echo -e "${GREEN}✅ API is healthy${NC}"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        echo -e "${RED}❌ API is not responding${NC}"
        return 1
    fi
}

case "${1:-help}" in
    start)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then
            echo -e "${RED}❌ pm2 not found. Run: cd $MLS2_ROOT && npm install${NC}"
            exit 1
        fi
        echo -e "${GREEN}🚀 Starting $APP_NAME...${NC}"
        
        if [ ! -d "$API_DIR/venv" ]; then
            echo -e "${YELLOW}⚠️  Virtual environment not found. Running setup...${NC}"
            setup_venv
        fi
        
        cd "$MLS2_ROOT"
        "$PM2_CMD" start ecosystem.config.js
        "$PM2_CMD" save
        
        echo ""
        sleep 4
        check_health
        ;;
        
    stop)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        echo -e "${YELLOW}🛑 Stopping $APP_NAME...${NC}"
        "$PM2_CMD" stop $APP_NAME
        echo -e "${GREEN}✅ Stopped${NC}"
        ;;
        
    restart)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        echo -e "${YELLOW}🔄 Restarting $APP_NAME...${NC}"
        "$PM2_CMD" restart $APP_NAME
        "$PM2_CMD" save
        
        echo ""
        sleep 4
        check_health
        ;;
        
    status)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        "$PM2_CMD" status $APP_NAME
        ;;
        
    logs)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        "$PM2_CMD" logs $APP_NAME
        ;;
        
    logs-err)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        "$PM2_CMD" logs $APP_NAME --err
        ;;
        
    setup)
        setup_venv
        ;;
        
    health)
        check_health
        ;;
        
    save)
        PM2_CMD=$(get_pm2) || true
        if [ -z "$PM2_CMD" ]; then echo -e "${RED}❌ pm2 not found${NC}"; exit 1; fi
        echo "Saving PM2 process list..."
        "$PM2_CMD" save
        echo -e "${GREEN}✅ PM2 state saved${NC}"
        ;;
        
    help|--help|-h|*)
        show_help
        ;;
esac


