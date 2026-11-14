"""Save real API responses for the demo districts as offline fallbacks.

Run from backend/:
    uv run python -m scripts.fetch_sample_data [weather|soil|all] [START END]

Dates are YYYY-MM-DD (weather only). Files go to app/data/sample/:
- power_<lat>_<lon>.json      NASA POWER daily weather, one per weather grid cell
- soilgrids_<lat>_<lon>.json  SoilGrids topsoil, at the first nearby point with data
"""

import asyncio
import json
import sys
from datetime import date

import httpx

from app.core.config import get_settings
from app.schemas.farm import Location
from app.services.nasa.client import NasaPowerClient, _TTLCache, sample_path
from app.services.soil.soilgrids import SoilGridsClient, parse_layers
from app.services.warm_up import DEMO_DISTRICTS

DEFAULT_RANGE = (date(2025, 6, 1), date(2026, 5, 31))  # one kharif + rabi cycle
SOILGRIDS_PAUSE_S = 13  # ISRIC fair use: at most 5 requests per minute


async def fetch_weather(start: date, end: date) -> None:
    settings = get_settings()
    client = NasaPowerClient(settings, cache=_TTLCache())
    for name, (lat, lon) in DEMO_DISTRICTS.items():
        resp = await client.fetch_daily(lat, lon, start, end)
        path = sample_path(settings.sample_data_dir, resp.latitude, resp.longitude)
        path.write_text(json.dumps(resp.payload), encoding="utf-8")
        print(f"{name}: weather cell ({resp.latitude}, {resp.longitude}) -> {path.name}")
        await asyncio.sleep(1)


async def fetch_soil() -> None:
    settings = get_settings()
    client = SoilGridsClient(settings)
    async with httpx.AsyncClient(timeout=120) as http:
        for name, (lat, lon) in DEMO_DISTRICTS.items():
            for candidate in client._candidates(Location(latitude=lat, longitude=lon)):
                payload = await client._query(http, candidate)
                await asyncio.sleep(SOILGRIDS_PAUSE_S)
                if any(layer.clay_pct is not None for layer in parse_layers(payload)):
                    name_ = f"soilgrids_{candidate.latitude:.3f}_{candidate.longitude:.3f}.json"
                    path = settings.sample_data_dir / name_
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    print(f"{name}: soil at ({candidate.latitude}, {candidate.longitude}) -> {path.name}")
                    break
            else:
                print(f"{name}: no SoilGrids data within ~5 km")


if __name__ == "__main__":
    args = sys.argv[1:]
    which = args.pop(0) if args and args[0] in ("weather", "soil", "all") else "all"
    rng = (date.fromisoformat(args[0]), date.fromisoformat(args[1])) if len(args) == 2 else DEFAULT_RANGE
    if which in ("weather", "all"):
        asyncio.run(fetch_weather(*rng))
    if which in ("soil", "all"):
        asyncio.run(fetch_soil())
