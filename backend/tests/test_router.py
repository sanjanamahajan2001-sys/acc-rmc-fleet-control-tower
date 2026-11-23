"""
Unit tests for API Router Registration Architecture
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import main_router

app = FastAPI()
app.include_router(main_router)
client = TestClient(app)


def test_api_router_v1_health_registration():
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
