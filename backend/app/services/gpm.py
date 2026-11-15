"""GPM IMERG daily rain in place of NASA POWER rain, where the saved GPM series covers the location.

NASA POWER rain (PRECTOTCORR) comes from a ~50 km model grid; GPM IMERG is satellite-based on a ~10 km
grid, so it is preferred for rain where it is available. Only rain changes: temperature, humidity,
sunlight and wind stay from POWER. The saved series (app/data/sample/gpm_imerg_daily.json, built by
scripts/fetch_gpm.py) covers the four demo districts; other places keep POWER rain.

Each GPM day is labelled "final" (gauge-calibrated) or "late" (near real time, not gauge-calibrated,
less accurate). The comparison reports how many days came from each, and how far GPM and POWER disagree,
because neither is a rain gauge in the farmer's field.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

from app.core.config import APP_DIR
from app.schemas.environment import DailyObservation
from app.schemas.farm import Location
from app.schemas.recommendation import RainSource

GPM_PATH = APP_DIR / "data" / "sample" / "gpm_imerg_daily.json"
MAX_DISTANCE_KM = 10.0  # about one 0.1-degree GPM cell
BIG_DIFFERENCE_PCT = 30.0


def _km(a: Location, lat: float, lon: float) -> float:
    p1, p2 = math.radians(a.latitude), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


@lru_cache
def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def gpm_series(location: Location, path: Path = GPM_PATH) -> tuple[str, dict[str, tuple[float, str]]] | None:
    """(district, {YYYY-MM-DD: (mm, "final"|"late")}) for the GPM cell covering the location, else None."""
    data = _load(path)
    if not data:
        return None
    for name, v in data["districts"].items():
        lat, lon = v["cell"]
        if _km(location, lat, lon) <= MAX_DISTANCE_KM:
            sources = v.get("sources") or ["final"] * len(v["dates"])
            return name, {
                d: (mm, src or "final")
                for d, mm, src in zip(v["dates"], v["precipitation_mm"], sources, strict=True)
                if mm is not None
            }
    return None


def apply_gpm(
    observations: list[DailyObservation], location: Location, path: Path = GPM_PATH
) -> tuple[list[DailyObservation], RainSource]:
    """Swap in GPM rain day by day where it exists; report what was used. Never mutates the input."""
    found = gpm_series(location, path)
    if found is None:
        return observations, RainSource(
            source="power",
            message="Rain from NASA POWER (about 50 km grid). Satellite GPM rain is saved only for the four "
            "demo districts.",
        )
    district, series = found
    out: list[DailyObservation] = []
    gpm_total = power_total = 0.0
    used = late = 0
    for o in observations:
        hit = series.get(o.day.isoformat())
        if hit is None:
            out.append(o)
            continue
        mm, src = hit
        if o.precipitation_mm is not None:
            power_total += o.precipitation_mm
            gpm_total += mm
        used += 1
        late += src == "late"
        out.append(o.model_copy(update={"precipitation_mm": mm}))

    if used == 0:
        return observations, RainSource(
            source="power", district=district,
            message="Rain from NASA POWER: the saved GPM series does not cover these dates.",
        )
    diff = None if power_total == 0 else round((gpm_total - power_total) / power_total * 100, 0)
    days = len(observations)
    msg = (
        f"Rain from NASA GPM IMERG satellite data (about 10 km) for {used} of {days} days around {district}"
        + (f", {late} of them from the faster Late run (not gauge-checked, less accurate)" if late else "")
        + f". Over those days GPM shows {gpm_total:.0f} mm and NASA POWER {power_total:.0f} mm"
        + (f" ({diff:+.0f}%)" if diff is not None else "")
        + "."
    )
    if diff is not None and abs(diff) >= BIG_DIFFERENCE_PCT:
        msg += " The two sources disagree a lot here: check rain-based results against local rain records."
    return out, RainSource(
        source="gpm", district=district, days_total=days, days_gpm=used, days_late=late,
        gpm_total_mm=round(gpm_total, 1), power_total_mm=round(power_total, 1), difference_pct=diff,
        message=msg,
    )
