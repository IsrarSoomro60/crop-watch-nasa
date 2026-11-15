"""Recommendation / comparison schemas."""

from pydantic import BaseModel, Field

from app.schemas.crop import CropName, RiskType
from app.schemas.environment import DataNote
from app.schemas.farm import Location, Priorities
from app.schemas.income import CropEconomics
from app.schemas.rotation import Rotation, RotationEvaluation
from app.schemas.satellite import RegionalWater
from app.schemas.soil import SoilInfo


class ClimateScenario(BaseModel):
    """'What if' adjustment applied to the observed weather before scoring. A sensitivity test, not a projection."""

    temperature_change_c: float = Field(
        default=0.0, ge=-5, le=5, description="Added to daily mean, max and min temperature"
    )
    rainfall_change_pct: float = Field(
        default=0.0, ge=-80, le=80, description="Daily rainfall scaled by (1 + pct/100)"
    )

    @property
    def is_neutral(self) -> bool:
        return self.temperature_change_c == 0 and self.rainfall_change_pct == 0


class ComparisonRequest(BaseModel):
    location: Location
    current: Rotation
    alternatives: list[Rotation] = Field(min_length=2)
    priorities: Priorities = Field(default_factory=Priorities)
    economics: dict[CropName, CropEconomics] = Field(
        default_factory=dict, description="Farmer's yield, price and cost per crop; FAOSTAT defaults fill gaps"
    )
    scenario: ClimateScenario | None = Field(
        default=None, description="Optional hotter/cooler, wetter/drier test of the same seasons"
    )


class DimensionScores(BaseModel):
    """Normalised 0-1 scores (higher is better). None = not yet computable."""

    soil_health: float | None = None
    water: float | None = None
    income: float | None = None
    resilience: float | None = None


class StrategyExplanation(BaseModel):
    """What the challenge asks for each strategy."""

    why_considered: list[str]
    benefits: list[str] = Field(description="Versus the current rotation; empty for the current one")
    evidence: list[str]
    information_gaps: list[str]
    needs_local_review: list[str]


class RankedRotation(BaseModel):
    rotation_name: str
    is_current: bool
    preference_score: float | None
    partial: bool = Field(
        default=False,
        description="True when the score leaves out missing_dimensions (weights re-normalised over the rest)",
    )
    dimension_scores: DimensionScores
    missing_dimensions: list[str] = Field(
        default_factory=list,
        description="Weighted dimensions other rotations have but this one lacks; left out of a partial score",
    )
    evaluation: RotationEvaluation
    strategy: StrategyExplanation | None = None


class RainSource(BaseModel):
    """Which rain the comparison used: GPM IMERG satellite rain where saved, otherwise NASA POWER."""

    source: str = Field(description='"gpm" or "power"')
    district: str | None = None
    days_total: int = 0
    days_gpm: int = 0
    days_late: int = Field(default=0, description="GPM days from the Late run (not gauge-calibrated)")
    gpm_total_mm: float | None = None
    power_total_mm: float | None = Field(default=None, description="POWER rain over the same days, for comparison")
    difference_pct: float | None = Field(default=None, description="(GPM - POWER) / POWER over the GPM days")
    message: str


class Recommendation(BaseModel):
    ranked: list[RankedRotation]
    rain_source: RainSource | None = None
    explanation: list[str]
    limitations: list[str]
    resilience_risks: list[RiskType] = Field(
        default_factory=list, description="Risk types the resilience comparison is based on"
    )
    data_note: DataNote | None = None
    soil: SoilInfo | None = None
    regional_water: RegionalWater | None = Field(
        default=None, description="GRACE regional water-storage trend; context only, not scored"
    )
