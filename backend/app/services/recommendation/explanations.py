"""Per-strategy explanation, as the challenge asks: why it was suggested, what evidence
supports it, what benefits it may offer, where information gaps exist, and which risks
need local review. Built only from numbers the comparison already computed.
"""

from app.repositories.crop_profiles import CropProfileRepository
from app.schemas.crop import RiskLevel
from app.schemas.recommendation import RankedRotation, StrategyExplanation


def _name(crop) -> str:
    return crop.value.replace("_", " ")


def _crops(r: RankedRotation) -> list:
    seen = []
    for c in r.evaluation.crop_results:
        if c.crop not in seen:
            seen.append(c.crop)
    return seen


def _short_source(source: str) -> str:
    return source.split(", http")[0].split(" (")[0].strip()


def explain(r: RankedRotation, current: RankedRotation, profiles: CropProfileRepository) -> StrategyExplanation:
    crops, current_crops = _crops(r), _crops(current)
    added = [c for c in crops if c not in current_crops]
    removed = [c for c in current_crops if c not in crops]
    profs = {c: profiles.get(c) for c in crops}

    # Why
    if r.is_current:
        why = ["Your current rotation; the alternatives are compared against it."]
    else:
        why = ["An alternative you entered."]
        if added or removed:
            swap = " and ".join(_name(c) for c in added) or "nothing"
            why.append(f"Replaces {' and '.join(_name(c) for c in removed) or 'nothing'} with {swap}.")

    # Benefits versus the current rotation
    benefits: list[str] = []
    if not r.is_current:
        w, cw = r.evaluation.water, current.evaluation.water
        if w and cw and w.irrigation_need_m3 is not None and cw.irrigation_need_m3:
            diff = cw.irrigation_need_m3 - w.irrigation_need_m3
            if diff > 0:
                benefits.append(f"About {diff:,.0f} m³ less irrigation water per cycle "
                                f"({diff / cw.irrigation_need_m3:.0%} below the current rotation).")
        for c in added:
            if profs[c].is_legume:
                benefits.append(f"Adds a legume ({_name(c)}); legumes can fix atmospheric nitrogen. This is an "
                                "indicator for soil health, not proof of improvement.")
        inc, cinc = r.evaluation.income, current.evaluation.income
        if inc and cinc and inc.basis == cinc.basis:
            mine = inc.net_income if inc.basis == "net" else inc.gross_revenue
            theirs = cinc.net_income if cinc.basis == "net" else cinc.gross_revenue
            if mine is not None and theirs and mine > theirs:
                benefits.append(f"About {mine - theirs:,.0f} {inc.currency} more {inc.basis} income per cycle "
                                f"({(mine - theirs) / theirs:.0%} above the current rotation).")
        g, cg = r.evaluation.ground_cover, current.evaluation.ground_cover
        if g and cg and g.bare_soil_days < cg.bare_soil_days:
            benefits.append(f"{cg.bare_soil_days - g.bare_soil_days} fewer bare-soil days per year.")
        if (r.dimension_scores.resilience is not None and current.dimension_scores.resilience is not None
                and r.evaluation.highest_crop_season_risk < current.evaluation.highest_crop_season_risk):
            benefits.append(
                f"Lower worst-season climate risk ({r.evaluation.highest_crop_season_risk:.0f} vs "
                f"{current.evaluation.highest_crop_season_risk:.0f} on the 0-100 scale).")

    # Evidence
    evidence = [
        "Weather: NASA POWER daily data for the ~50 km grid cell (see data_note for dates).",
        "Growth stages and crop water use: FAO-56 Tables 11-12; effective rainfall: FAO Irrigation Manual 3.",
    ]
    for c in crops:
        sources = sorted({_short_source(src) for s in profs[c].stages for t in s.thresholds
                          if t.warning is not None or t.critical is not None for src in t.sources})
        if sources:
            evidence.append(f"{_name(c).capitalize()} limits: {'; '.join(sources)}.")

    # Information gaps
    gaps: list[str] = []
    if r.missing_dimensions:
        gaps.append(f"Not scored: missing {', '.join(r.missing_dimensions)} while other rotations have it.")
    inc = r.evaluation.income
    if inc is None or inc.gross_revenue is None:
        gaps.append("Income not assessed: a crop has no yield or price (enter local values).")
    elif inc.basis == "gross":
        gaps.append("Income is gross revenue only (no production costs entered).")
    if inc and any(s.yield_source and s.yield_source != "farmer" for s in inc.seasons):
        gaps.append("Yields and prices are FAOSTAT national averages, not local figures.")
    for c in r.evaluation.crop_results:
        missing = [k.value for k, v in c.levels.items() if v is None]
        if missing:
            gaps.append(f"{_name(c.crop).capitalize()}: {', '.join(missing)} not assessed.")
    if r.evaluation.water and any(s.estimated_from_history for s in r.evaluation.water.seasons):
        gaps.append("Water for future seasons is a 20-season historical median, not a forecast.")
    gaps = list(dict.fromkeys(gaps))

    # Needs local review
    review: list[str] = []
    for c in r.evaluation.crop_results:
        for risk, level in c.levels.items():
            if level == RiskLevel.HIGH:
                days = c.high_days.get(risk, 0)
                review.append(f"{_name(c.crop).capitalize()} {risk.value} reached High ({days} days): check variety "
                              "tolerance and sowing date with a local extension officer.")
    review = list(dict.fromkeys(review))
    if any(t.evidence_status.value == "provisional" for c in crops for s in profs[c].stages for t in s.thresholds):
        review.append("Crop temperature limits are provisional starting values; local agronomists should confirm them.")
    if added:
        review.append(f"Market demand, seed and equipment for {', '.join(_name(c) for c in added)}.")
    review.append("Pest and disease cycles are not modelled.")

    return StrategyExplanation(why_considered=why, benefits=benefits, evidence=evidence,
                               information_gaps=gaps, needs_local_review=review)
