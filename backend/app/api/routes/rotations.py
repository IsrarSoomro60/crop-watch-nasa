import asyncio

import httpx
from fastapi import APIRouter, Depends

from app.api.dependencies import get_nasa_client, get_recommendation_engine, get_soil_client
from app.api.routes.environmental_data import load_environmental_data
from app.api.routes.history import likely_future, prefetch_history_weather, run_history
from app.repositories.crop_profiles import CropProfileRepository, get_crop_profile_repository
from app.repositories.crop_profiles import get_crop_profile_repository as _profiles
from app.schemas.crop import CropProfile
from app.schemas.recommendation import ComparisonRequest, Recommendation
from app.schemas.soil import SoilInfo
from app.services.nasa.client import NasaPowerClient
from app.services.recommendation.recommendation_engine import RecommendationEngine
from app.services.soil.soilgrids import SoilGridsClient

router = APIRouter(prefix="/rotations", tags=["rotations"])


@router.get("/crop-profiles", response_model=list[CropProfile])
def list_crop_profiles(
    repo: CropProfileRepository = Depends(get_crop_profile_repository),
) -> list[CropProfile]:
    return repo.list()


@router.post("/compare", response_model=Recommendation)
async def compare_rotations(
    request: ComparisonRequest,
    client: NasaPowerClient = Depends(get_nasa_client),
    engine: RecommendationEngine = Depends(get_recommendation_engine),
    soil_client: SoilGridsClient = Depends(get_soil_client),
) -> Recommendation:
    seasons = [s for r in [request.current, *request.alternatives] for s in r.seasons]

    async def get_soil() -> SoilInfo | None:
        try:
            return await soil_client.get(request.location)
        except httpx.HTTPError:
            return None  # soil is optional context; the comparison still runs without it

    # Weather, soil and (for seasons with no weather yet) 20 years of history are independent
    # downloads, so they run at the same time instead of one after another.
    env, soil, _ = await asyncio.gather(
        load_environmental_data(
            client,
            request.location.latitude,
            request.location.longitude,
            min(s.sowing_date for s in seasons),
            max(s.harvest_date for s in seasons),
        ),
        get_soil(),
        prefetch_history_weather(request.location, likely_future(seasons), client),
    )
    # Seasons that end after the latest weather (e.g. next season) get the historical median water need
    # and the typical (mean) risk of the same dates in past years.
    latest = env.data_note.latest_observation_date
    future = [s for s in seasons if latest is None or s.harvest_date > latest]
    fallback = risk_fallback = None
    if future:
        texture = soil.texture_class if soil else None
        histories, _, _, _ = await run_history(request.location, future, client, _profiles(), texture)
        by_md = {(h.crop, h.sowing_month_day, h.harvest_month_day): h for h in histories}
        matched = {
            (s.crop, s.sowing_date, s.harvest_date): by_md.get((s.crop, s.sowing_date.strftime("%m-%d"),
                                                                 s.harvest_date.strftime("%m-%d")))
            for s in future
        }
        fallback = {k: h.water for k, h in matched.items() if h is not None and h.water is not None}
        risk_fallback = {k: h for k, h in matched.items() if h is not None and h.per_year}
    recommendation = engine.compare(
        request, env.observations, elevation_m=env.data_note.elevation_m, soil=soil, water_fallback=fallback,
        risk_fallback=risk_fallback,
    )
    recommendation.data_note = env.data_note
    return recommendation
