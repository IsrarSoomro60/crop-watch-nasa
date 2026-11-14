from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_farm_repository
from app.repositories.farms import InMemoryFarmRepository
from app.schemas.farm import Farm, FarmCreate

router = APIRouter(prefix="/farms", tags=["farms"])


@router.post("", response_model=Farm, status_code=status.HTTP_201_CREATED)
def create_farm(data: FarmCreate, repo: InMemoryFarmRepository = Depends(get_farm_repository)) -> Farm:
    return repo.create(data)


@router.get("", response_model=list[Farm])
def list_farms(repo: InMemoryFarmRepository = Depends(get_farm_repository)) -> list[Farm]:
    return repo.list()


@router.get("/{farm_id}", response_model=Farm)
def get_farm(farm_id: str, repo: InMemoryFarmRepository = Depends(get_farm_repository)) -> Farm:
    farm = repo.get(farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm
