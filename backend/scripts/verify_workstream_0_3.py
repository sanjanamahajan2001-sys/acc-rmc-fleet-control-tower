"""
Manual Operational Verification Script for Workstream 0.3
"""
import asyncio
from fastapi.testclient import TestClient
from app.factory import create_app

app = create_app()
client = TestClient(app)


def main():
    print("=== Workstream 0.3 Manual Operational Verification Starting ===")

    # 1. Verify Process Liveness Probe
    res_live = client.get("/api/v1/health/liveness")
    print(f"✓ GET /api/v1/health/liveness Status: {res_live.status_code}")
    live_data = res_live.json()
    assert live_data["success"] is True
    assert live_data["data"]["status"] == "alive"
    assert "meta" in live_data
    assert "request_duration_ms" in live_data["meta"]
    print(f"  Response Meta: {live_data['meta']}")

    # 2. Verify Application Readiness Probe
    res_ready = client.get("/api/v1/health/readiness")
    print(f"✓ GET /api/v1/health/readiness Status: {res_ready.status_code}")
    ready_data = res_ready.json()
    assert ready_data["success"] is True
    assert ready_data["data"]["status"] == "ready"
    assert ready_data["data"]["components"]["database"]["status"] == "healthy"
    print(f"  Readiness Data: {ready_data['data']}")

    # 3. Verify Middleware Header Propagation
    custom_headers = {"X-Correlation-ID": "manual-verify-corr-999"}
    res_headers = client.get("/api/v1/health/liveness", headers=custom_headers)
    assert res_headers.headers["X-Correlation-ID"] == "manual-verify-corr-999"
    assert "X-Request-ID" in res_headers.headers
    print("✓ RequestID & CorrelationID Header Propagation Verified")

    # 4. Verify Custom OpenAPI Generation
    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    openapi_schema = res_openapi.json()
    assert openapi_schema["info"]["title"] == "Fleet Control Tower Platform API"
    assert openapi_schema["info"]["version"] == "1.0.0"
    print(f"✓ OpenAPI Title & Version Verified: {openapi_schema['info']['title']}")

    print("=== Workstream 0.3 Manual Verification PASSED ===")


if __name__ == "__main__":
    main()
