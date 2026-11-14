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
            status_code=404, detail=f"No saved satellite sample within {MAX_DISTANCE_KM:.0f} km (demo districts only)"
        )
    return data
