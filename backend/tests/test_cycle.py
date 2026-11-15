"""B3: rotations of different lengths are compared per year, not on totals."""

from datetime import date, timedelta

from app.repositories.crop_profiles import get_crop_profile_repository
from app.schemas.crop import CropName
from app.schemas.environment import DailyObservation
from app.schemas.farm import Location, Priorities
from app.schemas.recommendation import ComparisonRequest
from app.schemas.rotation import CropSeason, Rotation
from app.services.income.income import income_scores, rotation_income
from app.services.recommendation.recommendation_engine import RecommendationEngine
from app.services.rotation.cycle import cycle_years
from app.services.rotation.ground_cover import ground_cover


def _wheat(year: int) -> CropSeason:
    return CropSeason(crop=CropName.WHEAT, sowing_date=date(year, 11, 10), harvest_date=date(year + 1, 4, 10),
                      area_hectares=2)


ONE_YEAR = Rotation(name="Wheat (1 yr)", seasons=[_wheat(2023)])
TWO_YEARS = Rotation(name="Wheat twice (2 yr)", seasons=[_wheat(2023), _wheat(2024)])


def test_cycle_length():
    rice_wheat = Rotation(name="RW", seasons=[
        CropSeason(crop=CropName.RICE, sowing_date=date(2025, 6, 15), harvest_date=date(2025, 10, 20), area_hectares=1),
        CropSeason(crop=CropName.WHEAT, sowing_date=date(2025, 11, 15), harvest_date=date(2026, 4, 15),
                   area_hectares=1),
    ])
    assert cycle_years(rice_wheat) == 1
    assert cycle_years(ONE_YEAR) == 1 and cycle_years(TWO_YEARS) == 2
    leap = Rotation(name="L", seasons=[
        CropSeason(crop=CropName.MAIZE, sowing_date=date(2024, 2, 29), harvest_date=date(2024, 6, 1), area_hectares=1),
        CropSeason(crop=CropName.MAIZE, sowing_date=date(2025, 2, 28), harvest_date=date(2025, 6, 1), area_hectares=1),
    ])
    assert cycle_years(leap) == 2  # 29 Feb + 1 year -> 28 Feb, which is the next cycle


def test_income_compared_per_year():
    one, two = rotation_income(ONE_YEAR, None), rotation_income(TWO_YEARS, None)
    assert two.gross_revenue == 2 * one.gross_revenue  # totals differ...
    assert two.gross_revenue_per_year == one.gross_revenue_per_year  # ...per year they match
    assert income_scores([one, two]) == [1.0, 1.0]


def test_bare_soil_per_year_and_cover_over_whole_cycle():
    g1, g2 = ground_cover(ONE_YEAR), ground_cover(TWO_YEARS)
    assert g2.cycle_years == 2 and (g2.cycle_end - g2.cycle_start).days + 1 in (730, 731)
    assert abs(g2.bare_soil_days_per_year - g1.bare_soil_days_per_year) <= 1
    assert abs(g2.cover_fraction - g1.cover_fraction) <= 0.01


def _weather(start: date, days: int) -> list[DailyObservation]:
    return [DailyObservation(day=start + timedelta(days=i), tmax_c=24.0, tmin_c=8.0, relative_humidity_pct=50.0,
                             wind_speed_ms=2.0, solar_radiation_mj_m2=15.0, precipitation_mm=0.0)
            for i in range(days)]


def test_compare_scores_water_and_income_per_year_and_states_basis():
    alt = Rotation(name="Wheat (1 yr, again)", seasons=[_wheat(2023)])
    request = ComparisonRequest(location=Location(latitude=30.2, longitude=71.47), current=ONE_YEAR,
                                alternatives=[TWO_YEARS, alt], priorities=Priorities())
    rec = RecommendationEngine(get_crop_profile_repository()).compare(request, _weather(date(2023, 11, 1), 560))
    by = {r.rotation_name: r for r in rec.ranked}
    w1 = by["Wheat (1 yr)"].evaluation.water
    w2 = by["Wheat twice (2 yr)"].evaluation.water
    assert w2.irrigation_need_m3 > w1.irrigation_need_m3 * 1.5  # total over two years is larger
    assert abs(w2.irrigation_need_m3_per_year - w1.irrigation_need_m3_per_year) <= 0.05 * w1.irrigation_need_m3_per_year
    assert by["Wheat twice (2 yr)"].dimension_scores.water >= 0.95
    assert by["Wheat twice (2 yr)"].dimension_scores.income == 1.0
    assert any("different cycle lengths" in e and "Wheat twice (2 yr) 2 years" in e for e in rec.explanation)
