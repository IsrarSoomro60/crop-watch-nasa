"""Quick check: current risk for one crop from the last 7 days of NASA POWER weather.

Rule from the research brief (section 2): each day is Low inside the optimal range,
Moderate beyond it, High at or beyond the critical limit; a risk is also High when
Moderate lasts 3 or more days in a row. The overall badge is the worst single risk.
"""

from datetime import date

from app.domain import scoring_config as cfg
from app.repositories.advice import AdviceRepository
from app.schemas.crop import CropProfile, RiskLevel, RiskType, StageType, Threshold
from app.schemas.environment import DailyObservation, DataNote
from app.schemas.quick_check import DayStrip, QuickCheckRequest, QuickCheckResult, RiskCard
from app.services.risk.risk_engine import _HIGH_IS_BAD, daily_severity, season_wide_thresholds

WINDOW_DAYS = 7
MODERATE_RUN_FOR_HIGH = 3
MAX_CARDS = 3

_LABELS = {
    "tmax_c": ("Max temperature", "°C"), "tmin_c": ("Min temperature", "°C"), "tmean_c": ("Mean temperature", "°C"),
    "precipitation_mm": ("Rain", " mm"), "relative_humidity_pct": ("Humidity", "%"),
    "soil_moisture": ("Root-zone soil wetness", ""),
}


def current_stage(profile: CropProfile, request: QuickCheckRequest, today: date) -> tuple[StageType | None, str]:
    if request.stage is not None:
        return request.stage, "stage picked by the farmer"
    if request.sowing_date is None:
        return None, "no sowing date or stage given"
    if any(s.approx_days is None for s in profile.stages):
        return None, "stage lengths unknown for this crop"
    elapsed = (today - request.sowing_date).days
    if elapsed < 0:
        return None, "sowing date is in the future"
    total = 0
    for s in profile.stages:
        total += s.approx_days  # type: ignore[operator]
        if elapsed < total:
            return s.stage_type, f"day {elapsed + 1} after sowing, FAO-56 reference stage lengths"
    return None, f"day {elapsed + 1} after sowing is past the {total}-day reference season"


def thresholds_for(profile: CropProfile, stage: StageType | None) -> dict[RiskType, Threshold]:
    if stage is not None:
        for s in profile.stages:
            if s.stage_type == stage:
                return {t.risk: t for t in s.thresholds if t.warning is not None or t.critical is not None}
        return {}
    shared, _ = season_wide_thresholds(profile)
    return shared


def _reason(
    profile: CropProfile, risk: RiskType, t: Threshold, value: float, day: date, stage: StageType | None
) -> str:
    label, unit = _LABELS.get(t.variable, (t.variable, ""))
    high_bad = risk in _HIGH_IS_BAD
    limit = t.critical if t.critical is not None and (value >= t.critical if high_bad else value <= t.critical) \
        else t.warning
    word = "above" if high_bad else "below"
    where = f" at the {stage.value.replace('_', ' ')} stage" if stage else ""
    return (f"{label} {round(value, 1):g}{unit} on {day:%d %b} is {word} the {profile.display_name.lower()} "
            f"limit of {limit:g}{unit}{where}.")


def quick_check(
    profile: CropProfile,
    request: QuickCheckRequest,
    observations: list[DailyObservation],
    data_note: DataNote,
    advice: AdviceRepository,
) -> QuickCheckResult:
    today = data_note.latest_observation_date or date.today()
    stage, basis = current_stage(profile, request, today)
    limits = thresholds_for(profile, stage)
    recent = [o for o in observations if o.tmax_c is not None][-WINDOW_DAYS:]

    cards: list[RiskCard] = []
    levels: dict[RiskType, RiskLevel | None] = {}
    for risk in RiskType:
        t = limits.get(risk)
        values = [(o.day, getattr(o, t.variable)) for o in recent if getattr(o, t.variable) is not None] if t else []
        if not values:
            levels[risk] = None
            continue
        sev = [daily_severity(v, t, risk) for _, v in values]
        run = best_run = 0
        for s in sev:
            run = run + 1 if s == cfg.SEVERITY_WARNING else 0
            best_run = max(best_run, run)
        if cfg.SEVERITY_CRITICAL in sev or best_run >= MODERATE_RUN_FOR_HIGH:
            level = RiskLevel.HIGH
        elif cfg.SEVERITY_WARNING in sev:
            level = RiskLevel.MODERATE
        else:
            level = RiskLevel.LOW
        levels[risk] = level
        if level != RiskLevel.LOW:
            worst = max(range(len(values)), key=lambda i: (sev[i], values[i][1] if risk in _HIGH_IS_BAD
                                                            else -values[i][1]))
            reason = _reason(profile, risk, t, values[worst][1], values[worst][0], stage)
            if level == RiskLevel.HIGH and cfg.SEVERITY_CRITICAL not in sev:
                reason += f" Moderate for {best_run} days in a row."
            cards.append(RiskCard(risk=risk, level=level, reason=reason, days_beyond_limit=sum(1 for s in sev if s)))

    cards.sort(key=lambda c: (c.level != RiskLevel.HIGH, -c.days_beyond_limit))
    assessed = [lvl for lvl in levels.values() if lvl is not None]
    order = [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH]
    notes = []
    if stage is None:
        notes.append("Give a sowing date or pick a stage for stage-specific limits; only limits that are the same "
                     "in every stage were checked.")
    if not recent:
        notes.append("No recent weather available for this location.")
    return QuickCheckResult(
        crop=profile.crop,
        stage=stage,
        stage_basis=basis,
        overall=max(assessed, key=order.index) if assessed else None,
        cards=cards[:MAX_CARDS],
        not_assessed=[r for r, lvl in levels.items() if lvl is None],
        advice=advice.tips(profile.crop, levels),
        last_7_days=[DayStrip(day=o.day, tmax_c=o.tmax_c, tmin_c=o.tmin_c, precipitation_mm=o.precipitation_mm,
                              soil_moisture=o.soil_moisture) for o in recent],
        data_note=data_note,
        notes=notes,
    )
