from datetime import date, timedelta

from app.repositories.crop_profiles import get_crop_profile_repository
from app.schemas.crop import CropName, RiskLevel, RiskType
from app.schemas.environment import DailyObservation
from app.schemas.rotation import CropSeason
from app.services.risk.risk_engine import RiskEngine
from app.services.water.water_balance import Site, available_water, drought_severities

START = date(2025, 11, 15)
WHEAT = CropSeason(crop=CropName.WHEAT, sowing_date=START, harvest_date=START + timedelta(days=164), area_hectares=1)
SITE = Site(latitude=30.2, elevation_m=120.0, soil_texture="loam")


def _weather(rain_mm: float, days: int = 165) -> list[DailyObservation]:
    return [DailyObservation(day=START + timedelta(days=i), tmax_c=28.0, tmin_c=12.0, relative_humidity_pct=45.0,
                             wind_speed_ms=2.0, solar_radiation_mj_m2=18.0, precipitation_mm=rain_mm)
            for i in range(days)]


def test_available_water_from_fao56_table_19():
    assert available_water("loam") == (0.155, "loam (FAO-56 Table 19)")
    aw, basis = available_water("sandy clay loam")
    assert aw == 0.155 and "not in FAO-56 Table 19; loam value used" in basis


def test_dry_rainfed_season_reaches_high_and_wet_one_stays_low():
    wheat = get_crop_profile_repository().get(CropName.WHEAT)
    dry = RiskEngine().assess(wheat, WHEAT, _weather(0.0), SITE)
    wet = RiskEngine().assess(wheat, WHEAT, _weather(6.0), SITE)

    assert dry.levels[RiskType.DROUGHT] == RiskLevel.HIGH and dry.high_days[RiskType.DROUGHT] > 0
    assert wet.levels[RiskType.DROUGHT] == RiskLevel.LOW
    assert any("rainfed root-zone water stress" in g for g in dry.evidence_gaps)
    assert not any("No threshold values yet" in g and "drought" in g for g in dry.evidence_gaps)


def test_stress_builds_over_time_not_from_day_one():
    sev, _ = drought_severities(get_crop_profile_repository().get(CropName.WHEAT), START, 165, _weather(0.0), SITE)
    assert sev[0] == 0.0  # soil starts at field capacity
    first_stress = next(i for i, s in enumerate(sev) if s)
    first_high = next(i for i, s in enumerate(sev) if s == 1.0)
    assert 0 < first_stress < first_high


def test_gap_in_weather_stops_the_balance_and_paddy_rice_is_skipped():
    profiles = get_crop_profile_repository()
    sev, _ = drought_severities(profiles.get(CropName.WHEAT), START, 165, _weather(0.0, days=100), SITE)
    assert sev[99] is not None and all(s is None for s in sev[100:])

    rice = profiles.get(CropName.RICE)
    assert drought_severities(rice, START, 120, _weather(0.0), SITE) is None
    result = RiskEngine().assess(rice, WHEAT.model_copy(update={"crop": CropName.RICE}), _weather(0.0), SITE)
    assert result.levels[RiskType.DROUGHT] is None
