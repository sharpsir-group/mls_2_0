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

check_health() {
    echo "Checking API health..."
    local response=$(curl -s http://localhost:3900/health 2>/dev/null || echo "error")
    
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
        echo -e "${GREEN}🚀 Starting $APP_NAME...${NC}"
        
        # Check if venv exists
        if [ ! -d "$API_DIR/venv" ]; then
            echo -e "${YELLOW}⚠️  Virtual environment not found. Running setup...${NC}"
            setup_venv
        fi
        
        cd "$MLS2_ROOT"
        pm2 start ecosystem.config.js
        pm2 save
        
        echo ""
        sleep 2
        check_health
        ;;
        
    stop)
        echo -e "${YELLOW}🛑 Stopping $APP_NAME...${NC}"
        pm2 stop $APP_NAME
        echo -e "${GREEN}✅ Stopped${NC}"
        ;;
        
    restart)
        echo -e "${YELLOW}🔄 Restarting $APP_NAME...${NC}"
        pm2 restart $APP_NAME
        pm2 save
        
        echo ""
        sleep 2
        check_health
        ;;
        
    status)
        pm2 status $APP_NAME
        ;;
        
    logs)
        pm2 logs $APP_NAME
        ;;
        
    logs-err)
        pm2 logs $APP_NAME --err
        ;;
        
    setup)
        setup_venv
        ;;
        
    health)
        check_health
        ;;
        
    save)
        echo "Saving PM2 process list..."
        pm2 save
        echo -e "${GREEN}✅ PM2 state saved (will auto-start on reboot)${NC}"
        ;;
        
    help|--help|-h|*)
        show_help
        ;;
esac


