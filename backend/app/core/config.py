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
    # SoilGrids sometimes hangs under load; soil is optional context, so give up sooner than for weather.
    soilgrids_timeout_seconds: float = 15.0
    # After SoilGrids fails, use the fallback for this long before trying the live service again.
    soilgrids_retry_after_seconds: float = 15 * 60

    crop_profiles_dir: Path = APP_DIR / "domain" / "crop_profiles"
    database_path: Path = APP_DIR.parent / "var" / "cropwatch.db"
    log_level: str = "INFO"
    sample_data_dir: Path = APP_DIR / "data" / "sample"
    # Downloaded NASA POWER and SoilGrids responses are also saved here, so they survive restarts.
    disk_cache: bool = True
    cache_dir: Path = APP_DIR.parent / "var" / "cache"
    # Download data for the demo districts in the background when the server starts.
    warm_up_demo_districts: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
