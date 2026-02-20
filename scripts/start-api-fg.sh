#!/bin/bash
# Запуск RESO Web API в foreground (без PM2).
# Для прода: запустите в tmux/screen или через systemd.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$MLS2_ROOT/api"

if [ -f "$MLS2_ROOT/.env" ]; then
  set -a
  source "$MLS2_ROOT/.env"
  set +a
fi

if [ ! -d "$API_DIR/venv" ]; then
  echo "Creating venv and installing deps..."
  python3 -m venv "$API_DIR/venv"
  "$API_DIR/venv/bin/pip" install -q -r "$API_DIR/requirements.txt"
fi

cd "$API_DIR"
UVICORN_ARGS="main:app --host ${RESO_API_HOST:-0.0.0.0} --port ${RESO_API_PORT:-3900}"
if [ -n "$RESO_SSL_CERTFILE" ] && [ -n "$RESO_SSL_KEYFILE" ] && [ -f "$RESO_SSL_CERTFILE" ] && [ -f "$RESO_SSL_KEYFILE" ]; then
  UVICORN_ARGS="$UVICORN_ARGS --ssl-certfile $RESO_SSL_CERTFILE --ssl-keyfile $RESO_SSL_KEYFILE"
fi
exec "$API_DIR/venv/bin/uvicorn" $UVICORN_ARGS
