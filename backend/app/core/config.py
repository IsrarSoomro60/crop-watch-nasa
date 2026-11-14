"""Application settings loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Crop-Watch AI"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # NASA POWER (daily agroclimatology) is a keyless public API; Earthdata token is
    # only needed for datasets that require authentication.
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    nasa_earthdata_token: str | None = None
    # Used only by scripts/fetch_appeears.py (AppEEARS logs in with username + password).
    earthdata_username: str | None = None
    earthdata_password: str | None = None
    http_timeout_seconds: float = 30.0
    # Recent POWER days are revised nightly, so cached responses expire.
    nasa_cache_ttl_seconds: int = 6 * 60 * 60
    soilgrids_base_url: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    crop_profiles_dir: Path = APP_DIR / "domain" / "crop_profiles"
    sample_data_dir: Path = APP_DIR / "data" / "sample"


@lru_cache
def get_settings() -> Settings:
    return Settings()
