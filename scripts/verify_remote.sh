#!/usr/bin/env bash
set -e

ssh -i ~/.ssh/linode_prod -o StrictHostKeyChecking=no root@192.46.210.48 << 'VERIFY'
echo "=== 1. Google Maps JS Config ==="
curl -s http://127.0.0.1:8020/demo-api/v1/dispatch-analysis/route-analysis/maps-config
echo -e "\n=== 2. Google API Usage & Allowance ==="
curl -s http://127.0.0.1:8020/demo-api/v1/dispatch-analysis/route-analysis/api-usage
echo -e "\n=== 3. Batch Context ==="
curl -s http://127.0.0.1:8020/demo-api/v1/dispatch-analysis/route-analysis/batch-context
echo -e "\n=== 4. Backend Service Status ==="
systemctl is-active demo-fleet-backend
echo -e "=== 5. Nginx Status ==="
systemctl is-active nginx
VERIFY
