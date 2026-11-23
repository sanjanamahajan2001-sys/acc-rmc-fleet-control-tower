#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Starting Fleet Control Tower Platform in Development Mode..."

echo "1. Starting FastAPI Backend..."
(cd "$PROJECT_ROOT/backend" && ./run_backend.sh) &
BACKEND_PID=$!

echo "2. Starting Vite React Frontend..."
(cd "$PROJECT_ROOT/frontend" && ./run_frontend.sh) &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID; exit 0" INT TERM
wait
