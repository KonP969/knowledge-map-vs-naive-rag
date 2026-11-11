#!/usr/bin/env bash
# Start the backend (uvicorn :8000) and frontend (vite :5173) together.
# Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f backend/.env ]; then
  echo "backend/.env not found — copy backend/.env.example to backend/.env and add your OPENAI_API_KEY" >&2
  exit 1
fi
if ! grep -qE '^OPENAI_API_KEY=sk-' backend/.env; then
  echo "warning: OPENAI_API_KEY does not look set in backend/.env — ingest and chat will fail" >&2
fi

# Prefer the project venv so a fresh terminal (venv not activated) still works.
PYTHON=python
for p in backend/.venv/bin/python backend/.venv/Scripts/python.exe; do
  if [ -x "$p" ]; then PYTHON="$PWD/$p"; break; fi
done
if [ "$PYTHON" = python ]; then
  echo "warning: backend/.venv not found — falling back to 'python' on PATH (see README, Setup step 1)" >&2
fi

trap 'kill 0' EXIT
( cd backend  && exec "$PYTHON" -m uvicorn main:app --port 8000 ) &
( cd frontend && exec npm run dev ) &

echo "backend  -> http://localhost:8000  (API docs: http://localhost:8000/docs)"
echo "frontend -> http://localhost:5173"
echo "Ctrl+C stops both."
wait
