from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Opportunity Finder API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"

    khmdhs_base_url: AnyHttpUrl = "https://cerpp.eprocurement.gov.gr"
    khmdhs_verify_ssl: bool = True
    khmdhs_timeout_seconds: float = 18

    ted_base_url: AnyHttpUrl = "https://api.ted.europa.eu"
    ted_timeout_seconds: float = 18

    diavgeia_base_url: AnyHttpUrl = "https://diavgeia.gov.gr/opendata"
    diavgeia_timeout_seconds: float = 18

    gemi_base_url: AnyHttpUrl = "https://opendata-api.businessportal.gr"
    gemi_api_key: str | None = Field(default=None, repr=False)
    gemi_timeout_seconds: float = 18

    market_refresh_enabled: bool = True
    market_refresh_hour: int = Field(default=7, ge=0, le=23)
    market_refresh_interval_hours: int = Field(default=24, ge=1, le=168)
    market_daily_overlap_days: int = Field(default=14, ge=1, le=180)
    market_initial_backfill_days: int = Field(default=730, ge=14, le=1800)
    market_user_agent: str = "OpportunityFinder-MarketRadar/1.0"

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-4.1-mini"
    software_screening_model: str = "gpt-4o-mini"
    software_screening_deep_model: str = "gpt-4.1-mini"

    auth_required: bool = False
    auth_username: str = "admin"
    auth_password_hash: str | None = Field(default=None, repr=False)
    auth_secret_key: str | None = Field(default=None, repr=False)
    auth_session_hours: int = Field(default=12, ge=1, le=168)
    auth_cookie_name: str = Field(default="opportunity_session", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    auth_cookie_secure: bool = False

    bookmark_db_path: Path = Path("data/opportunity_finder.sqlite3")

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / ".env.local",
            BACKEND_DIR / ".env",
            BACKEND_DIR / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if not self.auth_required:
            raise ValueError("AUTH_REQUIRED must be true in production")
        if not self.auth_password_hash:
            raise ValueError("AUTH_PASSWORD_HASH is required in production")
        if not self.auth_secret_key or len(self.auth_secret_key) < 32:
            raise ValueError("AUTH_SECRET_KEY must contain at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
