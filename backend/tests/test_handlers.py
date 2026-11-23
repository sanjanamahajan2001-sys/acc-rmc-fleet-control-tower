"""
Unit tests for Global Exception Handlers Translation
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import OptimisticLockError, RecordNotFoundError
from app.core.handlers import register_exception_handlers
from app.core.middleware import CorrelationIDMiddleware

app = FastAPI()
app.add_middleware(CorrelationIDMiddleware)
register_exception_handlers(app)


class DummyPayload(BaseModel):
    name: str


@app.get("/not-found")
def trigger_not_found():
    raise RecordNotFoundError("Entity 123 missing", details={"id": "123"})


@app.get("/conflict")
def trigger_conflict():
    raise OptimisticLockError("Version conflict", details={"expected": 1})


@app.post("/validate")
def trigger_val(payload: DummyPayload):
    return payload


client = TestClient(app)


def test_exception_handler_not_found():
    response = client.get("/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Entity 123 missing"


def test_exception_handler_validation_error():
    response = client.post("/validate", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
