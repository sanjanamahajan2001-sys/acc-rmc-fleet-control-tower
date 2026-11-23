"""
OpenAPI Specification Customization

Configures API title, version, contact details, servers, security schemes,
and documentation endpoints for FastAPI.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def setup_openapi(app: FastAPI) -> None:
    """
    Customizes the OpenAPI schema for Fleet Control Tower Platform.
    """

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Fleet Control Tower Platform API",
            version="1.0.0",
            description=(
                "Enterprise Operational Intelligence & Dispatch Control Tower API for Ready Mix Concrete Logistics.\n\n"
                "Governance: Master Architecture Blueprint v1.0.0 (FROZEN)."
            ),
            routes=app.routes,
        )

        openapi_schema["info"]["contact"] = {
            "name": "Lead Enterprise Solution & Architecture Team",
            "email": "architecture@fleetcontrol.internal",
        }
        openapi_schema["servers"] = [
            {"url": "http://localhost:8010", "description": "Local Development Server"},
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
