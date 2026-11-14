import httpx
from fastapi import APIRouter, Depends

from app.api.dependencies import get_nasa_client, get_recommendation_engine, get_soil_client
from app.api.routes.environmental_data import load_environmental_data
from app.api.routes.history import run_history
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
    env = await load_environmental_data(
        client,
        request.location.latitude,
        request.location.longitude,
        min(s.sowing_date for s in seasons),
        max(s.harvest_date for s in seasons),
    )
    soil: SoilInfo | None = None
    try:
        soil = await soil_client.get(request.location)
    except httpx.HTTPError:
        soil = None  # soil is optional context; the comparison still runs without it
    # Seasons that end after the latest weather (e.g. next season) get the historical median water need.
    latest = env.data_note.latest_observation_date
    future = [s for s in seasons if latest is None or s.harvest_date > latest]
    fallback = None
    if future:
        texture = soil.texture_class if soil else None
        histories, _, _, _ = await run_history(request.location, future, client, _profiles(), texture)
        by_md = {(h.crop, h.sowing_month_day, h.harvest_month_day): h.water for h in histories}
        fallback = {
            (s.crop, s.sowing_date, s.harvest_date): by_md.get((s.crop, s.sowing_date.strftime("%m-%d"),
                                                                 s.harvest_date.strftime("%m-%d")))
            for s in future
        }
        fallback = {k: v for k, v in fallback.items() if v is not None}
    recommendation = engine.compare(
        request, env.observations, elevation_m=env.data_note.elevation_m, soil=soil, water_fallback=fallback
    )
    recommendation.data_note = env.data_note
    return recommendation
