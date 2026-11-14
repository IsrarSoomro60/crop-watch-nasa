from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.api.dependencies import get_nasa_client
from app.api.routes.environmental_data import load_environmental_data
from app.repositories.advice import get_advice_repository
from app.repositories.crop_profiles import CropProfileRepository, get_crop_profile_repository
from app.schemas.quick_check import QuickCheckRequest, QuickCheckResult
from app.services.nasa.client import NasaPowerClient
from app.services.quick_check import quick_check

router = APIRouter(prefix="/quick-check", tags=["quick check"])

LOOKBACK_DAYS = 30  # NASA POWER lags 2-3 days; 30 days leaves room for the 7-day window


@router.post("", response_model=QuickCheckResult)
async def run_quick_check(
    request: QuickCheckRequest,
    nasa: NasaPowerClient = Depends(get_nasa_client),
    profiles: CropProfileRepository = Depends(get_crop_profile_repository),
) -> QuickCheckResult:
    end = date.today()
    env = await load_environmental_data(
        nasa, request.location.latitude, request.location.longitude, end - timedelta(days=LOOKBACK_DAYS), end
    )
    return quick_check(profiles.get(request.crop), request, env.observations, env.data_note, get_advice_repository())
