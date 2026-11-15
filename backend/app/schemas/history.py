"""Historical vulnerability schemas (phase 6)."""

from pydantic import BaseModel, Field

from app.schemas.crop import CropName, RiskLevel, RiskType
from app.schemas.environment import DataNote
from app.schemas.farm import Location
from app.schemas.rotation import CropSeason


class HistoryRequest(BaseModel):
    location: Location
    seasons: list[CropSeason] = Field(
        min_length=1, description="Only month and day of sowing/harvest are used; each is replayed in past years"
    )
    start_year: int | None = Field(default=None, ge=1981, description="First sowing year (default: 20 years back)")
    end_year: int | None = Field(default=None, description="Last sowing year (default: latest complete season)")


class SeasonYear(BaseModel):
    sowing_year: int
    levels: dict[RiskType, RiskLevel | None]
    high_days: dict[RiskType, int]
    risk_scores: dict[RiskType, float]
    irrigation_need_mm: float | None = None


class RiskHistory(BaseModel):
    risk: RiskType
    years_assessed: int
    years_high: int = Field(description="Seasons with at least one High day")
    years_moderate: int = Field(description="Seasons whose worst level was Moderate")
    share_high: float | None = Field(default=None, description="years_high / years_assessed")
    mean_high_days: float | None = None
    mean_risk_score: float | None = None
    high_days_trend_per_decade: float | None = Field(
        default=None, description="Linear (OLS) slope of High days per season, per 10 years; descriptive only"
    )


class WaterHistory(BaseModel):
    years_calculated: int
    median_irrigation_need_mm: float
    p80_irrigation_need_mm: float = Field(description="Exceeded in about 1 season in 5")
    median_crop_water_use_mm: float


class SeasonHistory(BaseModel):
    crop: CropName
    sowing_month_day: str = Field(description="MM-DD")
    harvest_month_day: str
    season_days: int
    years: list[int]
    risks: list[RiskHistory]
    water: WaterHistory | None = None
    per_year: list[SeasonYear]
    notes: list[str] = Field(default_factory=list)


class HistoryResult(BaseModel):
    location: Location
    start_year: int
    end_year: int
    seasons: list[SeasonHistory]
    summary: list[str] = Field(description="Plain-language findings, most frequent risks first")
    method: list[str]
    data_note: DataNote
