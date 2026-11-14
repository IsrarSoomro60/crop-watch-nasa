"""Fetch MODIS NDVI and SMAP soil moisture for the demo districts from NASA AppEEARS.

Needs a free NASA Earthdata account (https://urs.earthdata.nasa.gov/users/new). Put the
credentials in backend/.env (never commit it):

    EARTHDATA_USERNAME=...
    EARTHDATA_PASSWORD=...

Run from backend/:
    uv run python -m scripts.fetch_appeears [START END]     # dates YYYY-MM-DD
    uv run python -m scripts.fetch_appeears --task TASK_ID  # download a finished task

AppEEARS runs point requests as background tasks, usually a few minutes to an hour.
The script submits one task for all districts, polls until it is done, and saves every
result file to app/data/sample/appeears/<task name>/. API reference:
https://appeears.earthdatacloud.nasa.gov/api/
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

from app.core.config import Settings, get_settings
from scripts.fetch_sample_data import DEFAULT_RANGE, DEMO_DISTRICTS

API = "https://appeears.earthdatacloud.nasa.gov/api"
# Product and layer names checked against the AppEEARS product catalogue on 2026-11-14.
LAYERS = [
    {"product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI"},  # 250 m, 16-day, scale 0.0001, fill -3000
    {"product": "MOD13Q1.061", "layer": "_250m_16_days_pixel_reliability"},  # 0 good ... 3 cloudy, -1 fill
    {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone"},  # 9 km, m3/m3, fill -9999
    {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_surface"},
]
POLL_SECONDS = 30
MAX_WAIT_SECONDS = 2 * 60 * 60


def build_task(start: date, end: date, name: str) -> dict:
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start.strftime("%m-%d-%Y"), "endDate": end.strftime("%m-%d-%Y")}],
            "layers": LAYERS,
            "coordinates": [
                {"id": district.lower(), "category": "demo_district", "latitude": lat, "longitude": lon}
                for district, (lat, lon) in DEMO_DISTRICTS.items()
            ],
        },
    }


def login(http: httpx.Client, settings: Settings) -> str:
    if not settings.earthdata_username or not settings.earthdata_password:
        sys.exit("Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in backend/.env first (see this file's docstring).")
    resp = http.post(f"{API}/login", auth=(settings.earthdata_username, settings.earthdata_password),
                     headers={"Content-Length": "0"})
    if resp.status_code == 401:
        sys.exit("Earthdata login rejected: check the username and password in backend/.env.")
    resp.raise_for_status()
    return resp.json()["token"]


def run(start: date, end: date, http: httpx.Client | None = None, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    http = http or httpx.Client(timeout=120)
    token = login(http, settings)
    auth = {"Authorization": f"Bearer {token}"}
    name = f"cropwatch_{start:%Y%m%d}_{end:%Y%m%d}"

    task = http.post(f"{API}/task", json=build_task(start, end, name), headers=auth)
    task.raise_for_status()
    task_id = task.json()["task_id"]
    print(f"Submitted AppEEARS task {task_id} ({name}); polling every {POLL_SECONDS}s")

    waited = 0
    while True:
        status = http.get(f"{API}/task/{task_id}", headers=auth).json().get("status")
        print(f"  status: {status}")
        if status == "done":
            break
        if status in ("error", "expired") or waited >= MAX_WAIT_SECONDS:
            sys.exit(f"Task {task_id} ended with status {status!r}; check https://appeears.earthdatacloud.nasa.gov")
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS

    out = download(http, auth, task_id, settings.sample_data_dir / "appeears" / name)
    (out / "task.json").write_text(json.dumps({"task_id": task_id, **build_task(start, end, name)}, indent=2))
    http.post(f"{API}/logout", headers=auth)
    return out


def download(http: httpx.Client, auth: dict, task_id: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    bundle = http.get(f"{API}/bundle/{task_id}", headers=auth)
    bundle.raise_for_status()
    for f in bundle.json()["files"]:
        data = http.get(f"{API}/bundle/{task_id}/{f['file_id']}", headers=auth, follow_redirects=True)
        data.raise_for_status()
        target = out / Path(f["file_name"]).name
        target.write_bytes(data.content)
        print(f"  saved {target}")
    return out


def fetch_existing(task_id: str, http: httpx.Client | None = None, settings: Settings | None = None) -> Path:
    """Download the results of a task that was already submitted (e.g. from the AppEEARS website)."""
    settings = settings or get_settings()
    http = http or httpx.Client(timeout=120)
    auth = {"Authorization": f"Bearer {login(http, settings)}"}
    task = http.get(f"{API}/task/{task_id}", headers=auth)
    task.raise_for_status()
    info = task.json()
    if info.get("status") != "done":
        sys.exit(f"Task {task_id} status is {info.get('status')!r}, not done yet.")
    out = download(http, auth, task_id, settings.sample_data_dir / "appeears" / info.get("task_name", task_id))
    (out / "task.json").write_text(json.dumps(info, indent=2, default=str))
    http.post(f"{API}/logout", headers=auth)
    return out

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--task":
        fetch_existing(args[1])
        sys.exit(0)
    rng = (date.fromisoformat(args[0]), date.fromisoformat(args[1])) if len(args) == 2 else DEFAULT_RANGE
    run(*rng)
