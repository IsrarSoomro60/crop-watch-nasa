from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_soil_client
from app.schemas.farm import Location
from app.schemas.soil import SoilInfo
from app.services.soil.soilgrids import SoilGridsClient

router = APIRouter(prefix="/soil", tags=["soil"])


@router.get("", response_model=SoilInfo)
async def get_soil(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    client: SoilGridsClient = Depends(get_soil_client),
) -> SoilInfo:
    info = await client.get(Location(latitude=latitude, longitude=longitude))
    if info is None:
        raise HTTPException(status_code=404, detail="No SoilGrids data within ~5 km and no saved sample nearby")
    return info
