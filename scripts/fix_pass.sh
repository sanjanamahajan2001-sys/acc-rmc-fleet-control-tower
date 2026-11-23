#!/usr/bin/env bash
set -e

sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres createdb -O postgres fleet_control_tower_db || true
echo "Postgres password and database ready."
