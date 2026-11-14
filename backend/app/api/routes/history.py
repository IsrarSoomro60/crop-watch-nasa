import asyncio
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_nasa_client, get_soil_client
from app.api.routes.environmental_data import load_environmental_data
from app.repositories.crop_profiles import CropProfileRepository, get_crop_profile_repository
from app.schemas.environment import EnvironmentalData
from app.schemas.farm import Location
from app.schemas.history import HistoryRequest, HistoryResult, SeasonHistory
from app.schemas.rotation import CropSeason
from app.services.history.vulnerability import (
    METHOD,
    complete_years,
    history_fetch_range,
    season_history,
    summarise,
)
from app.services.nasa.client import NasaPowerClient
from app.services.soil.soilgrids import SoilGridsClient

router = APIRouter(prefix="/history", tags=["history"])

DEFAULT_YEARS = 20
POWER_LAG_DAYS = 3  # POWER usually lags real time by 2-3 days


def history_window(
    seasons: list[CropSeason], start_year: int | None, end_year: int | None
) -> tuple[int, int, date, date]:
    today = date.today()
    first = start_year or today.year - DEFAULT_YEARS - 1
    last = end_year or today.year
    if last < first:
        raise HTTPException(status_code=422, detail="end_year must not be before start_year")
    fetch_start, fetch_end = history_fetch_range(seasons, first, last)
    return first, last, fetch_start, min(fetch_end, today)


async def prefetch_history_weather(location: Location, seasons: list[CropSeason], nasa: NasaPowerClient) -> None:
    """Download the weather run_history will need, so it can run alongside other downloads.

    Failures are ignored here: run_history repeats the request and reports any error itself.
    """
    if not seasons:
        return
    _, _, start, end = history_window(seasons, None, None)
    try:
        await nasa.fetch_daily(location.latitude, location.longitude, start, end)
    except httpx.HTTPError:
        pass


def likely_future(seasons: list[CropSeason]) -> list[CropSeason]:
    """Seasons that probably end after the latest POWER day (decided exactly once weather is in)."""
    cutoff = date.today() - timedelta(days=POWER_LAG_DAYS)
    return [s for s in seasons if s.harvest_date > cutoff]


async def soil_texture(client: SoilGridsClient, location: Location) -> str | None:
    try:
        soil = await client.get(location)
    except httpx.HTTPError:
        return None
    return soil.texture_class if soil else None


async def run_history(
    location: Location,
    seasons: list[CropSeason],
    nasa: NasaPowerClient,
    profiles: CropProfileRepository,
    texture: str | None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> tuple[list[SeasonHistory], EnvironmentalData, int, int]:
    first, last, fetch_start, fetch_end = history_window(seasons, start_year, end_year)
    env = await load_environmental_data(nasa, location.latitude, location.longitude, fetch_start, fetch_end)
    latest = env.data_note.latest_observation_date
    elevation = env.data_note.elevation_m or 0.0

    histories = []
    seen = set()
    for s in seasons:
        key = (s.crop, s.sowing_date.strftime("%m-%d"), s.harvest_date.strftime("%m-%d"))
        if key in seen:
            continue
        seen.add(key)
        years = complete_years(s, first, last, latest)
        if start_year is None:
            years = years[-DEFAULT_YEARS:]
        histories.append(season_history(profiles, s, env.observations, years, location.latitude, elevation, texture))
    used = [y for h in histories for y in h.years]
    return histories, env, min(used, default=first), max(used, default=last)


@router.post("", response_model=HistoryResult)
async def season_vulnerability(
    request: HistoryRequest,
    nasa: NasaPowerClient = Depends(get_nasa_client),
    soil_client: SoilGridsClient = Depends(get_soil_client),
    profiles: CropProfileRepository = Depends(get_crop_profile_repository),
) -> HistoryResult:
    # Soil and weather downloads don't depend on each other: run them at the same time.
    texture, _ = await asyncio.gather(
        soil_texture(soil_client, request.location),
        prefetch_history_weather(request.location, request.seasons, nasa)
        if request.start_year is None and request.end_year is None else asyncio.sleep(0),
    )
    histories, env, first, last = await run_history(
        request.location, request.seasons, nasa, profiles, texture, request.start_year, request.end_year
    )
    return HistoryResult(
        location=request.location,
        start_year=first,
        end_year=last,
        seasons=histories,
        summary=summarise(histories),
        method=METHOD,
        data_note=env.data_note,
    )
