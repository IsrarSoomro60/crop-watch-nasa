"""Download demo-district data in the background when the server starts.

One long NASA POWER download per district (20+ years up to today) covers every shorter request
the app makes there: comparisons, history and the weekly check are then answered from the cache.
Soil is fetched one district at a time because SoilGrids allows only ~5 requests a minute.
Everything is also saved to the disk cache, so a restart within the cache lifetime is instant.
"""

import asyncio
import logging
import time
from datetime import date

import httpx

from app.core.config import Settings
from app.schemas.farm import Location
from app.services.nasa.client import NasaPowerClient
from app.services.soil.soilgrids import SoilGridsClient

log = logging.getLogger("cropwatch")

# Districts with saved samples, used across the app and scripts.
# Approximate city-centre coordinates (Multan from the research brief).
DEMO_DISTRICTS: dict[str, tuple[float, float]] = {
    "Multan": (30.20, 71.47),
    "Bahawalpur": (29.40, 71.68),
    "Larkana": (27.56, 68.21),
    "Hyderabad": (25.40, 68.37),
}
HISTORY_YEARS = 21  # matches the history route's default window (20 seasons + the sowing year before)


async def warm_up(settings: Settings) -> None:
    started = time.perf_counter()
    nasa = NasaPowerClient(settings)
    today = date.today()
    start = date(today.year - HISTORY_YEARS, 1, 1)

    async def weather(name: str, lat: float, lon: float) -> None:
        try:
            await nasa.fetch_daily(lat, lon, start, today)
        except httpx.HTTPError as exc:
            log.warning("warm-up: NASA POWER for %s failed: %s", name, exc)

    await asyncio.gather(*(weather(n, la, lo) for n, (la, lo) in DEMO_DISTRICTS.items()))
    log.info("warm-up: weather for %d demo districts ready in %.1f s", len(DEMO_DISTRICTS),
             time.perf_counter() - started)

    soil = SoilGridsClient(settings)
    for name, (la, lo) in DEMO_DISTRICTS.items():
        try:
            await soil.get(Location(latitude=la, longitude=lo))
        except httpx.HTTPError as exc:
            log.warning("warm-up: SoilGrids for %s failed: %s", name, exc)
    log.info("warm-up: soil for demo districts ready; total %.1f s", time.perf_counter() - started)
