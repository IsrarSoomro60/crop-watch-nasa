"""Client for the SoilGrids 2.0 REST API (ISRIC).

SoilGrids gives 250 m machine-learning predictions of soil properties. It masks
built-up areas, so a town-centre point often returns no values; the client then
steps out ~5 km in each direction and reports which point it used.

ISRIC asks for no more than 5 requests per minute, so results are cached for the
life of the process (soil does not change) and saved samples are used when the
service cannot be reached (see scripts/fetch_sample_data.py).
"""

import json
import math
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.farm import Location
from app.schemas.soil import SoilInfo, SoilLayer

PROPERTIES = ("clay", "sand", "silt", "soc", "phh2o", "bdod")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
# Field name and divisor from mapped units to target units (per ISRIC unit_measure.d_factor).
_FIELDS = {
    "clay": ("clay_pct", 10), "sand": ("sand_pct", 10), "silt": ("silt_pct", 10),
    "soc": ("organic_carbon_g_kg", 10), "phh2o": ("ph_h2o", 10), "bdod": ("bulk_density_kg_dm3", 100),
}
SEARCH_STEP_DEG = 0.05  # ~5 km
SAMPLE_MAX_KM = 25.0

_cache: dict[tuple[float, float], SoilInfo] = {}


def distance_km(a: Location, b: Location) -> float:
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat, dlon = lat2 - lat1, math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def usda_texture(clay: float, sand: float, silt: float) -> str:
    """USDA soil texture class from percentages (NRCS texture-triangle rules)."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def parse_layers(payload: dict[str, Any]) -> list[SoilLayer]:
    layers: dict[str, dict[str, Any]] = {}
    for prop in payload["properties"]["layers"]:
        field, divisor = _FIELDS.get(prop["name"], (None, 1))
        if field is None:
            continue
        for depth in prop["depths"]:
            entry = layers.setdefault(depth["label"], {
                "depth": depth["label"], "top_cm": depth["range"]["top_depth"],
                "bottom_cm": depth["range"]["bottom_depth"],
            })
            value = depth["values"].get("mean")
            entry[field] = None if value is None else round(value / divisor, 2)
    return [SoilLayer(**layers[d]) for d in DEPTHS if d in layers]


def topsoil_average(layers: list[SoilLayer]) -> SoilLayer:
    avg: dict[str, float | None] = {}
    for field, _ in _FIELDS.values():
        pairs = [(getattr(lyr, field), lyr.bottom_cm - lyr.top_cm) for lyr in layers if getattr(lyr, field) is not None]
        weight = sum(w for _, w in pairs)
        avg[field] = round(sum(v * w for v, w in pairs) / weight, 2) if weight else None
    return SoilLayer(depth="0-30cm", top_cm=0, bottom_cm=30, **avg)


def _has_data(layers: list[SoilLayer]) -> bool:
    return any(lyr.clay_pct is not None for lyr in layers)


def build_info(requested: Location, used: Location, payload: dict[str, Any], from_sample: bool = False) -> SoilInfo:
    layers = parse_layers(payload)
    top = topsoil_average(layers)
    texture = (
        usda_texture(top.clay_pct, top.sand_pct, top.silt_pct)
        if None not in (top.clay_pct, top.sand_pct, top.silt_pct) else None
    )
    dist = round(distance_km(requested, used), 1)
    notes = ["Modelled 250 m predictions, not a soil test; a local soil test is more reliable."]
    if dist > 0:
        notes.append(f"No SoilGrids data at the requested point (often a built-up area); used a point {dist} km away.")
    return SoilInfo(requested_location=requested, used_location=used, distance_km=dist, layers=layers,
                    topsoil_0_30cm=top, texture_class=texture, from_sample=from_sample, notes=notes)


def sample_files(sample_dir: Path) -> list[Path]:
    return sorted(sample_dir.glob("soilgrids_*.json"))


class SoilGridsClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self._settings = settings
        self._http = http

    async def _query(self, http: httpx.AsyncClient, point: Location) -> dict[str, Any]:
        params = [("lon", point.longitude), ("lat", point.latitude), ("value", "mean")]
        params += [("property", p) for p in PROPERTIES] + [("depth", d) for d in DEPTHS]
        resp = await http.get(self._settings.soilgrids_base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _candidates(self, point: Location) -> list[Location]:
        s = SEARCH_STEP_DEG
        offsets = [(0, 0), (s, 0), (0, s), (-s, 0), (0, -s)]
        return [Location(latitude=round(point.latitude + dy, 4), longitude=round(point.longitude + dx, 4))
                for dy, dx in offsets]

    async def get(self, point: Location) -> SoilInfo | None:
        key = (round(point.latitude, 3), round(point.longitude, 3))
        if key in _cache:
            return _cache[key]
        try:
            info = await self._search(point)
        except httpx.HTTPError:
            info = self._nearest_sample(point)
        if info is not None and not info.from_sample:
            _cache[key] = info
        return info

    async def _search(self, point: Location) -> SoilInfo | None:
        async def run(http: httpx.AsyncClient) -> SoilInfo | None:
            for candidate in self._candidates(point):
                payload = await self._query(http, candidate)
                info = build_info(point, candidate, payload)
                if _has_data(info.layers):
                    return info
            return None

        if self._http is not None:
            return await run(self._http)
        async with httpx.AsyncClient(timeout=self._settings.http_timeout_seconds) as http:
            return await run(http)

    def _nearest_sample(self, point: Location) -> SoilInfo | None:
        best: tuple[float, dict[str, Any], Location] | None = None
        for path in sample_files(self._settings.sample_data_dir):
            payload = json.loads(path.read_text(encoding="utf-8"))
            lon, lat = payload["geometry"]["coordinates"][:2]
            used = Location(latitude=lat, longitude=lon)
            d = distance_km(point, used)
            if d <= SAMPLE_MAX_KM and (best is None or d < best[0]):
                best = (d, payload, used)
        if best is None:
            return None
        info = build_info(point, best[2], best[1], from_sample=True)
        info.notes.append("SoilGrids was unreachable; used a saved sample.")
        return info
