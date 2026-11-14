from datetime import date, timedelta

import pytest

from app.schemas.crop import (
    CropName,
    CropProfile,
    EvidenceStatus,
    GrowthStage,
    RiskType,
    StageType,
    Threshold,
)
from app.schemas.environment import DailyObservation


@pytest.fixture
def heat_profile() -> CropProfile:
    """Synthetic profile with made-up TEST thresholds (not agricultural evidence)."""
    heat = Threshold(
        risk=RiskType.HEAT,
        variable="tmax_c",
        warning=30.0,
        critical=35.0,
        evidence_status=EvidenceStatus.PROVISIONAL,
    )
    return CropProfile(
        crop=CropName.RICE,
        display_name="Test crop",
        family="Test",
        is_legume=False,
        season="test",
        stages=[
            GrowthStage(name="veg", stage_type=StageType.VEGETATIVE, approx_days=5, thresholds=[heat]),
            GrowthStage(name="flower", stage_type=StageType.FLOWERING, approx_days=5, thresholds=[heat]),
        ],
    )


def make_observations(start: date, tmax: list[float]) -> list[DailyObservation]:
    return [DailyObservation(day=start + timedelta(days=i), tmax_c=t) for i, t in enumerate(tmax)]


@pytest.fixture(autouse=True)
def _in_memory_farms():
    """Keep API tests off the real SQLite file."""
    from app.api.dependencies import get_farm_repository
    from app.main import app
    from app.repositories.farms import InMemoryFarmRepository

    store = InMemoryFarmRepository()
    app.dependency_overrides[get_farm_repository] = lambda: store
    yield
    app.dependency_overrides.pop(get_farm_repository, None)
