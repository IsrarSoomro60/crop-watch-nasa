from datetime import date, timedelta

import pytest

from app.repositories.crop_profiles import get_crop_profile_repository
from app.schemas.crop import CropName
from app.schemas.environment import DailyObservation
from app.schemas.rotation import CropSeason
from app.services.water.crop_water import effective_rainfall, kc_curve, rotation_water, season_water
from app.services.water.et0 import extraterrestrial_radiation, penman_monteith


def test_extraterrestrial_radiation_matches_fao56_example_8():
    # FAO-56 Example 8: Ra on 3 September at 20°S = 32.2 MJ m-2 day-1
    assert extraterrestrial_radiation(-20.0, date(2023, 9, 3)) == pytest.approx(32.2, abs=0.1)


def test_penman_monteith_matches_fao56_example_18():
    # FAO-56 Example 18 (Uccle, Brussels, 6 July): ETo = 3.9 mm/day
    # Tmax 21.5, Tmin 12.3, ea 1.409 kPa, Rs 22.07 MJ, u2 2.078 m/s, lat 50°48'N, z 100 m
    et0 = penman_monteith(21.5, 12.3, 1.409, 22.07, 2.078, 50.8, date(2023, 7, 6), 100)
    assert et0 == pytest.approx(3.9, abs=0.1)


def test_effective_rainfall_fao_monthly_formula():
    # Training Manual 3 worked answers: P = 90 -> 47, P = 35 -> 11, P = 5 -> 0
    june = [date(2025, 6, 1) + timedelta(days=i) for i in range(30)]
    assert effective_rainfall(june, [3.0] * 30) == pytest.approx(47.0)
    assert effective_rainfall(june, [35 / 30] * 30) == pytest.approx(11.0)
    assert effective_rainfall(june, [5 / 30] * 30) == pytest.approx(0.0)


def test_kc_curve_follows_fao56_shape():
    profile = get_crop_profile_repository().get(CropName.WHEAT)  # 25/35/65/40 days, Kc 0.3/1.15/0.4
    curve = kc_curve(profile, 165)
    assert curve[0] == curve[24] == 0.3
    assert curve[59] == pytest.approx(1.15)  # end of development reaches Kc mid
    assert curve[60] == curve[124] == 1.15
    assert curve[164] == pytest.approx(0.4)  # harvest reaches Kc end
    assert all(a <= b for a, b in zip(curve[25:59], curve[26:60], strict=True))  # rising in development


def _weather(start: date, days: int, rain: float = 0.0) -> list[DailyObservation]:
    return [
        DailyObservation(day=start + timedelta(days=i), tmax_c=35.0, tmin_c=22.0, relative_humidity_pct=50.0,
                         wind_speed_ms=2.0, solar_radiation_mj_m2=23.4, precipitation_mm=rain)
        for i in range(days)
    ]


def test_paddy_rice_needs_more_water_than_upland_maize():
    repo = get_crop_profile_repository()
    start = date(2025, 6, 15)
    end = start + timedelta(days=119)
    obs = _weather(start, 120)
    rice = season_water(repo.get(CropName.RICE), CropSeason(crop=CropName.RICE, sowing_date=start, harvest_date=end,
                                                            area_hectares=1), obs, 30.0, 120.0)
    maize = season_water(repo.get(CropName.MAIZE), CropSeason(crop=CropName.MAIZE, sowing_date=start, harvest_date=end,
                                                              area_hectares=1), obs, 30.0, 120.0)
    assert rice.paddy_extra_mm == pytest.approx(200 + 6 * 120 + 100)
    assert rice.irrigation_need_mm > maize.irrigation_need_mm > 0
    assert maize.effective_rainfall_mm == 0.0
    assert maize.crop_water_use_mm < maize.et0_mm * 1.2  # Kc never above Kc mid


def test_missing_weather_or_stage_lengths_leave_water_unset():
    repo = get_crop_profile_repository()
    start = date(2025, 11, 1)
    end = start + timedelta(days=99)
    berseem = CropSeason(crop=CropName.BERSEEM, sowing_date=start, harvest_date=end, area_hectares=1)
    wheat = CropSeason(crop=CropName.WHEAT, sowing_date=start, harvest_date=end, area_hectares=1)
    profiles = {CropName.BERSEEM: repo.get(CropName.BERSEEM), CropName.WHEAT: repo.get(CropName.WHEAT)}

    water = rotation_water(profiles, [wheat, berseem], _weather(start, 100), 30.0, 120.0)
    assert water.seasons[0].irrigation_need_mm is not None
    assert water.seasons[1].irrigation_need_mm is None  # berseem: no FAO-56 stage lengths
    assert water.irrigation_need_m3 is None

    short = season_water(profiles[CropName.WHEAT], wheat, _weather(start, 50), 30.0, 120.0)
    assert short.irrigation_need_mm is None
    assert any("weather missing for 50 of 100 days" in n for n in short.notes)
