"""
Workstream 0.1 Unit Tests - Configuration & Pydantic Settings Validation
"""

from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert (
        settings.PROJECT_NAME
        == "Fleet Control Tower & Operational Intelligence Platform"
    )
    assert settings.BACKEND_PORT == 8010
    assert settings.FRONTEND_PORT == 5174
    assert settings.POSTGRES_PORT == 5432
    assert settings.REDIS_PORT == 6379
    assert "postgresql+asyncpg://" in settings.ASYNC_DATABASE_URI


def test_settings_env_overrides(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("BACKEND_PORT", "9000")
    settings = Settings()
    assert settings.ENVIRONMENT == "production"
    assert settings.BACKEND_PORT == 9000
