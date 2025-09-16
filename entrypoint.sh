#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres (compose sets POSTGRES_HOST=db inside the api container)
if [[ -n "${POSTGRES_HOST:-}" ]]; then
  echo "Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  python - <<'PY'
import os, socket, time, sys
host = os.getenv("POSTGRES_HOST","127.0.0.1")
port = int(os.getenv("POSTGRES_PORT","5432"))
for _ in range(120):
    with socket.socket() as s:
        try:
            s.settimeout(1.0)
            s.connect((host, port))
            sys.exit(0)
        except Exception:
            time.sleep(1)
print("DB not reachable", file=sys.stderr)
sys.exit(1)
PY
fi

# Run Alembic migrations (env.py already converts +asyncpg → sync)
if [[ -f "alembic.ini" ]]; then
  echo "Running Alembic migrations..."
  alembic upgrade head || { echo "Alembic migration failed"; exit 1; }
fi

echo "Starting Uvicorn..."
exec python -m uvicorn app.main:app --host "${UVICORN_HOST:-0.0.0.0}" --port "${UVICORN_PORT:-8000}" --workers "${UVICORN_WORKERS:-2}"
