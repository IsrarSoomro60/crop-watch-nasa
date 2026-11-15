from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_soil_client
from app.schemas.farm import Location
from app.schemas.soil import SoilInfo
from app.services.soil.soilgrids import SoilGridsClient, SoilGridsUnavailable

router = APIRouter(prefix="/soil", tags=["soil"])


@router.get("", response_model=SoilInfo)
async def get_soil(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    client: SoilGridsClient = Depends(get_soil_client),
) -> SoilInfo:
    try:
        info = await client.get(Location(latitude=latitude, longitude=longitude))
    except SoilGridsUnavailable as exc:
        # The service is down or slow: say so, rather than claiming there is no soil data here.
        raise HTTPException(
            status_code=503,
            detail="The SoilGrids soil service is not responding right now. Try again in a few minutes.",
        ) from exc
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="SoilGrids has no soil data within about 5 km of this point (often a town, river or "
            "desert). Pick a field nearby.",
        )
    return info
