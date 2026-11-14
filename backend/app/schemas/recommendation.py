"""Recommendation / comparison schemas."""

from pydantic import BaseModel, Field

from app.schemas.crop import CropName, RiskType
from app.schemas.environment import DataNote
from app.schemas.farm import Location, Priorities
from app.schemas.income import CropEconomics
from app.schemas.rotation import Rotation, RotationEvaluation
from app.schemas.soil import SoilInfo


class ComparisonRequest(BaseModel):
    location: Location
    current: Rotation
    alternatives: list[Rotation] = Field(min_length=2)
    priorities: Priorities = Field(default_factory=Priorities)
    economics: dict[CropName, CropEconomics] = Field(
        default_factory=dict, description="Farmer's yield, price and cost per crop; FAOSTAT defaults fill gaps"
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
    dimension_scores: DimensionScores
    missing_dimensions: list[str] = Field(
        default_factory=list,
        description="Weighted dimensions other rotations have but this one lacks; score is withheld",
    )
    evaluation: RotationEvaluation
    strategy: StrategyExplanation | None = None


class Recommendation(BaseModel):
    ranked: list[RankedRotation]
    explanation: list[str]
    limitations: list[str]
    resilience_risks: list[RiskType] = Field(
        default_factory=list, description="Risk types the resilience comparison is based on"
    )
    data_note: DataNote | None = None
    soil: SoilInfo | None = None
