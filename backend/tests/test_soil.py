import asyncio
import json
from datetime import date

import httpx
import pytest

from app.core.config import Settings
from app.schemas.crop import CropName
from app.schemas.farm import Location
from app.schemas.rotation import CropSeason, Rotation
from app.services.rotation.ground_cover import ground_cover
from app.services.soil import soilgrids
from app.services.soil.soilgrids import SoilGridsClient, usda_texture
from app.services.water.crop_water import paddy_percolation


@pytest.mark.parametrize(
    ("clay", "sand", "silt", "expected"),
    [
        (23.5, 45.9, 30.6, "loam"),  # SoilGrids topsoil near Multan
        (31.6, 16.6, 51.8, "silty clay loam"),  # near Hyderabad
        (45, 15, 40, "silty clay"),
        (50, 30, 20, "clay"),
        (10, 80, 10, "sandy loam"),
        (3, 92, 5, "sand"),
        (30, 60, 10, "sandy clay loam"),
        (5, 15, 80, "silt"),
    ],
)
def test_usda_texture_classes(clay, sand, silt, expected):
    assert usda_texture(clay, sand, silt) == expected


def _payload(lat, lon, clay):
    def layer(name, value):
        return {"name": name, "depths": [
            {"range": {"top_depth": t, "bottom_depth": b}, "label": f"{t}-{b}cm", "values": {"mean": value}}
            for t, b in ((0, 5), (5, 15), (15, 30))
        ]}
    v = None if clay is None else clay * 10
    return {"geometry": {"coordinates": [lon, lat]}, "properties": {"layers": [
        layer("clay", v), layer("sand", None if v is None else 459), layer("silt", None if v is None else 306),
        layer("soc", None if v is None else 52), layer("phh2o", None if v is None else 81),
        layer("bdod", None if v is None else 152),
    ]}}


def _client(tmp_path, handler) -> SoilGridsClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SoilGridsClient(Settings(sample_data_dir=tmp_path), http=http)


@pytest.fixture(autouse=True)
def _clear_cache():
    soilgrids._cache.clear()
    soilgrids._failed.clear()
    yield
    soilgrids._cache.clear()
    soilgrids._failed.clear()


def test_steps_out_from_built_up_point_and_converts_units(tmp_path):
    calls = []

    def handler(request):
        lat, lon = float(request.url.params["lat"]), float(request.url.params["lon"])
        calls.append((lat, lon))
        return httpx.Response(200, json=_payload(lat, lon, None if len(calls) == 1 else 23.5))

    client = _client(tmp_path, handler)
    info = asyncio.run(client.get(Location(latitude=30.2, longitude=71.47)))

    assert len(calls) == 2  # town centre had no data; first step out did
    assert info.used_location == Location(latitude=30.25, longitude=71.47)
    assert info.distance_km == pytest.approx(5.6, abs=0.1)
    top = info.topsoil_0_30cm
    assert (top.clay_pct, top.sand_pct, top.organic_carbon_g_kg, top.ph_h2o, top.bulk_density_kg_dm3) == (
        23.5, 45.9, 5.2, 8.1, 1.52)
    assert info.texture_class == "loam"
    assert any("5.6 km away" in n for n in info.notes)

    asyncio.run(client.get(Location(latitude=30.2, longitude=71.47)))
    assert len(calls) == 2  # cached


def test_uses_nearest_saved_sample_when_unreachable(tmp_path):
    (tmp_path / "soilgrids_30.250_71.470.json").write_text(json.dumps(_payload(30.25, 71.47, 23.5)))

    def handler(request):
        raise httpx.ConnectError("offline")

    client = _client(tmp_path, handler)
    info = asyncio.run(client.get(Location(latitude=30.2, longitude=71.47)))
    assert info.from_sample and info.texture_class == "loam"
    assert asyncio.run(client.get(Location(latitude=25.0, longitude=68.0))) is None  # no sample within 25 km


def test_paddy_percolation_follows_texture():
    assert paddy_percolation("clay")[0] == 4.0
    assert paddy_percolation("sandy loam")[0] == 8.0
    assert paddy_percolation("loam")[0] == 6.0
    assert paddy_percolation(None) == (6.0, "FAO average; soil texture unknown")


def test_ground_cover_counts_bare_days():
    def s(crop, a, b):
        return CropSeason(crop=crop, sowing_date=a, harvest_date=b, area_hectares=1)

    rice_wheat = Rotation(name="RW", seasons=[
        s(CropName.RICE, date(2025, 6, 15), date(2025, 10, 15)),  # 123 days
        s(CropName.WHEAT, date(2025, 11, 15), date(2026, 4, 15)),  # 152 days
    ])
    gc = ground_cover(rice_wheat)
    assert gc.bare_soil_days == 365 - 123 - 152
    assert gc.cover_fraction == round(275 / 365, 3)


def test_answers_are_saved_to_disk_including_no_data(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        lat, lon = float(request.url.params["lat"]), float(request.url.params["lon"])
        clay = None if lat > 31 else 23.5  # "city" with no data around 31.5
        return httpx.Response(200, json=_payload(lat, lon, clay))

    settings = Settings(sample_data_dir=tmp_path, disk_cache=True, cache_dir=tmp_path / "cache")

    def client():
        return SoilGridsClient(settings, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    farm, city = Location(latitude=30.2, longitude=71.47), Location(latitude=31.5, longitude=74.3)
    assert asyncio.run(client().get(farm)).texture_class
    assert asyncio.run(client().get(city)) is None
    n = len(calls)

    soilgrids._cache.clear()  # as after a server restart: only the disk copy is left
    assert asyncio.run(client().get(farm)).texture_class
    assert asyncio.run(client().get(city)) is None
    assert len(calls) == n  # nothing downloaded again


def test_failure_is_remembered_so_repeats_do_not_wait_again(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("SoilGrids hung")

    client = _client(tmp_path, handler)
    point = Location(latitude=30.2, longitude=71.47)
    assert asyncio.run(client.get(point)) is None  # no saved sample in tmp_path
    asyncio.run(client.get(point))
    assert len(calls) == 1  # second call used the remembered failure
