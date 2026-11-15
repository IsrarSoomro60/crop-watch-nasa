import json
from datetime import date

from app.schemas.environment import DailyObservation
from app.schemas.farm import Location
from app.services import gpm
from app.services.gpm import apply_gpm, gpm_series

MULTAN = Location(latitude=30.20, longitude=71.47)


def _file(tmp_path, dates, mm, sources):
    p = tmp_path / "gpm.json"
    p.write_text(json.dumps({"districts": {"Multan": {
        "cell": [30.25, 71.45], "dates": dates, "precipitation_mm": mm, "sources": sources,
    }}}))
    gpm._load.cache_clear()
    return p


def _obs(day: str, rain: float | None) -> DailyObservation:
    return DailyObservation(day=date.fromisoformat(day), tmax_c=35, tmin_c=25, tmean_c=30, precipitation_mm=rain)


def test_swaps_rain_only_where_gpm_has_a_value_and_reports_the_difference(tmp_path):
    p = _file(tmp_path, ["2025-07-01", "2025-07-02", "2025-07-03"], [10.0, None, 4.0], ["final", None, "late"])
    obs = [_obs("2025-07-01", 5.0), _obs("2025-07-02", 2.0), _obs("2025-07-03", 1.0)]
    out, src = apply_gpm(obs, MULTAN, p)
    assert [o.precipitation_mm for o in out] == [10.0, 2.0, 4.0]  # day 2 keeps POWER rain
    assert out[0].tmax_c == 35  # only rain changes
    assert obs[0].precipitation_mm == 5.0  # input untouched
    assert (src.source, src.district, src.days_gpm, src.days_late, src.days_total) == ("gpm", "Multan", 2, 1, 3)
    assert (src.gpm_total_mm, src.power_total_mm, src.difference_pct) == (14.0, 6.0, 133.0)
    assert "Late run" in src.message and "disagree a lot" in src.message


def test_places_away_from_the_saved_cells_keep_power_rain(tmp_path):
    p = _file(tmp_path, ["2025-07-01"], [10.0], ["final"])
    far = Location(latitude=31.5, longitude=74.3)  # Lahore
    obs = [_obs("2025-07-01", 5.0)]
    out, src = apply_gpm(obs, far, p)
    assert out is obs and src.source == "power"
    assert gpm_series(far, p) is None


def test_dates_outside_the_series_keep_power_rain(tmp_path):
    p = _file(tmp_path, ["2025-07-01"], [10.0], ["final"])
    obs = [_obs("2019-07-01", 5.0)]
    out, src = apply_gpm(obs, MULTAN, p)
    assert out is obs and src.source == "power" and "does not cover" in src.message


def test_missing_file_falls_back_to_power(tmp_path):
    gpm._load.cache_clear()
    out, src = apply_gpm([_obs("2025-07-01", 5.0)], MULTAN, tmp_path / "none.json")
    assert src.source == "power"
