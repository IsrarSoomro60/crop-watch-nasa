"""Loads crop profiles from the JSON files in app/domain/crop_profiles."""

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.schemas.crop import CropName, CropProfile


class CropProfileRepository:
    def __init__(self, profiles_dir: Path):
        self._dir = profiles_dir

    def get(self, crop: CropName) -> CropProfile:
        path = self._dir / f"{crop.value}.json"
        return CropProfile.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[CropProfile]:
        return [self.get(c) for c in CropName]


@lru_cache
def get_crop_profile_repository() -> CropProfileRepository:
    return CropProfileRepository(get_settings().crop_profiles_dir)
