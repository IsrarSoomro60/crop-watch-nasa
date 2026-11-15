"""Growth-stage timing: FAO-56 reference stage lengths scaled to an actual season."""

from app.schemas.crop import CropProfile, StageType


def stage_timeline(profile: CropProfile, season_days: int) -> list[StageType | None]:
    """Assign a growth stage to each season day, or None if stage lengths are unknown.

    Reference lengths (e.g. FAO-56 Table 11) are scaled proportionally to the
    actual sowing-to-harvest length, keeping each stage's share of the season.
    """
    spans = stage_spans(profile, season_days)
    if spans is None:
        return [None] * season_days
    timeline: list[StageType | None] = []
    for stage_type, start, end in spans:
        timeline.extend([stage_type] * (end - start))
    return timeline


def stage_spans(profile: CropProfile, season_days: int) -> list[tuple[StageType, int, int]] | None:
    """(stage, first day index, end index exclusive) per stage, scaled to the season; None if unknown."""
    if not profile.stages or any(s.approx_days is None for s in profile.stages):
        return None
    total = sum(s.approx_days for s in profile.stages)  # type: ignore[misc]
    spans, start, elapsed = [], 0, 0
    for stage in profile.stages:
        elapsed += stage.approx_days  # type: ignore[operator]
        end = round(elapsed * season_days / total)
        spans.append((stage.stage_type, start, end))
        start = end
    return spans
