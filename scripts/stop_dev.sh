#!/usr/bin/env bash
echo "Stopping Fleet Control Tower development servers..."

pkill -f "uvicorn app.main:app" || true
pkill -f "vite" || true

echo "All development servers stopped."
