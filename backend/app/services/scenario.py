"""'What if' climate scenarios: shift observed temperature and scale observed rainfall.

This is a simple sensitivity test ("delta method"), not a climate projection. Only temperature and
rainfall change; humidity, sunlight, wind and POWER's soil wetness stay as observed, so effects that
run through them (for example disease-conducive humidity) are not adjusted.
"""

from app.schemas.environment import DailyObservation
from app.schemas.recommendation import ClimateScenario


def apply_scenario(observations: list[DailyObservation], scenario: ClimateScenario | None) -> list[DailyObservation]:
    if scenario is None or scenario.is_neutral:
        return observations
    dt = scenario.temperature_change_c
    rain_factor = max(0.0, 1 + scenario.rainfall_change_pct / 100)

    def shift(v: float | None) -> float | None:
        return None if v is None else v + dt

    return [
        o.model_copy(
            update={
                "tmean_c": shift(o.tmean_c),
                "tmax_c": shift(o.tmax_c),
                "tmin_c": shift(o.tmin_c),
                "precipitation_mm": None if o.precipitation_mm is None else o.precipitation_mm * rain_factor,
            }
        )
        for o in observations
    ]


def scenario_note(scenario: ClimateScenario | None) -> str | None:
    if scenario is None or scenario.is_neutral:
        return None
    parts = []
    if scenario.temperature_change_c:
        parts.append(f"temperature {scenario.temperature_change_c:+g} °C every day")
    if scenario.rainfall_change_pct:
        parts.append(f"rainfall {scenario.rainfall_change_pct:+g}%")
    return (
        f"What-if scenario applied to the observed weather: {' and '.join(parts)}. This is a sensitivity test, "
        "not a forecast or climate projection; humidity, sunlight and soil wetness are unchanged, and seasons "
        "estimated from past years are not adjusted."
    )
