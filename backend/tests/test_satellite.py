from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.farm import Location
from app.schemas.satellite import GracePoint
from app.services.satellite import grace_trend, satellite_for

client = TestClient(app)


def test_multan_sample_has_all_three_sources():
    d = satellite_for(Location(latitude=30.2, longitude=71.47))
    assert d is not None and d.district == "Multan"
    assert len(d.ndvi) >= 20 and len(d.soil_moisture) >= 300
    assert d.grace is not None and len(d.grace.series) > 200
    assert all(0 < p.rootzone_m3m3 < 0.6 for p in d.soil_moisture)
    assert all(p.usable == (p.ndvi is not None and p.reliability in (0, 1)) for p in d.ndvi)


def test_far_location_returns_404():
    assert satellite_for(Location(latitude=0, longitude=0)) is None
    r = client.get("/api/satellite", params={"latitude": 0, "longitude": 0})
    assert r.status_code == 404


def test_endpoint_returns_limitations():
    r = client.get("/api/satellite", params={"latitude": 29.4, "longitude": 71.68})
    assert r.status_code == 200
    assert r.json()["district"] == "Bahawalpur" and r.json()["limitations"]


def test_grace_trend_recovers_linear_slope():
    pts = [GracePoint(date=date(2003 + m // 12, m % 12 + 1, 15), lwe_cm=-1.5 * m / 12, uncertainty_cm=1)
           for m in range(60)]
    assert abs(grace_trend(pts) - -1.5) < 0.01
    assert grace_trend(pts[:10]) is None
