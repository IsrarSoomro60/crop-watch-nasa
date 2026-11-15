import asyncio
import json
from datetime import date

import httpx
import pytest

from app.core.config import Settings
from app.services.nasa.client import NasaPowerClient, _TTLCache, sample_path, snap_to_grid
from app.services.nasa.data_processor import parse_power_daily

PAYLOAD = {"properties": {"parameter": {
    "T2M_MAX": {"20260301": 33.0, "20260302": -999.0},
    "WS2M": {"20260301": 2.5, "20260302": 3.0},
    "GWETTOP": {"20260301": 0.4, "20260302": 0.38},
}}}


def test_snap_to_grid_cell_centres():
    assert snap_to_grid(30.20, 71.47) == (30.0, 71.25)
    assert snap_to_grid(30.26, 71.6) == (30.5, 71.875)
    assert snap_to_grid(-0.2, 179.9) == (-0.0, -180.0)  # wraps at the antimeridian


def test_parse_new_parameters_and_fill_values():
    obs = parse_power_daily(PAYLOAD)
    assert obs[0].wind_speed_ms == 2.5 and obs[0].surface_soil_moisture == 0.4
    assert obs[1].tmax_c is None  # -999 fill value


def _client(handler, tmp_path, cache=None):
    settings = Settings(sample_data_dir=tmp_path)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NasaPowerClient(settings, http=http, cache=cache or _TTLCache())


def test_cache_hits_by_grid_cell(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.params["latitude"])
        return httpx.Response(200, json=PAYLOAD)

    client = _client(handler, tmp_path)
    args = (date(2026, 3, 1), date(2026, 3, 2))
    first = asyncio.run(client.fetch_daily(30.20, 71.47, *args))
    second = asyncio.run(client.fetch_daily(30.10, 71.30, *args))  # same cell
    assert len(calls) == 1 and calls[0] == "30.0"
    assert not first.from_cache and second.from_cache


def test_falls_back_to_sample_when_nasa_unreachable(tmp_path):
    sample = {"properties": {"parameter": {"T2M_MAX": {"20260228": 30.0, "20260301": 31.0}}}}
    sample_path(tmp_path, 30.0, 71.25).write_text(json.dumps(sample))

    def handler(request):
        raise httpx.ConnectError("offline")

    client = _client(handler, tmp_path)
    resp = asyncio.run(client.fetch_daily(30.2, 71.47, date(2026, 3, 1), date(2026, 3, 1)))
    assert resp.from_sample
    assert resp.payload["properties"]["parameter"]["T2M_MAX"] == {"20260301": 31.0}

    with pytest.raises(httpx.ConnectError):  # no sample for this cell
        asyncio.run(client.fetch_daily(10.0, 10.0, date(2026, 3, 1), date(2026, 3, 1)))


LONG = {"properties": {"parameter": {"T2M_MAX": {f"202603{d:02d}": 30.0 + d for d in range(1, 11)}}}}


def test_longer_download_answers_shorter_request_and_survives_restart(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=LONG)

    settings = Settings(sample_data_dir=tmp_path, disk_cache=True, cache_dir=tmp_path / "cache")

    def client(cache):
        return NasaPowerClient(settings, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), cache=cache)

    memory = _TTLCache()
    asyncio.run(client(memory).fetch_daily(30.2, 71.47, date(2026, 3, 1), date(2026, 3, 10)))
    short = asyncio.run(client(memory).fetch_daily(30.2, 71.47, date(2026, 3, 3), date(2026, 3, 4)))
    assert len(calls) == 1 and short.from_cache
    assert list(short.payload["properties"]["parameter"]["T2M_MAX"]) == ["20260303", "20260304"]

    after_restart = asyncio.run(client(_TTLCache()).fetch_daily(30.2, 71.47, date(2026, 3, 2), date(2026, 3, 5)))
    assert len(calls) == 1 and after_restart.from_cache  # read from the disk copy
    assert len(after_restart.payload["properties"]["parameter"]["T2M_MAX"]) == 4
