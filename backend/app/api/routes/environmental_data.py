from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_nasa_client
from app.schemas.environment import EnvironmentalData
from app.services.nasa.client import NasaPowerClient
from app.services.nasa.data_processor import build_data_note, parse_power_daily

router = APIRouter(prefix="/environmental-data", tags=["environmental data"])


async def load_environmental_data(
    client: NasaPowerClient, latitude: float, longitude: float, start: date, end: date
) -> EnvironmentalData:
    if end < start:
        raise HTTPException(status_code=422, detail="end must not be before start")
    try:
        response = await client.fetch_daily(latitude, longitude, start, end)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"NASA POWER request failed and no offline sample covers this place: {exc}"
        ) from exc
    observations = parse_power_daily(response.payload)
    return EnvironmentalData(
        observations=observations, data_note=build_data_note(response, observations, start, end)
    )


@router.get("/daily", response_model=EnvironmentalData)
async def get_daily(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    start: date = Query(),
    end: date = Query(),
    client: NasaPowerClient = Depends(get_nasa_client),
) -> EnvironmentalData:
    return await load_environmental_data(client, latitude, longitude, start, end)
