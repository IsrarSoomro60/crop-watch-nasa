"""Saved satellite samples for the demo districts (built by scripts/build_satellite_samples.py).

Only the four demo districts have samples; other locations return None rather than a
borrowed series from far away.
"""

import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.core.config import APP_DIR
from app.schemas.farm import Location
from app.schemas.satellite import GracePoint, GraceSummary, NdviPoint, SatelliteData, SoilMoisturePoint

SAMPLES_PATH = APP_DIR / "data" / "sample" / "satellite_samples.json"
MAX_DISTANCE_KM = 50.0

LIMITATIONS = [
    "Saved one-year sample (June 2025 - May 2026) for the demo districts, not a live feed.",
    "NDVI shows living green vegetation; it cannot reliably tell crop residue from bare soil.",
    "MODIS NDVI is one 250 m pixel at the district point, not the farmer's field.",
    "SMAP L4 soil moisture is a 9 km model analysis that assimilates satellite data, not a field "
    "measurement, and irrigation is not fully represented in it.",
    "GRACE measures total water storage (groundwater, soil, surface water) over mascons about 300 km "
    "wide; it describes the region, not one farm or one aquifer.",
]


def _km(a: Location, lat: float, lon: float) -> float:
    p1, p2 = math.radians(a.latitude), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def grace_trend(series: list[GracePoint]) -> float | None:
    if len(series) < 24:
        return None
    xs = [(p.date - date(2000, 1, 1)).days / 365.25 for p in series]
    ys = [p.lwe_cm for p in series]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx, 3)


@lru_cache
def load_samples(path: Path = SAMPLES_PATH) -> dict:
    if not path.exists():
        return {"sources": {}, "districts": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def satellite_for(location: Location, path: Path = SAMPLES_PATH) -> SatelliteData | None:
    data = load_samples(path)
    best = min(
        ((_km(location, d["latitude"], d["longitude"]), d) for d in data["districts"].values()),
        key=lambda t: t[0],
        default=None,
    )
    if best is None or best[0] > MAX_DISTANCE_KM:
        return None
    dist, d = best
    grace = None
    if d.get("grace"):
        series = [GracePoint.model_validate(p) for p in d["grace"]["series"]]
        grace = GraceSummary(
            cell_lat=d["grace"]["cell_lat"], cell_lon=d["grace"]["cell_lon"],
            trend_cm_per_year=grace_trend(series), latest=series[-1] if series else None, series=series,
        )
    return SatelliteData(
        district=d["name"],
        distance_km=round(dist, 1),
        ndvi=[
            NdviPoint(**p, usable=p["ndvi"] is not None and p["reliability"] in (0, 1)) for p in d["ndvi"]
        ],
        soil_moisture=[SoilMoisturePoint.model_validate(p) for p in d["soil_moisture"]],
        grace=grace,
        sources=data["sources"],
        limitations=LIMITATIONS,
    )
