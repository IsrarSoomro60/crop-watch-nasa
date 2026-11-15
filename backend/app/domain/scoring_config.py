"""Scoring configuration.

These are PROVISIONAL engineering choices (see AGENTS.md "Example scoring
proposal"), not validated agricultural coefficients. Keep them here, in one
place, so they are easy to revise and to show to users as assumptions.
"""

from app.schemas.crop import StageType

PROVISIONAL_NOTE = (
    "Severity levels and growth-stage weights are provisional engineering choices, "
    "not validated agricultural coefficients."
)

# Daily severity levels.
SEVERITY_NONE = 0.0
SEVERITY_WARNING = 0.5
SEVERITY_CRITICAL = 1.0

# Growth-stage weights.
STAGE_WEIGHTS: dict[StageType, float] = {
    StageType.ESTABLISHMENT: 1.25,
    StageType.VEGETATIVE: 1.0,
    StageType.FLOWERING: 2.0,
    StageType.GRAIN_FILLING: 1.75,
    # FAO-56 mid-season spans flowering (2.0) and grain filling (1.75); use the higher weight.
    StageType.REPRODUCTIVE: 2.0,
    StageType.MATURITY: 1.0,
}

# Weight used when stage timing for a day is unknown.
DEFAULT_STAGE_WEIGHT = STAGE_WEIGHTS[StageType.VEGETATIVE]
