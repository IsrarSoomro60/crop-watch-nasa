"""Pure risk formulas (provisional, see AGENTS.md).

R_crop     = 100 * sum(w_d * s_d) / (D * w_max)
R_rotation = sum(A_i * R_i) / sum(A_i)
"""

from collections.abc import Sequence


def crop_risk(severities: Sequence[float], weights: Sequence[float], w_max: float) -> float:
    """Stage-weighted crop-season risk on a 0-100 scale."""
    if len(severities) != len(weights):
        raise ValueError("severities and weights must have the same length")
    if not severities:
        return 0.0
    if w_max <= 0:
        raise ValueError("w_max must be positive")
    weighted = sum(w * s for w, s in zip(weights, severities, strict=True))
    return 100.0 * weighted / (len(severities) * w_max)


def area_weighted_risk(risks: Sequence[float], areas: Sequence[float]) -> float:
    """Area-weighted average of crop risks across a rotation."""
    if len(risks) != len(areas):
        raise ValueError("risks and areas must have the same length")
    total_area = sum(areas)
    if total_area <= 0:
        raise ValueError("total area must be positive")
    return sum(a * r for a, r in zip(areas, risks, strict=True)) / total_area
