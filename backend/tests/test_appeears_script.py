from datetime import date

import httpx
import pytest

from app.core.config import Settings
from scripts import fetch_appeears


def test_task_payload_matches_appeears_point_format():
    task = fetch_appeears.build_task(date(2025, 6, 1), date(2026, 5, 31), "t")
    assert task["task_type"] == "point"
    assert task["params"]["dates"] == [{"startDate": "06-01-2025", "endDate": "05-31-2026"}]
    assert {c["id"] for c in task["params"]["coordinates"]} == {"multan", "bahawalpur", "larkana", "hyderabad"}
    assert {"product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI"} in task["params"]["layers"]


def test_full_flow_against_mock_api(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_appeears, "POLL_SECONDS", 0)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api")
        seen.append((request.method, path))
        if path == "/login":
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"token": "tok"})
        assert request.headers["authorization"] == "Bearer tok"
        if path == "/task" and request.method == "POST":
            return httpx.Response(202, json={"task_id": "abc"})
        if path == "/task/abc":
            done = sum(1 for _, p in seen if p == "/task/abc") > 1
            return httpx.Response(200, json={"status": "done" if done else "processing"})
        if path == "/bundle/abc":
            return httpx.Response(200, json={"files": [{"file_id": "f1", "file_name": "x/MOD13Q1-061-results.csv"}]})
        if path == "/bundle/abc/f1":
            return httpx.Response(200, content=b"ID,Date,NDVI\n")
        if path == "/logout":
            return httpx.Response(204)
        return httpx.Response(404)

    settings = Settings(sample_data_dir=tmp_path, earthdata_username="u", earthdata_password="p")
    out = fetch_appeears.run(date(2025, 6, 1), date(2025, 6, 30),
                             http=httpx.Client(transport=httpx.MockTransport(handler)), settings=settings)
    assert (out / "MOD13Q1-061-results.csv").read_bytes() == b"ID,Date,NDVI\n"
    assert (out / "task.json").exists()


def test_missing_credentials_exit_with_instructions(tmp_path):
    with pytest.raises(SystemExit, match="EARTHDATA_USERNAME"):
        fetch_appeears.run(date(2025, 6, 1), date(2025, 6, 2), http=httpx.Client(),
                           settings=Settings(sample_data_dir=tmp_path, earthdata_username=None, earthdata_password=None,
                                             _env_file=None))
