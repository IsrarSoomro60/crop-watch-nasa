"""Rotation schemas."""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.schemas.crop import CropName, RiskLevel, RiskType


class CropSeason(BaseModel):
    crop: CropName
    sowing_date: date
    harvest_date: date
    area_hectares: float = Field(gt=0)

    @model_validator(mode="after")
    def _harvest_after_sowing(self) -> "CropSeason":
        if self.harvest_date <= self.sowing_date:
            raise ValueError(
                f"{self.crop.value}: harvest date {self.harvest_date} must be after sowing date {self.sowing_date}"
            )
        return self


class Rotation(BaseModel):
    name: str
    seasons: list[CropSeason] = Field(min_length=1)
    is_current: bool = False


class AdviceTip(BaseModel):
    risk: RiskType
    level: RiskLevel
    text_en: str
    text_ur: str | None = Field(default=None, description="Urdu text")
    ur_reviewed: bool = Field(
        default=False,
        description="False = draft translation, not yet checked by a native speaker",
    )
    source: str


class CropRiskResult(BaseModel):
    crop: CropName
    sowing_date: date
    risks: dict[RiskType, float] = Field(description="Per-risk score 0-100")
    max_risk: float
    levels: dict[RiskType, RiskLevel | None] = Field(
        description="Worst daily level per risk; null when the risk could not be assessed"
    )
    high_days: dict[RiskType, int] = Field(default_factory=dict, description="Days at High per risk")
    moderate_days: dict[RiskType, int] = Field(default_factory=dict, description="Days at Moderate per risk")
    advice: list[AdviceTip] = Field(default_factory=list, description="Up to three tips")
    estimated_from_history: bool = Field(
        default=False, description="Future season: typical risk from past seasons, not this season's weather"
    )
    evidence_gaps: list[str] = Field(default_factory=list)


class SeasonWater(BaseModel):
    """Water balance for one crop-season, mm over the season (null = not calculated)."""

    crop: CropName
    sowing_date: date
    area_hectares: float
    et0_mm: float | None = None
    crop_water_use_mm: float | None = Field(default=None, description="ETc = Kc x ETo")
    rainfall_mm: float | None = None
    effective_rainfall_mm: float | None = None
    paddy_extra_mm: float | None = None
    irrigation_need_mm: float | None = None
    estimated_from_history: bool = Field(
        default=False, description="True when the season has no weather yet and the historical median is used"
    )
    notes: list[str] = Field(default_factory=list)


class RotationWater(BaseModel):
    seasons: list[SeasonWater]
    irrigation_need_m3: float | None = Field(
        default=None, description="Sum of irrigation need x area over the whole cycle; null if any season failed"
    )
    irrigation_need_m3_per_year: float | None = Field(
        default=None, description="irrigation_need_m3 / cycle_years: the value rotations are compared on"
    )
    method: list[str] = Field(default_factory=list)


class GroundCover(BaseModel):
    """Crop cover over one year from the first sowing (growing crops only)."""

    cycle_start: date
    cycle_end: date
    bare_soil_days: int = Field(description="Days with no crop on any part of the farm, over the whole cycle")
    cover_fraction: float = Field(description="Share of farm area x days under a growing crop, 0-1")
    cycle_years: int = Field(default=1, description="Length of the rotation cycle in years")
    bare_soil_days_per_year: float = Field(default=0.0, description="bare_soil_days / cycle_years")


class RotationEvaluation(BaseModel):
    rotation_name: str
    crop_results: list[CropRiskResult]
    area_weighted_risk: dict[RiskType, float]
    highest_crop_season_risk: float
    cycle_years: int = Field(default=1, description="Rotation cycle length; water, income, bare soil are per year")
    water: RotationWater | None = None
    ground_cover: GroundCover | None = None
    income: "RotationIncome | None" = None
    assumptions: list[str] = Field(default_factory=list)


from app.schemas.income import RotationIncome  # noqa: E402

RotationEvaluation.model_rebuild()
