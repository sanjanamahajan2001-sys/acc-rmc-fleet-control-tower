#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ]; then
    echo "node_modules not found! Run ./setup_frontend.sh first."
    exit 1
fi

echo "Starting Vite React development server on port 5174..."
exec npm run dev -- --host 0.0.0.0 --port 5174
