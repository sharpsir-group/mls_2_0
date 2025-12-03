#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# =============================================================================
# RESO Web API Server
# =============================================================================
# Starts the FastAPI RESO Web API server
#
# Usage:
#   ./scripts/run_api.sh              # Start on port 8000
#   ./scripts/run_api.sh 8080         # Start on custom port
#   ./scripts/run_api.sh --dev        # Development mode with reload
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$MLS2_ROOT/api"

# Default settings
PORT="${1:-8000}"
HOST="0.0.0.0"
RELOAD=""

# Check for dev mode
if [ "$1" = "--dev" ] || [ "$2" = "--dev" ]; then
    RELOAD="--reload"
    PORT="${2:-8000}"
    [ "$1" = "--dev" ] && PORT="${2:-8000}"
fi

# Check for required files
if [ ! -f "$API_DIR/main.py" ]; then
    echo "❌ Error: API not found at $API_DIR/main.py"
    exit 1
fi

# Load environment from parent .env if exists
if [ -f "$MLS2_ROOT/.env" ]; then
    echo "📋 Loading environment from $MLS2_ROOT/.env"
    export $(grep -v '^#' "$MLS2_ROOT/.env" | xargs)
fi

# Check for Databricks credentials
if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "⚠️  Warning: DATABRICKS_HOST or DATABRICKS_TOKEN not set"
    echo "   API will fail to connect to Databricks"
    echo ""
    echo "   Set these in $MLS2_ROOT/.env or environment:"
    echo "   - DATABRICKS_HOST=your-workspace.cloud.databricks.com"
    echo "   - DATABRICKS_TOKEN=your-access-token"
    echo "   - DATABRICKS_WAREHOUSE_ID=your-warehouse-id"
    echo ""
fi

# Create virtual environment if needed
if [ ! -d "$API_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$API_DIR/venv"
fi

# Activate virtual environment
source "$API_DIR/venv/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r "$API_DIR/requirements.txt"

# Start server
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Starting RESO Web API"
echo "════════════════════════════════════════════════════════════════════"
echo "   URL:         http://$HOST:$PORT"
echo "   Docs:        http://$HOST:$PORT/docs"
echo "   OData:       http://$HOST:$PORT/odata"
echo "   Health:      http://$HOST:$PORT/health"
echo "════════════════════════════════════════════════════════════════════"
echo ""

cd "$API_DIR"
uvicorn main:app --host "$HOST" --port "$PORT" $RELOAD

