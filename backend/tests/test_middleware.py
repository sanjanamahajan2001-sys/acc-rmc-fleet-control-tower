"""
Unit tests for Middleware Pipeline and RequestContext
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.context import RequestContext
from app.core.middleware import CorrelationIDMiddleware, RequestLoggingMiddleware

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)


@app.get("/test-endpoint")
def sample_route():
    return {
        "request_id": RequestContext.get_request_id(),
        "correlation_id": RequestContext.get_correlation_id(),
        "client_ip": RequestContext.get_client_ip(),
    }


client = TestClient(app)


def test_correlation_and_request_id_middleware():
    response = client.get(
        "/test-endpoint", headers={"X-Correlation-ID": "custom-corr-999"}
    )
    assert response.status_code == 200
    headers = response.headers
    assert "X-Request-ID" in headers
    assert headers["X-Correlation-ID"] == "custom-corr-999"

    data = response.json()
    assert data["correlation_id"] == "custom-corr-999"
    assert len(data["request_id"]) > 0
