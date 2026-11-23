#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found! Run ./setup_backend.sh first."
    exit 1
fi

source .venv/bin/activate
echo "Starting FastAPI backend server on port 8010..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
