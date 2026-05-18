#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source env/bin/activate
pip install -r requirements-hosted.txt

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

if [[ "$WORKERS" != "1" ]]; then
  echo "Warning: hosted mode uses in-memory queue/state; set UVICORN_WORKERS=1 to avoid split job state."
fi

uvicorn tubeswift.hosted_api:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
