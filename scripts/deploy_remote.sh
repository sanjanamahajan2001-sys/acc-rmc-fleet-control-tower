#!/usr/bin/env bash
set -e

ssh -i ~/.ssh/linode_prod -o StrictHostKeyChecking=no root@192.46.210.48 << 'REMOTESCRIPT'
set -e

mkdir -p /opt/apps/demo-fleet/
tar -xzvf /opt/demo-fleet-app.tar.gz -C /opt/apps/demo-fleet/

cat << 'EOF' > /opt/apps/demo-fleet/backend/.env
PROJECT_NAME="Fleet Control Tower & Operational Intelligence Platform"
ENVIRONMENT="production"
LOG_LEVEL="INFO"

BACKEND_PORT=8010
FRONTEND_PORT=5174
POSTGRES_PORT=5432

POSTGRES_USER=fleet_admin
POSTGRES_PASSWORD=fleet_secure_pass_prod_2026
POSTGRES_DB=fleet_control_tower_db
POSTGRES_HOST=localhost

JWT_SECRET_KEY=prod_super_secret_jwt_key_fleet_control_tower_2026_32bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

STORAGE_PROVIDER=LOCAL
STORAGE_ROOT_DIR=/var/lib/fleet_control_tower/storage

fleet-control-tower-routes-dev=AIzaSyDUBdkaweiF1-JJlR2saVHmf-oOxzYB-go
fleet-control-tower-maps-js-dev=AIzaSyAfgMMioDu7f_9sgn0u0VeFaPmh6jU-eKc
GOOGLE_MAPS_ROUTES_API_KEY=AIzaSyDUBdkaweiF1-JJlR2saVHmf-oOxzYB-go
GOOGLE_MAPS_JS_API_KEY=AIzaSyAfgMMioDu7f_9sgn0u0VeFaPmh6jU-eKc
EOF

cd /opt/apps/demo-fleet/backend
venv/bin/alembic upgrade head
systemctl kill -s 9 demo-fleet-backend || true
sleep 1
systemctl start demo-fleet-backend
systemctl reload nginx
systemctl status demo-fleet-backend --no-pager

REMOTESCRIPT
