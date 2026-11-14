from datetime import date, timedelta

from app.repositories.advice import get_advice_repository
from app.repositories.crop_profiles import get_crop_profile_repository
from app.schemas.crop import CropName, RiskLevel, RiskType, StageType
from app.schemas.environment import DailyObservation, DataNote
from app.schemas.farm import Location
from app.schemas.quick_check import QuickCheckRequest
from app.services.quick_check import current_stage, quick_check

MULTAN = Location(latitude=30.2, longitude=71.47)
LATEST = date(2027, 3, 20)


def _note() -> DataNote:
    return DataNote(grid_cell_center=MULTAN, requested_start=LATEST - timedelta(days=30), requested_end=LATEST,
                    latest_observation_date=LATEST)


def _days(tmax: list[float], tmin: float = 12.0) -> list[DailyObservation]:
    start = LATEST - timedelta(days=len(tmax) - 1)
    return [DailyObservation(day=start + timedelta(days=i), tmax_c=t, tmin_c=tmin) for i, t in enumerate(tmax)]


def _run(request: QuickCheckRequest, obs: list[DailyObservation]):
    profile = get_crop_profile_repository().get(request.crop)
    return quick_check(profile, request, obs, _note(), get_advice_repository())


def test_brief_worked_example_wheat_grain_filling_heat():
    # Brief section 2: wheat at grain filling in Multan, 33, 34, 35 °C over the last three days -> High.
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, sowing_date=date(2026, 11, 20))
    result = _run(req, _days([24, 24, 24, 24, 33, 34, 35]))

    assert result.stage == StageType.REPRODUCTIVE  # day 121; FAO mid-season is days 61-125
    assert result.overall == RiskLevel.HIGH
    card = result.cards[0]
    assert card.risk == RiskType.HEAT and card.level == RiskLevel.HIGH and card.days_beyond_limit == 3
    assert card.reason == ("Max temperature 35°C on 20 Mar is above the wheat limit of 32°C "
                           "at the reproductive stage.")
    assert result.advice[0].text_en == "Irrigate lightly to cool the crop."
    assert len(result.last_7_days) == 7


def test_three_moderate_days_in_a_row_escalate_to_high():
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, stage=StageType.REPRODUCTIVE)
    result = _run(req, _days([24, 24, 24, 24, 27, 28, 29]))  # above 25, below 32
    heat = result.cards[0]
    assert heat.level == RiskLevel.HIGH and "Moderate for 3 days in a row" in heat.reason

    two = _run(req, _days([24, 24, 24, 24, 24, 28, 29]))
    assert two.cards[0].level == RiskLevel.MODERATE


def test_cool_week_is_low_and_unassessed_risks_are_listed():
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, stage=StageType.VEGETATIVE)
    result = _run(req, _days([20] * 7))
    assert result.overall == RiskLevel.LOW and result.cards == []
    assert RiskType.DROUGHT in result.not_assessed


def test_stage_from_sowing_date_and_fallbacks():
    wheat = get_crop_profile_repository().get(CropName.WHEAT)  # 25/35/65/40 days
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, sowing_date=date(2027, 3, 1))
    assert current_stage(wheat, req, date(2027, 3, 10))[0] == StageType.ESTABLISHMENT
    assert current_stage(wheat, req, date(2027, 2, 1))[1] == "sowing date is in the future"
    assert current_stage(wheat, req, date(2028, 1, 1))[0] is None  # past the 165-day season

    no_stage = _run(QuickCheckRequest(location=MULTAN, crop=CropName.RICE), _days([36] * 7, tmin=26))
    assert no_stage.stage is None
    assert no_stage.overall == RiskLevel.HIGH  # rice heat limit is the same in every stage that sets one
    assert any("sowing date" in n for n in no_stage.notes)


def test_unsupported_stage_is_rejected_before_any_download():
    from fastapi.testclient import TestClient

    from app.main import app

    body = {"location": {"latitude": 30.2, "longitude": 71.47}, "crop": "berseem", "stage": "reproductive"}
    r = TestClient(app).post("/api/quick-check", json=body)
    assert r.status_code == 422
    assert "supported stages: establishment, vegetative" in r.text


def test_missing_thresholds_report_not_assessed_never_low():
    # Weather with no temperature limits that apply: every risk is not assessed, overall is null.
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, stage=StageType.MATURITY)
    result = _run(req, _days([45, 45, 45, 45, 45, 45, 45], tmin=-10))  # extreme, but wheat maturity has no limits

    assert result.overall is None and result.cards == [] and result.assessed == []
    assert set(result.not_assessed) == set(RiskType)
    assert any(n.startswith("Not assessed:") and "not a 'no risk' result" in n for n in result.notes)


def test_assessed_lists_only_risks_checked():
    req = QuickCheckRequest(location=MULTAN, crop=CropName.WHEAT, stage=StageType.VEGETATIVE)
    result = _run(req, _days([20] * 7, tmin=5))
    assert result.overall == RiskLevel.LOW
    assert set(result.assessed) == {RiskType.HEAT, RiskType.COLD}
    assert RiskType.DISEASE in result.not_assessed and not any(n.startswith("Not assessed:") for n in result.notes)
