from datetime import date

import pytest

from app.schemas.crop import CropName, RiskLevel, RiskType
from app.schemas.rotation import CropSeason
from app.services.risk.risk_calculator import area_weighted_risk, crop_risk
from app.services.risk.risk_engine import RiskEngine, apply_min_duration, stage_timeline

from .conftest import make_observations


def test_crop_risk_formula():
    # 100 * (1*1 + 2*0.5) / (2 * 2) = 50
    assert crop_risk([1.0, 0.5], [1.0, 2.0], w_max=2.0) == pytest.approx(50.0)


def test_crop_risk_empty_season_is_zero():
    assert crop_risk([], [], w_max=2.0) == 0.0


def test_area_weighted_risk():
    assert area_weighted_risk([10.0, 40.0], [3.0, 1.0]) == pytest.approx(17.5)


def test_min_duration_drops_short_runs():
    assert apply_min_duration([1, 1, 0, 1, 1, 1], 3) == [0, 0, 0, 1, 1, 1]


def test_engine_weights_flowering_heat_more(heat_profile):
    start = date(2026, 1, 1)
    season = CropSeason(crop=CropName.RICE, sowing_date=start, harvest_date=date(2026, 1, 10), area_hectares=1)
    engine = RiskEngine()

    hot_veg = engine.assess(heat_profile, season, make_observations(start, [36] * 5 + [20] * 5))
    hot_flower = engine.assess(heat_profile, season, make_observations(start, [20] * 5 + [36] * 5))

    assert hot_veg.risks[RiskType.HEAT] == pytest.approx(25.0)  # 100*5*1.0/(10*2)
    assert hot_flower.risks[RiskType.HEAT] == pytest.approx(50.0)  # 100*5*2.0/(10*2)
    assert hot_flower.max_risk == hot_flower.risks[RiskType.HEAT]



def _season(crop: CropName, start: date, end: date) -> CropSeason:
    return CropSeason(crop=crop, sowing_date=start, harvest_date=end, area_hectares=1)


def _profile(crop: CropName):
    from app.repositories.crop_profiles import get_crop_profile_repository

    return get_crop_profile_repository().get(crop)


def test_severity_bands_follow_brief_rule(heat_profile):
    from app.services.risk.risk_engine import daily_severity

    heat = heat_profile.stages[0].thresholds[0]  # warning 30, critical 35
    assert daily_severity(30.0, heat, RiskType.HEAT) == 0.0  # at optimal edge = Low
    assert daily_severity(30.1, heat, RiskType.HEAT) == 0.5  # beyond optimal = Moderate
    assert daily_severity(35.0, heat, RiskType.HEAT) == 1.0  # at critical = High


@pytest.mark.parametrize(
    ("crop", "season_days", "expected"),
    [
        (CropName.RICE, 150, [30, 30, 60, 30]),  # FAO-56 lengths used as-is
        (CropName.RICE, 75, [15, 15, 30, 15]),  # scaled down, same shares
        (CropName.WHEAT, 120, [18, 26, 47, 29]),  # 165 reference days scaled to 120
    ],
)
def test_stage_timeline_scales_fao56_lengths(crop, season_days, expected):
    from collections import Counter

    timeline = stage_timeline(_profile(crop), season_days)
    counts = Counter(timeline)
    assert len(timeline) == season_days
    assert [counts[s.stage_type] for s in _profile(crop).stages] == expected


def test_wheat_heat_scored_by_stage_with_advice():
    start, end = date(2025, 11, 15), date(2026, 4, 28)  # 165 days = FAO-56 reference length
    tmax = [20.0] * 165
    tmax[30] = 26.0  # development stage: above optimal 25 -> Moderate (weight 1.0)
    tmax[70] = 33.0  # mid-season: at/above critical 32 -> High (weight 2.0)
    tmax[140] = 40.0  # late season: no limits yet -> not assessed
    result = RiskEngine().assess(_profile(CropName.WHEAT), _season(CropName.WHEAT, start, end),
                                 make_observations(start, tmax))

    assert result.levels[RiskType.HEAT] == RiskLevel.HIGH
    assert result.risks[RiskType.HEAT] == round(100 * (0.5 * 1.0 + 1.0 * 2.0) / (165 * 2.0), 2)
    assert result.levels[RiskType.COLD] is None  # no tmin observations supplied
    assert result.advice[0].text_en == "Irrigate lightly to cool the crop."
    assert all(t.text_ur is None for t in result.advice)
    assert any("heat: no limits for stage(s) maturity" in g for g in result.evidence_gaps)
    assert any("FAO-56 Table 11" in g for g in result.evidence_gaps)


def test_unknown_stage_lengths_fall_back_to_shared_limits(heat_profile):
    # Same heat limit in every stage, but no lengths -> applied season-wide.
    for s in heat_profile.stages:
        s.approx_days = None
    start = date(2026, 1, 1)
    result = RiskEngine().assess(heat_profile, _season(CropName.RICE, start, date(2026, 1, 4)),
                                 make_observations(start, [29, 31, 36, 20]))
    assert result.levels[RiskType.HEAT] == RiskLevel.HIGH
    assert any("Stage durations unknown" in g for g in result.evidence_gaps)
    assert any("Applied season-wide" in g for g in result.evidence_gaps)

    # Differing limits across stages -> not assessed.
    heat_profile.stages[1].thresholds[0] = heat_profile.stages[1].thresholds[0].model_copy(update={"critical": 40.0})
    result = RiskEngine().assess(heat_profile, _season(CropName.RICE, start, date(2026, 1, 4)),
                                 make_observations(start, [29, 31, 36, 20]))
    assert result.levels[RiskType.HEAT] is None
    assert any("Not assessed" in g and "heat" in g for g in result.evidence_gaps)


def test_berseem_has_no_stage_lengths_and_reports_gaps():
    result = RiskEngine().assess(_profile(CropName.BERSEEM),
                                 _season(CropName.BERSEEM, date(2025, 11, 1), date(2025, 11, 5)), [])
    assert all(v == 0 for v in result.risks.values())
    assert any("Stage durations unknown" in g for g in result.evidence_gaps)
    assert any("No environmental observations" in g for g in result.evidence_gaps)
