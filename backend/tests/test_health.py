"""
Unit tests for Diagnostic Health & Readiness Router
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.health import router as health_router
from app.core.middleware import CorrelationIDMiddleware

app = FastAPI()
app.add_middleware(CorrelationIDMiddleware)
app.include_router(health_router)

client = TestClient(app)


def test_health_liveness_endpoint():
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "alive"
    assert "meta" in data


def test_health_readiness_endpoint():
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ready"
    assert data["data"]["components"]["database"]["status"] == "healthy"
