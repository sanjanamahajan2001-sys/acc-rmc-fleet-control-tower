"""
Additional Coverage Tests for Handlers, ContextVars & App Lifespan
"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.context import RequestContext
from app.core.exceptions import DatabaseConnectionError, DuplicateKeyError
from app.core.handlers import register_exception_handlers
from app.core.middleware import CorrelationIDMiddleware
from app.factory import create_app

app = FastAPI()
app.add_middleware(CorrelationIDMiddleware)
register_exception_handlers(app)


class CustomTestError(Exception):
    pass


@app.get("/duplicate")
def trigger_dup():
    raise DuplicateKeyError("Key already exists", details={"key": "ID1"})


@app.get("/db-conn-error")
def trigger_db_conn():
    raise DatabaseConnectionError("DB server offline")


@app.get("/http-error")
def trigger_http_err():
    raise HTTPException(status_code=403, detail="Forbidden access")


@app.get("/unhandled")
def trigger_unhandled():
    raise CustomTestError("Unhandled custom test exception")


client = TestClient(app, raise_server_exceptions=False)


def test_exception_handler_duplicate_key():
    res = client.get("/duplicate")
    assert res.status_code == 409
    data = res.json()
    assert data["error"]["code"] == "DUPLICATE_RESOURCE"


def test_exception_handler_db_connection():
    res = client.get("/db-conn-error")
    assert res.status_code == 503
    data = res.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_exception_handler_http_exception():
    res = client.get("/http-error")
    assert res.status_code == 403
    data = res.json()
    assert data["error"]["code"] == "HTTP_403"


def test_exception_handler_unhandled_exception():
    res = client.get("/unhandled")
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"


def test_context_vars_getters():
    RequestContext.init(
        user_id="U1", tenant_id="T1", plant_id="P1", user_agent="Pytest"
    )
    assert RequestContext.get_user_id() == "U1"
    assert RequestContext.get_tenant_id() == "T1"
    assert RequestContext.get_plant_id() == "P1"
    assert RequestContext.get_user_agent() == "Pytest"


def test_app_lifespan_execution():
    app_instance = create_app()
    with TestClient(app_instance) as test_c:
        res = test_c.get("/api/v1/health/liveness")
        assert res.status_code == 200
