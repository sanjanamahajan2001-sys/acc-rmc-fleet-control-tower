from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Project Metadata
    PROJECT_NAME: str = "Fleet Control Tower & Operational Intelligence Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Networking & Ports
    BACKEND_PORT: int = Field(default=8020)
    FRONTEND_PORT: int = Field(default=5175)
    POSTGRES_PORT: int = Field(default=5432)
    REDIS_PORT: int = Field(default=6379)

    # Native PostgreSQL Connection (Linux System Service)
    POSTGRES_USER: str = Field(default="demo_fleet_admin")
    POSTGRES_PASSWORD: str = Field(default="demo_fleet_secure_pass_prod_2026")
    POSTGRES_DB: str = Field(default="demo_fleet_db")
    POSTGRES_HOST: str = Field(default="localhost")

    # Native Redis Connection (Linux System Service)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Security & Tokens
    JWT_SECRET_KEY: str = Field(
        default="super_secret_jwt_key_change_in_production_32bytes"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Storage Configuration
    STORAGE_PROVIDER: str = Field(default="LOCAL")  # Options: LOCAL, S3, AZURE
    STORAGE_ROOT_DIR: str = Field(default="/var/lib/fleet_control_tower/storage")
    MAX_UPLOAD_FILE_SIZE_BYTES: int = Field(default=524_288_000)  # 500 MB
    REPORT_ARTIFACT_RETENTION_DAYS: int = Field(default=7)  # Default 7 days retention

    # Security & Rate Limiting Configuration
    REPORT_GENERATE_RATE_LIMIT_PER_MINUTE: int = Field(default=10)
    REPORT_DOWNLOAD_RATE_LIMIT_PER_MINUTE: int = Field(default=30)
    DOWNLOAD_TOKEN_EXPIRE_MINUTES: int = Field(default=15)

    # Google Maps Platform Configuration (Backend Routes API v2 & Frontend Maps JS SDK)
    GOOGLE_MAPS_ROUTES_API_KEY: str = Field(
        default="",
        validation_alias="fleet-control-tower-routes-dev",
    )
    GOOGLE_MAPS_JS_API_KEY: str = Field(
        default="",
        validation_alias="fleet-control-tower-maps-js-dev",
    )




    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
