"""Crop profile schemas.

Thresholds are optional on purpose: a value is only filled in when it is backed
by a cited source. Missing values are surfaced as evidence gaps, not guessed.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class CropName(StrEnum):
    WHEAT = "wheat"
    RICE = "rice"
    MAIZE = "maize"
    MUNG_BEAN = "mung_bean"
    BERSEEM = "berseem"


class StageType(StrEnum):
    ESTABLISHMENT = "establishment"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    GRAIN_FILLING = "grain_filling"
    REPRODUCTIVE = "reproductive"  # FAO-56 mid-season: flowering through most grain/pod filling
    MATURITY = "maturity"


class RiskType(StrEnum):
    HEAT = "heat"
    COLD = "cold"
    DROUGHT = "drought"
    WATERLOGGING = "waterlogging"
    DISEASE = "disease"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class EvidenceStatus(StrEnum):
    SOURCED = "sourced"
    PROVISIONAL = "provisional"
    NEEDS_RESEARCH = "needs_research"


class Threshold(BaseModel):
    """A crop/stage-specific risk threshold. Values stay null until sourced."""

    risk: RiskType
    variable: str = Field(description="Environmental variable, e.g. 'tmax_c', 'soil_moisture'")
    warning: float | None = Field(
        default=None, description="Edge of the optimal range; going strictly beyond it is a warning (Moderate)"
    )
    critical: float | None = Field(
        default=None, description="Critical limit; reaching or passing it is critical (High)"
    )
    min_duration_days: int | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.NEEDS_RESEARCH
    sources: list[str] = Field(default_factory=list)
    notes: str | None = None


class GrowthStage(BaseModel):
    name: str
    stage_type: StageType
    approx_days: int | None = Field(default=None, description="Typical duration; varies by variety and climate")
    thresholds: list[Threshold] = Field(default_factory=list)


class CropCoefficients(BaseModel):
    """FAO-56 single crop coefficients (Kc) for the initial, mid-season and end of season."""

    ini: float
    mid: float
    end: float
    source: str
    notes: str | None = None


class WaterStressParams(BaseModel):
    """FAO-56 Table 22: maximum effective rooting depth and depletion fraction for no stress."""

    zr_max_m: float
    p: float
    source: str
    notes: str | None = None


class CropProfile(BaseModel):
    crop: CropName
    display_name: str
    family: str
    is_legume: bool
    season: str = Field(description="Typical season label, e.g. 'rabi' or 'kharif'")
    stages: list[GrowthStage]
    kc: CropCoefficients | None = None
    water_stress: WaterStressParams | None = None
    water_regime: Literal["upland", "paddy"] = Field(
        default="upland", description="'paddy' adds soil soaking, percolation and water-layer needs"
    )
    stage_lengths_source: str | None = Field(
        default=None, description="Citation for approx_days; lengths are scaled to each season's length"
    )
    notes: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
