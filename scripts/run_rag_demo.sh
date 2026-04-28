#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BOOTSTRAP="${PYTHON_BOOTSTRAP:-python3}"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-8501}"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

export DATASET_CSV_PATH="${DATASET_CSV_PATH:-data/raw/mediaexpert_laptops.csv}"
export CATALOG_DB_PATH="${CATALOG_DB_PATH:-data/catalog.db}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
export QDRANT_COLLECTION="${QDRANT_COLLECTION:-laptops}"
export API_URL="${API_URL:-http://${API_HOST}:${API_PORT}}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Missing OPENAI_API_KEY. Add it to .env or export it before running this script." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to start Qdrant." >&2
  exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Creating .venv..."
  "$PYTHON_BOOTSTRAP" -m venv .venv
fi

echo "Installing project dependencies..."
"$VENV_PYTHON" -m pip install -e ".[dev]"

echo "Starting Qdrant..."
docker compose -f infra/docker-compose.yml up -d

echo "Waiting for Qdrant at $QDRANT_URL..."
"$VENV_PYTHON" - <<'PY'
import os
import time
from urllib.request import urlopen

base_url = os.environ["QDRANT_URL"].rstrip("/")
last_error = None
for _ in range(60):
    try:
        with urlopen(f"{base_url}/readyz", timeout=2) as response:
            if response.status < 500:
                raise SystemExit(0)
    except Exception as exc:
        last_error = exc
    time.sleep(1)

raise SystemExit(f"Qdrant did not become ready: {last_error}")
PY

echo "Importing laptop CSV into SQLite..."
"$VENV_PYTHON" -c "from mediaexpert_laptops.rag.cli import import_catalog_main; import_catalog_main()"

if [[ "${SKIP_INDEX:-0}" == "1" ]]; then
  echo "Skipping Qdrant indexing because SKIP_INDEX=1."
else
  echo "Indexing laptops in Qdrant..."
  "$VENV_PYTHON" -c "from mediaexpert_laptops.rag.cli import index_catalog_main; index_catalog_main()"
fi

API_PID=""
cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "Stopping API process $API_PID..."
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting FastAPI at $API_URL..."
"$VENV_PYTHON" -m uvicorn mediaexpert_laptops.rag.app:app \
  --host "$API_HOST" \
  --port "$API_PORT" &
API_PID="$!"

echo "Waiting for API health..."
"$VENV_PYTHON" - <<'PY'
import os
import time
from urllib.request import urlopen

api_url = os.environ["API_URL"].rstrip("/")
last_error = None
for _ in range(60):
    try:
        with urlopen(f"{api_url}/health", timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception as exc:
        last_error = exc
    time.sleep(1)

raise SystemExit(f"API did not become ready: {last_error}")
PY

echo "Starting Streamlit UI at http://localhost:${UI_PORT}..."
"$VENV_PYTHON" -m streamlit run src/mediaexpert_laptops/rag/ui.py \
  --server.port "$UI_PORT"
