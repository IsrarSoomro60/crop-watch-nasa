from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.api.dependencies import get_nasa_client, get_soil_client
from app.core.config import get_settings
from app.main import app
from app.repositories.crop_profiles import CropProfileRepository, get_crop_profile_repository
from app.schemas.crop import CropName, RiskType
from app.schemas.environment import DailyObservation
from app.schemas.farm import Location, Priorities
from app.schemas.recommendation import ComparisonRequest
from app.schemas.rotation import CropSeason, Rotation
from app.services.nasa.client import PowerResponse
from app.services.recommendation.recommendation_engine import RecommendationEngine


def _rotation(name: str, *crops: CropName) -> Rotation:
    seasons = [
        CropSeason(crop=c, sowing_date=date(2025, 6, 1), harvest_date=date(2025, 9, 30), area_hectares=1)
        for c in crops
    ]
    return Rotation(name=name, seasons=seasons)


def _request() -> ComparisonRequest:
    return ComparisonRequest(
        location=Location(latitude=30.0, longitude=73.0),
        current=_rotation("Rice-Wheat", CropName.RICE, CropName.WHEAT),
        alternatives=[
            _rotation("Maize-Wheat", CropName.MAIZE, CropName.WHEAT),
            _rotation("Mung-Wheat", CropName.MUNG_BEAN, CropName.WHEAT),
        ],
        priorities=Priorities(soil_health=1, water=0, income=0, resilience=0),
    )


def test_compare_ranks_all_rotations_and_marks_current():
    rec = RecommendationEngine(get_crop_profile_repository()).compare(_request(), observations=[])
    assert len(rec.ranked) == 3
    assert [r.rotation_name for r in rec.ranked if r.is_current] == ["Rice-Wheat"]
    # With only soil-health priority, the legume rotation ranks first.
    assert rec.ranked[0].rotation_name == "Mung-Wheat"
    assert rec.limitations


def _mild_weather() -> list[DailyObservation]:
    start = date(2025, 6, 1)
    return [DailyObservation(day=start + timedelta(days=i), tmax_c=30.0, tmin_c=20.0) for i in range(122)]


class _NoMungLimits(CropProfileRepository):
    """Profiles as shipped, except mung bean has every threshold value removed."""

    def get(self, crop):
        profile = super().get(crop)
        if crop == CropName.MUNG_BEAN:
            for stage in profile.stages:
                stage.thresholds = [t.model_copy(update={"warning": None, "critical": None}) for t in stage.thresholds]
        return profile


def test_unassessed_crop_is_not_treated_as_low_risk():
    request = _request().model_copy(update={"priorities": Priorities()})  # resilience weighted
    repo = _NoMungLimits(get_settings().crop_profiles_dir)
    rec = RecommendationEngine(repo).compare(request, _mild_weather())
    by_name = {r.rotation_name: r for r in rec.ranked}

    # Mung bean has no limits here, so its rotation gets no resilience and no overall score...
    mung = by_name["Mung-Wheat"]
    assert mung.dimension_scores.resilience is None
    assert mung.preference_score is None
    # FAOSTAT has no mung bean price, so income is missing too until the farmer enters one.
    assert mung.missing_dimensions == ["income", "resilience"]
    assert rec.ranked[-1].rotation_name == "Mung-Wheat"
    assert any("Mung-Wheat: not scored" in e and "mung_bean" in e for e in rec.explanation)

    # ...while fully assessed rotations are scored on the risks they share.
    assert rec.resilience_risks == [RiskType.COLD, RiskType.HEAT]
    assert by_name["Rice-Wheat"].preference_score is not None
    assert by_name["Maize-Wheat"].preference_score is not None


def test_partly_assessed_alternative_does_not_shrink_comparison():
    # Berseem has a cold limit but no heat limit. Adding a berseem rotation must not drop
    # heat from everyone's resilience comparison (found in live testing, Bahawalpur).
    request = _request().model_copy(update={
        "priorities": Priorities(),
        "alternatives": [
            _rotation("Maize-Wheat", CropName.MAIZE, CropName.WHEAT),
            _rotation("Rice-Berseem", CropName.RICE, CropName.BERSEEM),
        ],
    })
    rec = RecommendationEngine(get_crop_profile_repository()).compare(request, _mild_weather())
    by_name = {r.rotation_name: r for r in rec.ranked}

    assert rec.resilience_risks == [RiskType.COLD, RiskType.HEAT]
    assert by_name["Maize-Wheat"].dimension_scores.resilience is not None
    berseem = by_name["Rice-Berseem"]
    assert berseem.dimension_scores.resilience is None
    assert berseem.preference_score is None
    assert any("Rice-Berseem: not scored" in e and "berseem" in e for e in rec.explanation)


class _FakeNasaClient:
    async def fetch_daily(self, *args, **kwargs):
        payload = {"properties": {"parameter": {"T2M_MAX": {"20250601": 31.0}, "RH2M": {"20250601": -999.0}}}}
        return PowerResponse(payload, latitude=30.0, longitude=73.125)


class _NoSoilClient:
    async def get(self, point):
        return None


def test_compare_endpoint_uses_injected_client():
    app.dependency_overrides[get_nasa_client] = lambda: _FakeNasaClient()
    app.dependency_overrides[get_soil_client] = lambda: _NoSoilClient()
    try:
        resp = TestClient(app).post("/api/rotations/compare", json=_request().model_dump(mode="json"))
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ranked"]) == 3
    assert body["data_note"]["latest_observation_date"] == "2025-06-01"
    assert body["data_note"]["grid_cell_center"] == {"latitude": 30.0, "longitude": 73.125}


def test_each_strategy_is_explained():
    request = _request().model_copy(update={"priorities": Priorities()})
    rec = RecommendationEngine(get_crop_profile_repository()).compare(request, _mild_weather())
    by_name = {r.rotation_name: r for r in rec.ranked}

    current = by_name["Rice-Wheat"].strategy
    assert current.why_considered[0].startswith("Your current rotation")
    assert current.benefits == []

    mung = by_name["Mung-Wheat"].strategy
    assert "Replaces rice with mung bean." in mung.why_considered
    assert any("legume (mung bean)" in b and "not proof" in b for b in mung.benefits)
    assert any("Mung bean limits:" in e and "Feedipedia" in e for e in mung.evidence)
    assert any("Income not assessed" in g for g in mung.information_gaps)
    assert any("Market demand, seed and equipment for mung bean" in n for n in mung.needs_local_review)
    assert all(r.strategy for r in rec.ranked)
