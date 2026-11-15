from fastapi import APIRouter, HTTPException, Query

from app.schemas.farm import Location
from app.schemas.satellite import SatelliteData
from app.services.satellite import MAX_DISTANCE_KM, satellite_for

router = APIRouter(prefix="/satellite", tags=["satellite"])


@router.get("", response_model=SatelliteData)
def get_satellite(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> SatelliteData:
    data = satellite_for(Location(latitude=latitude, longitude=longitude))
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Outside Pakistan (GRACE grid) and more than {MAX_DISTANCE_KM:.0f} km from a demo district",
        )
    return data
