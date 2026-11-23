"""
Thread & Async-Safe RequestContext Abstraction

Uses Python contextvars to store request-scoped variables (correlation ID,
request ID, user ID, tenant ID, plant ID, client IP, user agent, start time)
accessible across any backend layer without parameter drilling.
"""

import time
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
_tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_plant_id_var: ContextVar[str | None] = ContextVar("plant_id", default=None)
_client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
_user_agent_var: ContextVar[str | None] = ContextVar("user_agent", default=None)
_start_time_var: ContextVar[float] = ContextVar("start_time", default=0.0)


class RequestContext:
    """
    Static accessor interface for ContextVar request metadata.
    """

    @classmethod
    def init(
        cls,
        request_id: str | None = None,
        correlation_id: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        plant_id: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        req_id = request_id or str(uuid.uuid4())
        corr_id = correlation_id or req_id

        _request_id_var.set(req_id)
        _correlation_id_var.set(corr_id)
        _user_id_var.set(user_id)
        _tenant_id_var.set(tenant_id)
        _plant_id_var.set(plant_id)
        _client_ip_var.set(client_ip)
        _user_agent_var.set(user_agent)
        _start_time_var.set(time.perf_counter())

    @classmethod
    def get_request_id(cls) -> str:
        return _request_id_var.get() or str(uuid.uuid4())

    @classmethod
    def get_correlation_id(cls) -> str:
        return _correlation_id_var.get() or cls.get_request_id()

    @classmethod
    def get_user_id(cls) -> str | None:
        return _user_id_var.get()

    @classmethod
    def get_tenant_id(cls) -> str | None:
        return _tenant_id_var.get()

    @classmethod
    def get_plant_id(cls) -> str | None:
        return _plant_id_var.get()

    @classmethod
    def get_client_ip(cls) -> str | None:
        return _client_ip_var.get()

    @classmethod
    def get_user_agent(cls) -> str | None:
        return _user_agent_var.get()

    @classmethod
    def get_execution_duration_ms(cls) -> float:
        start = _start_time_var.get()
        if start <= 0.0:
            return 0.0
        return round((time.perf_counter() - start) * 1000, 2)
