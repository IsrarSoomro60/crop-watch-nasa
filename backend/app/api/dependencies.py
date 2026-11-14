"""FastAPI dependency providers."""

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.crop_profiles import CropProfileRepository, get_crop_profile_repository
from app.repositories.farms import InMemoryFarmRepository, farm_repository
from app.services.nasa.client import NasaPowerClient
from app.services.recommendation.recommendation_engine import RecommendationEngine
from app.services.soil.soilgrids import SoilGridsClient


def get_farm_repository() -> InMemoryFarmRepository:
    return farm_repository


def get_nasa_client(settings: Settings = Depends(get_settings)) -> NasaPowerClient:
    return NasaPowerClient(settings)


def get_recommendation_engine(
    profiles: CropProfileRepository = Depends(get_crop_profile_repository),
) -> RecommendationEngine:
    return RecommendationEngine(profiles)


def get_soil_client(settings: Settings = Depends(get_settings)) -> SoilGridsClient:
    return SoilGridsClient(settings)
