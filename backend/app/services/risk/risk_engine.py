"""Assesses per-risk crop-season risk from daily observations and a crop profile.

Each risk type is scored separately so a combined value never hides a severe
individual risk. When a threshold or stage timing is not sourced, the engine
does not guess: it leaves that risk unassessed and records an evidence gap.

Daily rule (research brief section 2): inside the optimal range = Low; beyond
the optimal edge (`warning`) = Moderate; at or beyond the critical limit = High.
"""

from collections import defaultdict
from datetime import timedelta

from app.domain import scoring_config as cfg
from app.repositories.advice import AdviceRepository, get_advice_repository
from app.schemas.crop import CropProfile, RiskLevel, RiskType, StageType, Threshold
from app.schemas.environment import DailyObservation
from app.schemas.rotation import CropRiskResult, CropSeason
from app.services.risk.risk_calculator import crop_risk

# Risks where a HIGH value is harmful; the others (cold, drought) are harmful when LOW.
_HIGH_IS_BAD = {RiskType.HEAT, RiskType.WATERLOGGING, RiskType.DISEASE}

_LEVEL_BY_SEVERITY = {
    cfg.SEVERITY_NONE: RiskLevel.LOW,
    cfg.SEVERITY_WARNING: RiskLevel.MODERATE,
    cfg.SEVERITY_CRITICAL: RiskLevel.HIGH,
}


def daily_severity(value: float | None, threshold: Threshold, risk: RiskType) -> float:
    if value is None:
        return cfg.SEVERITY_NONE
    high_bad = risk in _HIGH_IS_BAD
    c, w = threshold.critical, threshold.warning
    if c is not None and (value >= c if high_bad else value <= c):
        return cfg.SEVERITY_CRITICAL
    if w is not None and (value > w if high_bad else value < w):
        return cfg.SEVERITY_WARNING
    return cfg.SEVERITY_NONE


def apply_min_duration(severities: list[float], min_days: int | None) -> list[float]:
    """Keep only flagged runs that last at least `min_days` consecutive days."""
    if not min_days or min_days <= 1:
        return severities
    result = [0.0] * len(severities)
    start = None
    for i, s in enumerate([*severities, 0.0]):
        if s > 0 and start is None:
            start = i
        elif s == 0 and start is not None:
            if i - start >= min_days:
                result[start:i] = severities[start:i]
            start = None
    return result


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


def _has_values(t: Threshold) -> bool:
    return t.warning is not None or t.critical is not None


def season_wide_thresholds(profile: CropProfile) -> tuple[dict[RiskType, Threshold], list[RiskType]]:
    """Thresholds usable without stage timing: those identical in every stage that sets them.

    Returns (usable thresholds, risks skipped because their limits differ by stage).
    """
    by_risk: dict[RiskType, list[Threshold]] = defaultdict(list)
    for stage in profile.stages:
        for t in stage.thresholds:
            if _has_values(t):
                by_risk[t.risk].append(t)
    usable, differing = {}, []
    for risk, ts in by_risk.items():
        if len({(t.variable, t.warning, t.critical, t.min_duration_days) for t in ts}) == 1:
            usable[risk] = ts[0]
        else:
            differing.append(risk)
    return usable, differing


class RiskEngine:
    def __init__(self, advice: AdviceRepository | None = None):
        self._advice = advice or get_advice_repository()

    def assess(
        self,
        profile: CropProfile,
        season: CropSeason,
        observations: list[DailyObservation],
    ) -> CropRiskResult:
        season_days = (season.harvest_date - season.sowing_date).days + 1
        days = [season.sowing_date + timedelta(days=i) for i in range(season_days)]
        by_day = {o.day: o for o in observations}
        timeline = stage_timeline(profile, season_days)
        timing_known = bool(timeline) and timeline[0] is not None
        weights = [cfg.STAGE_WEIGHTS.get(st, cfg.DEFAULT_STAGE_WEIGHT) if st else cfg.DEFAULT_STAGE_WEIGHT
                   for st in timeline]
        w_max = max(cfg.STAGE_WEIGHTS.values())

        gaps = list(profile.evidence_gaps)
        stage_thresholds = {
            (stage.stage_type, t.risk): t for stage in profile.stages for t in stage.thresholds if _has_values(t)
        }
        season_wide: dict[RiskType, Threshold] = {}
        if timing_known:
            reference = sum(s.approx_days for s in profile.stages)  # type: ignore[misc]
            gaps.append(
                f"Growth stages placed by scaling {reference} reference days to this {season_days}-day season"
                + (f" ({profile.stage_lengths_source})" if profile.stage_lengths_source else "") + "."
            )
            stage_types = [s.stage_type for s in profile.stages]
            for risk in RiskType:
                covered = {st for (st, r) in stage_thresholds if r == risk}
                if covered and len(covered) < len(stage_types):
                    missing_stages = [st.value for st in stage_types if st not in covered]
                    gaps.append(
                        f"{risk.value}: no limits for stage(s) {', '.join(missing_stages)}; "
                        "those days are not assessed."
                    )
        else:
            season_wide, differing = season_wide_thresholds(profile)
            gaps.append("Stage durations unknown: growth-stage weights not applied.")
            if season_wide:
                gaps.append(
                    "Applied season-wide (same limit in every stage that sets one): "
                    + ", ".join(sorted(r.value for r in season_wide)) + "."
                )
            if differing:
                gaps.append(
                    "Not assessed (limits differ by stage, stage timing unknown): "
                    + ", ".join(sorted(r.value for r in differing)) + "."
                )
        missing = sum(1 for d in days if d not in by_day)
        if missing:
            gaps.append(f"No environmental observations for {missing} of {season_days} season days.")

        risks: dict[RiskType, float] = {}
        levels: dict[RiskType, RiskLevel | None] = {}
        high_days: dict[RiskType, int] = {}
        moderate_days: dict[RiskType, int] = {}
        for risk in RiskType:
            severities: list[float] = []
            min_days: int | None = None
            assessed = False
            for day, stage in zip(days, timeline, strict=True):
                threshold = stage_thresholds.get((stage, risk)) if stage else season_wide.get(risk)
                obs = by_day.get(day)
                value = getattr(obs, threshold.variable, None) if threshold and obs else None
                if threshold is None or value is None:
                    severities.append(cfg.SEVERITY_NONE)
                    continue
                assessed = True
                min_days = threshold.min_duration_days
                severities.append(daily_severity(value, threshold, risk))
            severities = apply_min_duration(severities, min_days)
            risks[risk] = round(crop_risk(severities, weights, w_max), 2)
            levels[risk] = _LEVEL_BY_SEVERITY[max(severities, default=0.0)] if assessed else None
            high_days[risk] = sum(1 for s in severities if s == cfg.SEVERITY_CRITICAL)
            moderate_days[risk] = sum(1 for s in severities if s == cfg.SEVERITY_WARNING)

        unsourced = sorted(
            {t.risk.value for s in profile.stages for t in s.thresholds} - {r.value for r in
             {t.risk for s in profile.stages for t in s.thresholds if _has_values(t)}}
        )
        if unsourced:
            gaps.append(f"No threshold values yet (risk not scored): {', '.join(unsourced)}.")

        return CropRiskResult(
            crop=profile.crop,
            sowing_date=season.sowing_date,
            risks=risks,
            max_risk=max(risks.values(), default=0.0),
            levels=levels,
            high_days=high_days,
            moderate_days=moderate_days,
            advice=self._advice.tips(profile.crop, levels),
            evidence_gaps=gaps,
        )
