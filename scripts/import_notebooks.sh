#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# Import MLS 2.0 notebooks to Databricks workspace
# Usage: ./scripts/import_notebooks.sh
# Run from: repository root (this project) directory

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load credentials
if [ -f "$MLS2_ROOT/.env" ]; then
    set -a
    source "$MLS2_ROOT/.env"
    set +a
else
    echo "❌ Error: $MLS2_ROOT/.env not found"
    echo "   Copy .env.example to .env and fill in your values."
    exit 1
fi

NOTEBOOKS_DIR="$MLS2_ROOT/notebooks"
# Override in .env, e.g. MLS_NOTEBOOK_BASE=/mls_etl/notebooks (folder path in workspace)
WORKSPACE_PATH="${MLS_NOTEBOOK_BASE:-/Shared/mls_2_0}"

echo "📤 Importing MLS 2.0 notebooks to Databricks..."
echo "   Source: $NOTEBOOKS_DIR"
echo "   Target: $WORKSPACE_PATH (set MLS_NOTEBOOK_BASE in .env to change)"
echo ""

for notebook in "$NOTEBOOKS_DIR"/*.py; do
    if [ -f "$notebook" ]; then
        name=$(basename "$notebook" .py)
        echo "   Importing: $name"
        databricks workspace import \
            "$notebook" \
            "$WORKSPACE_PATH/$name" \
            --language PYTHON \
            --format SOURCE \
            --overwrite \
            2>&1 | grep -v "^WARN:" || true
    fi
done

echo ""
echo "✅ All notebooks imported to $WORKSPACE_PATH"

