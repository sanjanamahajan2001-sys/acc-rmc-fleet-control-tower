#!/bin/bash
cd /home/sanjana/demo-fleet/backend
source venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8020
