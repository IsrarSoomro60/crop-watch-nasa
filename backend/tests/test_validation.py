from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.crop import CropName
from app.schemas.rotation import CropSeason


def _season(sow: str, harvest: str) -> dict:
    return {"crop": "wheat", "sowing_date": sow, "harvest_date": harvest, "area_hectares": 1}


@pytest.mark.parametrize("harvest", [date(2025, 11, 1), date(2025, 10, 31)])
def test_harvest_on_or_before_sowing_is_rejected(harvest):
    with pytest.raises(ValidationError, match="must be after sowing date"):
        CropSeason(crop=CropName.WHEAT, sowing_date=date(2025, 11, 1), harvest_date=harvest, area_hectares=1)


def test_valid_season_still_accepted():
    s = CropSeason(crop=CropName.WHEAT, sowing_date=date(2025, 11, 1), harvest_date=date(2026, 4, 1), area_hectares=1)
    assert (s.harvest_date - s.sowing_date).days == 151


def test_compare_endpoint_returns_422_for_reversed_dates():
    body = {
        "location": {"latitude": 30.2, "longitude": 71.47},
        "current": {"name": "Bad", "seasons": [_season("2026-04-01", "2025-11-01")]},
        "alternatives": [
            {"name": "A", "seasons": [_season("2025-11-01", "2026-04-01")]},
            {"name": "B", "seasons": [_season("2025-11-01", "2026-04-01")]},
        ],
    }
    r = TestClient(app).post("/api/rotations/compare", json=body)
    assert r.status_code == 422
    assert "must be after sowing date" in r.text
