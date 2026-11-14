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


def test_grace_covers_all_of_pakistan_but_not_elsewhere():
    from app.services.satellite import grace_at

    lahore = satellite_for(Location(latitude=31.55, longitude=74.34))  # not a demo district
    assert lahore is not None and lahore.district is None and not lahore.ndvi
    assert lahore.grace is not None and lahore.grace.trend_cm_per_year < 0
    karachi = grace_at(Location(latitude=24.86, longitude=67.0))  # coastal: falls back to nearest land cell
    assert karachi is not None and abs(karachi.cell_lat - 24.86) <= 1
    assert grace_at(Location(latitude=51.5, longitude=-0.1)) is None


def test_regional_water_message():
    from app.services.satellite import regional_water

    rw = regional_water(Location(latitude=30.2, longitude=71.47))
    assert rw is not None and rw.trend_cm_per_year < 0
    assert "cm per year since 2002" in rw.message and "water saving more weight" in rw.message
