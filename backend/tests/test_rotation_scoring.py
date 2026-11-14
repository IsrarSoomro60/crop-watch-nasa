import pytest

from app.schemas.farm import Priorities
from app.schemas.recommendation import DimensionScores
from app.services.rotation.scoring import normalise_weights, preference_score, risk_to_resilience


def test_weights_normalise_to_one():
    weights = normalise_weights(Priorities(soil_health=2, water=1, income=1, resilience=0))
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["soil_health"] == pytest.approx(0.5)


def test_missing_dimensions_are_excluded_not_zeroed():
    scores = DimensionScores(soil_health=0.8, resilience=0.4)
    # Equal priorities -> only the two available dimensions count, equally.
    assert preference_score(scores, Priorities()) == pytest.approx(0.6)


def test_no_available_dimensions_returns_none():
    assert preference_score(DimensionScores(), Priorities()) is None


def test_risk_to_resilience_is_clamped():
    assert risk_to_resilience(0) == 1.0
    assert risk_to_resilience(100) == 0.0
    assert risk_to_resilience(150) == 0.0
