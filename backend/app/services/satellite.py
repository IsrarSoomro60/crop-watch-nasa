"""Satellite add-ons.

* GRACE/GRACE-FO water storage: a Pakistan-wide grid (app/data/grace_pakistan.npz, built by
  scripts/build_grace_pakistan.py), so any location in Pakistan gets its regional series.
* MODIS NDVI and SMAP soil moisture: saved one-year samples for the four demo districts only
  (app/data/sample/satellite_samples.json); other locations get none rather than a borrowed series.
"""

import json
import math
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import APP_DIR
from app.schemas.farm import Location
from app.schemas.satellite import (
    GracePoint,
    GraceSummary,
    NdviPoint,
    RegionalWater,
    SatelliteData,
    SoilMoisturePoint,
)

SAMPLES_PATH = APP_DIR / "data" / "sample" / "satellite_samples.json"
GRACE_PATH = APP_DIR / "data" / "grace_pakistan.npz"
MAX_DISTANCE_KM = 50.0
GRACE_EPOCH = date(2002, 1, 1)
GRACE_SOURCE = "JPL GRACE/GRACE-FO mascon RL06.3Mv04 CRI (PO.DAAC), anomaly vs 2004.0-2009.999 mean"
TREND_YEARS = 10  # recent trend window, alongside the full-record trend
MAX_CELL_DEGREES = 1.0

LIMITATIONS = [
    "NDVI and soil moisture: saved one-year sample (June 2025 - May 2026) for the four demo districts only.",
    "NDVI shows living green vegetation; it cannot reliably tell crop residue from bare soil.",
    "MODIS NDVI is one 250 m pixel at the district point, not the farmer's field.",
    "SMAP L4 soil moisture is a 9 km model analysis that assimilates satellite data, not a field "
    "measurement, and irrigation is not fully represented in it.",
    "GRACE does not measure groundwater directly: it infers changes in total water storage (groundwater, "
    "soil moisture and surface water combined) from changes in Earth's gravity, over mascons about 300 km "
    "wide. It describes the region, not one farm or one aquifer.",
]


def _km(a: Location, lat: float, lon: float) -> float:
    p1, p2 = math.radians(a.latitude), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def grace_trend(series: list[GracePoint]) -> float | None:
    """OLS slope in cm per year; descriptive only (no significance test)."""
    if len(series) < 24:
        return None
    xs = [(p.date - date(2000, 1, 1)).days / 365.25 for p in series]
    ys = [p.lwe_cm for p in series]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx, 3)


@lru_cache
def _grace_grid(path: Path = GRACE_PATH) -> dict | None:
    if not path.exists():
        return None
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def grace_at(location: Location, path: Path = GRACE_PATH) -> GraceSummary | None:
    g = _grace_grid(path)
    if g is None:
        return None
    lat, lon = g["lat"], g["lon"]
    if not (lat[0] - 0.25 <= location.latitude <= lat[-1] + 0.25
            and lon[0] - 0.25 <= location.longitude % 360 <= lon[-1] + 0.25):
        return None
    # Nearest cell with data; coastal points can fall on an ocean cell, so look up to ~1 degree away.
    has_data = ~np.all(np.isnan(g["lwe_cm"]), axis=0)
    dlat = lat[:, None] - location.latitude
    dlon = (lon[None, :] - location.longitude % 360) * math.cos(math.radians(location.latitude))
    dist = np.where(has_data, np.hypot(dlat, dlon), np.inf)
    i, j = (int(k) for k in np.unravel_index(np.argmin(dist), dist.shape))
    if dist[i, j] > MAX_CELL_DEGREES:
        return None
    series = [
        GracePoint(
            date=GRACE_EPOCH + timedelta(days=float(d)),
            lwe_cm=round(float(v), 2),
            uncertainty_cm=round(float(u), 2),
        )
        for d, v, u in zip(g["days_since_2002"], g["lwe_cm"][:, i, j], g["uncertainty_cm"][:, i, j], strict=True)
        if not np.isnan(v)
    ]
    if not series:
        return None
    recent_start = series[-1].date - timedelta(days=round(TREND_YEARS * 365.25))
    return GraceSummary(
        cell_lat=float(lat[i]),
        cell_lon=float(lon[j]) if lon[j] <= 180 else float(lon[j]) - 360,
        trend_cm_per_year=grace_trend(series),
        recent_trend_cm_per_year=grace_trend([p for p in series if p.date >= recent_start]),
        recent_trend_years=TREND_YEARS,
        latest=series[-1],
        series=series,
        source=GRACE_SOURCE,
    )


@lru_cache
def load_samples(path: Path = SAMPLES_PATH) -> dict:
    if not path.exists():
        return {"sources": {}, "districts": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def satellite_for(location: Location, path: Path = SAMPLES_PATH, grace_path: Path = GRACE_PATH) -> SatelliteData | None:
    data = load_samples(path)
    best = min(
        ((_km(location, d["latitude"], d["longitude"]), d) for d in data["districts"].values()),
        key=lambda t: t[0],
        default=None,
    )
    district = best[1] if best is not None and best[0] <= MAX_DISTANCE_KM else None
    grace = grace_at(location, grace_path)
    if district is None and grace is None:
        return None
    sources = dict(data["sources"]) if district else {}
    if grace:
        sources["grace"] = GRACE_SOURCE
    return SatelliteData(
        district=district["name"] if district else None,
        distance_km=round(best[0], 1) if district and best else None,
        ndvi=[
            NdviPoint(**p, usable=p["ndvi"] is not None and p["reliability"] in (0, 1))
            for p in (district["ndvi"] if district else [])
        ],
        soil_moisture=[SoilMoisturePoint.model_validate(p) for p in (district["soil_moisture"] if district else [])],
        grace=grace,
        sources=sources,
        limitations=LIMITATIONS,
    )


def regional_water(location: Location) -> RegionalWater | None:
    """Plain-language GRACE context for the comparison; descriptive, not a score."""
    g = grace_at(location)
    if g is None or g.latest is None:
        return None
    parts = [f"GRACE satellites: total water stored in this region (about 300 km across) has changed "
             f"{g.trend_cm_per_year:+.1f} cm per year since {g.series[0].date.year}"
             if g.trend_cm_per_year is not None else "GRACE satellites: regional water storage"]
    if g.recent_trend_cm_per_year is not None:
        parts.append(f"({g.recent_trend_cm_per_year:+.1f} cm per year over the last {g.recent_trend_years} years)")
    msg = " ".join(parts) + (
        f". In {g.latest.date:%b %Y} it was {g.latest.lwe_cm:+.0f} cm (± {g.latest.uncertainty_cm:.0f} cm) "
        "compared with the 2004-2009 average."
    )
    if g.trend_cm_per_year is not None and g.trend_cm_per_year < 0:
        msg += " Falling regional storage is one reason to give water saving more weight in your priorities."
    return RegionalWater(
        trend_cm_per_year=g.trend_cm_per_year,
        recent_trend_cm_per_year=g.recent_trend_cm_per_year,
        recent_trend_years=g.recent_trend_years,
        first_month=g.series[0].date,
        latest=g.latest,
        message=msg,
        source=g.source,
    )
