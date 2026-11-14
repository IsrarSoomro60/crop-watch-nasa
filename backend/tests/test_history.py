from datetime import date, timedelta

import pytest

from app.repositories.crop_profiles import get_crop_profile_repository
from app.schemas.crop import CropName, RiskType
from app.schemas.environment import DailyObservation
from app.schemas.history import WaterHistory
from app.schemas.rotation import CropSeason
from app.services.history.vulnerability import (
    complete_years,
    ols_slope,
    season_history,
    shift_season,
    summarise,
)
from app.services.water.crop_water import rotation_water

RICE = CropSeason(crop=CropName.RICE, sowing_date=date(2025, 6, 15), harvest_date=date(2025, 10, 15), area_hectares=1)


def test_shift_season_keeps_length_and_handles_leap_day():
    shifted = shift_season(RICE, 2010)
    assert shifted.sowing_date == date(2010, 6, 15)
    assert shifted.harvest_date - shifted.sowing_date == RICE.harvest_date - RICE.sowing_date
    leap = CropSeason(crop=CropName.WHEAT, sowing_date=date(2024, 2, 29), harvest_date=date(2024, 5, 1),
                      area_hectares=1)
    assert shift_season(leap, 2023).sowing_date == date(2023, 2, 28)


def test_ols_slope():
    assert ols_slope([2000, 2001, 2002], [1, 3, 5]) == pytest.approx(2.0)
    assert ols_slope([2000], [1]) is None


def test_complete_years_stop_at_latest_data():
    wheat = CropSeason(crop=CropName.WHEAT, sowing_date=date(2025, 11, 15), harvest_date=date(2026, 4, 15),
                       area_hectares=1)
    assert complete_years(wheat, 2023, 2026, date(2026, 11, 11)) == [2023, 2024, 2025]  # 2026 ends in 2027
    assert complete_years(wheat, 2023, 2026, None) == []


def _warming_weather(first_year: int, last_year: int) -> list[DailyObservation]:
    """Mild weather, plus 5 extra 36 °C days in rice mid-season for each year after 2015 (a built-in trend)."""
    obs = []
    d = date(first_year, 1, 1)
    while d <= date(last_year, 12, 31):
        tmax = 30.0
        if d.year > 2015 and date(d.year, 8, 10) <= d < date(d.year, 8, 10) + timedelta(days=5 * (d.year - 2015)):
            tmax = 36.0
        obs.append(DailyObservation(day=d, tmax_c=tmax, tmin_c=22.0, tmean_c=26.0, relative_humidity_pct=60.0,
                                    wind_speed_ms=2.0, solar_radiation_mj_m2=20.0, precipitation_mm=2.0))
        d += timedelta(days=1)
    return obs


def test_season_history_counts_high_years_trend_and_water():
    years = list(range(2006, 2026))
    h = season_history(get_crop_profile_repository(), RICE, _warming_weather(2006, 2025), years, 30.0, 120.0)
    heat = next(r for r in h.risks if r.risk == RiskType.HEAT)

    assert heat.years_assessed == 20
    assert heat.years_high == 10  # 2016-2025
    assert heat.share_high == 0.5
    assert heat.high_days_trend_per_decade > 0
    assert h.water.years_calculated == 20
    assert h.water.p80_irrigation_need_mm >= h.water.median_irrigation_need_mm > 0
    assert len(h.per_year) == 20 and h.sowing_month_day == "06-15"

    text = summarise([h])
    assert text[0].startswith("rice sown 06-15: heat reached High in 10 of 20 seasons")
    assert "more High days per decade" in text[0]


def test_future_season_uses_historical_water_median():
    future = CropSeason(crop=CropName.RICE, sowing_date=date(2027, 6, 15), harvest_date=date(2027, 10, 15),
                        area_hectares=2)
    hist = WaterHistory(years_calculated=20, median_irrigation_need_mm=1800.0, p80_irrigation_need_mm=1950.0,
                        median_crop_water_use_mm=900.0)
    profiles = {CropName.RICE: get_crop_profile_repository().get(CropName.RICE)}
    key = (future.crop, future.sowing_date, future.harvest_date)

    water = rotation_water(profiles, [future], [], 30.0, 120.0, fallback={key: hist})
    season = water.seasons[0]
    assert season.estimated_from_history and season.irrigation_need_mm == 1800.0
    assert water.irrigation_need_m3 == 1800.0 * 2 * 10
    assert any("median of 20 past seasons" in n for n in season.notes)

    assert rotation_water(profiles, [future], [], 30.0, 120.0).irrigation_need_m3 is None  # no fallback, no number


def test_future_season_risk_uses_history():
    from app.schemas.crop import RiskLevel
    from app.schemas.history import RiskHistory, SeasonHistory, SeasonYear
    from app.schemas.rotation import CropRiskResult
    from app.services.history.vulnerability import risk_from_history, typical_level

    assert typical_level([RiskLevel.LOW, RiskLevel.HIGH]) == RiskLevel.HIGH  # tie -> more severe
    assert typical_level([RiskLevel.LOW, RiskLevel.LOW, RiskLevel.HIGH]) == RiskLevel.LOW
    assert typical_level([]) is None

    blank = CropRiskResult(crop=CropName.WHEAT, sowing_date=date(2027, 11, 15), risks=dict.fromkeys(RiskType, 0.0),
                           max_risk=0.0, levels=dict.fromkeys(RiskType))
    years = [
        SeasonYear(sowing_year=2000 + i, levels={RiskType.HEAT: RiskLevel.HIGH if i < 3 else RiskLevel.LOW},
                   high_days={RiskType.HEAT: 2 if i < 3 else 0}, risk_scores={RiskType.HEAT: 6.0 if i < 3 else 0.0})
        for i in range(5)
    ]
    hist = SeasonHistory(
        crop=CropName.WHEAT, sowing_month_day="11-15", harvest_month_day="04-15", season_days=152,
        years=[y.sowing_year for y in years], per_year=years,
        risks=[RiskHistory(risk=RiskType.HEAT, years_assessed=5, years_high=3, years_moderate=0,
                           mean_risk_score=3.6, mean_high_days=1.2)],
    )
    est = risk_from_history(blank, hist)
    assert est.estimated_from_history
    assert est.risks[RiskType.HEAT] == 3.6 and est.max_risk == 3.6
    assert est.levels[RiskType.HEAT] == RiskLevel.HIGH and est.high_days[RiskType.HEAT] == 1
    assert any("mean of 5 past seasons (2000-2004)" in g for g in est.evidence_gaps)
    assert est.advice and est.advice[0].text_en.startswith("Irrigate lightly")
