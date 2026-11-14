"""Evaluates a full rotation: per-crop risks plus area-weighted rotation risk."""

from app.domain.scoring_config import PROVISIONAL_NOTE
from app.repositories.crop_profiles import CropProfileRepository
from app.schemas.crop import RiskType
from app.schemas.environment import DailyObservation
from app.schemas.rotation import Rotation, RotationEvaluation
from app.services.risk.risk_calculator import area_weighted_risk
from app.services.risk.risk_engine import RiskEngine
from app.services.rotation.ground_cover import ground_cover
from app.services.water.crop_water import rotation_water


class RotationEvaluator:
    def __init__(self, profiles: CropProfileRepository, engine: RiskEngine | None = None):
        self._profiles = profiles
        self._engine = engine or RiskEngine()

    def evaluate(
        self,
        rotation: Rotation,
        observations: list[DailyObservation],
        latitude: float | None = None,
        elevation_m: float | None = None,
        soil_texture: str | None = None,
        water_fallback: dict | None = None,
    ) -> RotationEvaluation:
        results = [
            self._engine.assess(self._profiles.get(season.crop), season, observations)
            for season in rotation.seasons
        ]
        areas = [s.area_hectares for s in rotation.seasons]
        weighted = {
            risk: round(area_weighted_risk([r.risks[risk] for r in results], areas), 2)
            for risk in RiskType
        }
        return RotationEvaluation(
            rotation_name=rotation.name,
            crop_results=results,
            area_weighted_risk=weighted,
            highest_crop_season_risk=max(r.max_risk for r in results),
            assumptions=[PROVISIONAL_NOTE],
            water=None if latitude is None else rotation_water(
                {s.crop: self._profiles.get(s.crop) for s in rotation.seasons},
                rotation.seasons, observations, latitude, elevation_m or 0.0, soil_texture, water_fallback,
            ),
            ground_cover=ground_cover(rotation),
        )
