from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.environment import DailyObservation
from app.schemas.recommendation import ClimateScenario
from app.services.scenario import apply_scenario, scenario_note

OBS = [
    DailyObservation(day=date(2025, 6, 1), tmean_c=30, tmax_c=38, tmin_c=24, precipitation_mm=10),
    DailyObservation(day=date(2025, 6, 2), tmean_c=None, tmax_c=None, tmin_c=None, precipitation_mm=None),
]


def test_shifts_temperature_and_scales_rain():
    out = apply_scenario(OBS, ClimateScenario(temperature_change_c=2, rainfall_change_pct=-30))
    assert (out[0].tmean_c, out[0].tmax_c, out[0].tmin_c) == (32, 40, 26)
    assert out[0].precipitation_mm == pytest.approx(7)
    # Missing values stay missing rather than becoming a shifted number.
    assert out[1].tmax_c is None and out[1].precipitation_mm is None
    # The observed data is not modified.
    assert OBS[0].tmax_c == 38


def test_neutral_or_missing_scenario_returns_the_same_data():
    assert apply_scenario(OBS, None) is OBS
    assert apply_scenario(OBS, ClimateScenario()) is OBS
    assert scenario_note(ClimateScenario()) is None


def test_note_says_it_is_not_a_forecast():
    note = scenario_note(ClimateScenario(temperature_change_c=1.5))
    assert note is not None and "+1.5 °C" in note and "not a forecast" in note


def test_scenario_limits_are_enforced():
    with pytest.raises(ValidationError):
        ClimateScenario(temperature_change_c=9)
    with pytest.raises(ValidationError):
        ClimateScenario(rainfall_change_pct=-100)
