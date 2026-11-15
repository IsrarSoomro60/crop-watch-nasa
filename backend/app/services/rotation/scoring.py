"""Preference scoring across dimensions.

S = W_s*S_s + W_w*S_w + W_e*S_e + W_r*S_r  (provisional; see AGENTS.md)

Dimensions that cannot yet be computed (None) are dropped and the remaining
farmer weights are renormalised, so a missing input never silently counts as 0.
"""

from app.schemas.farm import Priorities
from app.schemas.recommendation import DimensionScores


def normalise_weights(priorities: Priorities) -> dict[str, float]:
    raw = priorities.model_dump()
    total = sum(raw.values())
    if total <= 0:
        return {k: 1 / len(raw) for k in raw}
    return {k: v / total for k, v in raw.items()}


def preference_score(scores: DimensionScores, priorities: Priorities) -> float | None:
    weights = normalise_weights(priorities)
    available = {k: v for k, v in scores.model_dump().items() if v is not None}
    weight_sum = sum(weights[k] for k in available)
    if not available or weight_sum == 0:
        return None
    return sum(weights[k] * v for k, v in available.items()) / weight_sum


def risk_to_resilience(highest_risk: float) -> float:
    """Map a 0-100 risk to a 0-1 resilience score (higher is better)."""
    return max(0.0, min(1.0, 1 - highest_risk / 100))
