#!/usr/bin/env bash
set -e

sudo service postgresql restart
sudo -u postgres psql << 'EOF'
ALTER USER postgres WITH PASSWORD 'postgres';
SELECT 1 FROM pg_database WHERE datname = 'fleet_control_tower_db';
EOF

sudo -u postgres createdb -O postgres fleet_control_tower_db || true
echo "Setup finished."
