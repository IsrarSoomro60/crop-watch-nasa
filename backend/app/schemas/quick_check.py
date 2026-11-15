"""Quick check: one crop, recent weather, one risk badge (research brief, section 2)."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.crop import CropName, RiskLevel, RiskType, StageType
from app.schemas.environment import DataNote
from app.schemas.farm import Location
from app.schemas.rotation import AdviceTip


class QuickCheckRequest(BaseModel):
    location: Location
    crop: CropName
    sowing_date: date | None = Field(default=None, description="Used to estimate the current growth stage")
    stage: StageType | None = Field(default=None, description="Farmer-picked stage; overrides the sowing date")


class RiskCard(BaseModel):
    risk: RiskType
    level: RiskLevel
    reason: str = Field(description="One line with the number against the limit")
    days_beyond_limit: int


class DayStrip(BaseModel):
    day: date
    tmax_c: float | None
    tmin_c: float | None
    precipitation_mm: float | None
    soil_moisture: float | None


class QuickCheckResult(BaseModel):
    crop: CropName
    stage: StageType | None
    stage_basis: str = Field(description="How the stage was decided")
    overall: RiskLevel | None = Field(description="Worst single risk; null if nothing could be assessed")
    cards: list[RiskCard] = Field(description="Up to three, most severe first")
    assessed: list[RiskType] = Field(default_factory=list, description="Risks checked against a limit")
    not_assessed: list[RiskType]
    advice: list[AdviceTip]
    last_7_days: list[DayStrip]
    data_note: DataNote
    notes: list[str] = Field(default_factory=list)
