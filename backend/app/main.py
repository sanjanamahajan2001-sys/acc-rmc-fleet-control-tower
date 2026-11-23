"""
FastAPI Application Entrypoint

Initializes the platform application instance via create_app() factory.
Contains zero business logic or routing scaffolding.
"""

from app.factory import create_app

app = create_app()
