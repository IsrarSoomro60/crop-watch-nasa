"""Turns raw NASA POWER responses into daily observations and a data note."""

from datetime import date, datetime
from typing import Any

from app.schemas.environment import DailyObservation, DataNote
from app.schemas.farm import Location
from app.services.nasa.client import PowerResponse

__all__ = ["DailyObservation", "build_data_note", "parse_power_daily"]

# POWER uses this sentinel for missing values (e.g. days not yet processed).
POWER_FILL_VALUE = -999.0

_FIELD_MAP = {
    "T2M": "tmean_c",
    "T2M_MAX": "tmax_c",
    "T2M_MIN": "tmin_c",
    "PRECTOTCORR": "precipitation_mm",
    "RH2M": "relative_humidity_pct",
    "WS2M": "wind_speed_ms",
    "ALLSKY_SFC_SW_DWN": "solar_radiation_mj_m2",
    "GWETTOP": "surface_soil_moisture",
    "GWETROOT": "soil_moisture",
}


def parse_power_daily(payload: dict[str, Any]) -> list[DailyObservation]:
    parameters: dict[str, dict[str, float]] = payload["properties"]["parameter"]
    days: dict[str, dict[str, float | None]] = {}
    for power_name, series in parameters.items():
        field = _FIELD_MAP.get(power_name)
        if field is None:
            continue
        for day_key, value in series.items():
            days.setdefault(day_key, {})[field] = None if value == POWER_FILL_VALUE else value
    return [
        DailyObservation(day=datetime.strptime(k, "%Y%m%d").date(), **v)
        for k, v in sorted(days.items())
    ]


def build_data_note(
    response: PowerResponse, observations: list[DailyObservation], start: date, end: date
) -> DataNote:
    coords = response.payload.get("geometry", {}).get("coordinates", [])
    elevation = coords[2] if len(coords) > 2 and coords[2] != POWER_FILL_VALUE else None
    with_temp = [o.day for o in observations if o.tmax_c is not None or o.tmean_c is not None]
    return DataNote(
        grid_cell_center=Location(latitude=response.latitude, longitude=response.longitude),
        elevation_m=elevation,
        requested_start=start,
        requested_end=end,
        latest_observation_date=max(with_temp, default=None),
        from_cache=response.from_cache,
        from_sample=response.from_sample,
    )
