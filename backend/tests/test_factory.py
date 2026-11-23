"""
Unit tests for Application Factory and OpenAPI Customization
"""

from fastapi.testclient import TestClient

from app.factory import create_app

app = create_app()
client = TestClient(app)


def test_application_factory_routes():
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_openapi_schema_generation():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Fleet Control Tower Platform API"
    assert schema["info"]["version"] == "1.0.0"
    assert "/api/v1/health/liveness" in schema["paths"]
