"""Client for NASA POWER daily point data.

POWER provides satellite/model-derived daily agroclimatology. It is not
field-measured data. Weather values sit on a 0.5 x 0.625 degree grid (~50 km)
and usually lag real time by 2-3 days.

Requests are snapped to the grid-cell centre so that every point in a cell
shares one cache entry, and the data cached is exactly what was requested.
If NASA cannot be reached, a saved sample for the same cell is used when one
exists (see scripts/fetch_sample_data.py).
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings

# Codes and meanings: docs/architecture.md (from POWER API docs / research brief Appendix A).
DEFAULT_PARAMETERS = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
    "GWETTOP",
    "GWETROOT",
)

log = logging.getLogger("cropwatch")

GRID_LAT_STEP = 0.5
GRID_LON_STEP = 0.625


def snap_to_grid(latitude: float, longitude: float) -> tuple[float, float]:
    """Nearest weather grid-cell centre (cells are centred on -90 + 0.5i, -180 + 0.625j)."""
    lat = round(latitude / GRID_LAT_STEP) * GRID_LAT_STEP
    lon = -180 + round((longitude + 180) / GRID_LON_STEP) * GRID_LON_STEP
    if lon >= 180:
        lon -= 360
    return round(max(-90.0, min(90.0, lat)), 4), round(lon, 4)


def sample_path(sample_dir: Path, latitude: float, longitude: float) -> Path:
    return sample_dir / f"power_{latitude:.3f}_{longitude:.3f}.json"


@dataclass
class PowerResponse:
    payload: dict[str, Any]
    latitude: float
    longitude: float
    from_cache: bool = False
    from_sample: bool = False


class _TTLCache:
    def __init__(self) -> None:
        self._items: dict[tuple, tuple[float, dict[str, Any]]] = {}

    def get(self, key: tuple) -> dict[str, Any] | None:
        item = self._items.get(key)
        if item is None or item[0] < time.monotonic():
            self._items.pop(key, None)
            return None
        return item[1]

    def set(self, key: tuple, value: dict[str, Any], ttl: float) -> None:
        self._items[key] = (time.monotonic() + ttl, value)

    def find_covering(self, lat: float, lon: float, start: date, end: date, parameters: tuple) -> dict | None:
        """A cached download for the same cell and parameters whose dates include start..end."""
        for key in list(self._items):
            k_lat, k_lon, k_start, k_end, k_params = key
            if (k_lat, k_lon, k_params) == (lat, lon, parameters) and k_start <= start and end <= k_end:
                value = self.get(key)
                if value is not None:
                    return value
        return None

    def clear(self) -> None:
        self._items.clear()


# Shared across requests for the life of the process.
power_cache = _TTLCache()


def _filter_payload(payload: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    lo, hi = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    params = {
        name: {k: v for k, v in series.items() if lo <= k <= hi}
        for name, series in payload["properties"]["parameter"].items()
    }
    return {**payload, "properties": {**payload["properties"], "parameter": params}}


class NasaPowerClient:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient | None = None,
        cache: _TTLCache = power_cache,
    ):
        self._settings = settings
        self._http = http
        self._cache = cache

    async def fetch_daily(
        self,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
        parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
    ) -> PowerResponse:
        lat, lon = snap_to_grid(latitude, longitude)
        key = (lat, lon, start, end, parameters)
        cached = self._cache.get(key)
        if cached is None:
            # A longer download that includes these dates (e.g. 20 years) answers a shorter request too.
            covering = self._cache.find_covering(lat, lon, start, end, parameters) or self._disk_get(
                lat, lon, start, end, parameters
            )
            if covering is not None:
                cached = _filter_payload(covering, start, end)
        if cached is not None:
            return PowerResponse(cached, lat, lon, from_cache=True)

        try:
            payload = await self._request(lat, lon, start, end, parameters)
        except httpx.HTTPError:
            sample = self._load_sample(lat, lon, start, end)
            if sample is None:
                raise
            return PowerResponse(sample, lat, lon, from_sample=True)

        self._cache.set(key, payload, self._settings.nasa_cache_ttl_seconds)
        self._disk_set(lat, lon, start, end, parameters, payload)
        return PowerResponse(payload, lat, lon)

    # --- disk cache: one JSON file per download, reused until it is older than the TTL ---

    def _disk_prefix(self, lat: float, lon: float, parameters: tuple[str, ...]) -> str:
        digest = hashlib.sha1(",".join(parameters).encode()).hexdigest()[:8]
        return f"{lat}_{lon}_{digest}"

    def _disk_dir(self) -> Path | None:
        return self._settings.cache_dir / "power" if self._settings.disk_cache else None

    def _disk_get(self, lat: float, lon: float, start: date, end: date, parameters: tuple[str, ...]) -> dict | None:
        folder = self._disk_dir()
        if folder is None or not folder.exists():
            return None
        ttl = self._settings.nasa_cache_ttl_seconds
        for path in folder.glob(f"{self._disk_prefix(lat, lon, parameters)}_*.json"):
            try:
                f_start, f_end = (date.fromisoformat(x) for x in path.stem.rsplit("_", 2)[-2:])
                age = time.time() - path.stat().st_mtime
                if not (f_start <= start and end <= f_end) or age > ttl:
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            self._cache.set((lat, lon, f_start, f_end, parameters), payload, ttl - age)
            return payload
        return None

    def _disk_set(
        self, lat: float, lon: float, start: date, end: date, parameters: tuple[str, ...], payload: dict
    ) -> None:
        folder = self._disk_dir()
        if folder is None:
            return
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{self._disk_prefix(lat, lon, parameters)}_{start.isoformat()}_{end.isoformat()}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:  # a cache write must never break a request
            log.warning("could not save POWER cache file: %s", exc)

    async def _request(
        self, lat: float, lon: float, start: date, end: date, parameters: tuple[str, ...]
    ) -> dict[str, Any]:
        params = {
            "parameters": ",".join(parameters),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        if self._http is not None:
            resp = await self._http.get(self._settings.nasa_power_base_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=self._settings.http_timeout_seconds) as http:
                resp = await http.get(self._settings.nasa_power_base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _load_sample(self, lat: float, lon: float, start: date, end: date) -> dict[str, Any] | None:
        path = sample_path(self._settings.sample_data_dir, lat, lon)
        if not path.exists():
            return None
        payload = _filter_payload(json.loads(path.read_text(encoding="utf-8")), start, end)
        if not any(payload["properties"]["parameter"].values()):
            return None
        return payload
