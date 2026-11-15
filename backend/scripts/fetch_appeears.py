"""Fetch NASA AppEEARS data for the demo districts.

Sets: satellite (default: MODIS NDVI + SMAP soil moisture), field (ECOSTRESS land-surface temperature and
evapotranspiration, HLS Landsat/Sentinel-2 NDVI at 30 m), terrain (NASADEM elevation boxes for slope).

Needs a free NASA Earthdata account (https://urs.earthdata.nasa.gov/users/new). Put the
credentials in backend/.env (never commit it):

    EARTHDATA_USERNAME=...
    EARTHDATA_PASSWORD=...

Run from backend/:
    uv run python -m scripts.fetch_appeears [START END]     # dates YYYY-MM-DD
    uv run python -m scripts.fetch_appeears --set field START END
    uv run python -m scripts.fetch_appeears --set terrain
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
# Field-scale set (checked against the AppEEARS catalogue on 2026-11-15). ECOSTRESS revisits are irregular
# (ISS orbit) and often cloudy; the cloud layers are kept so cloudy readings can be dropped.
FIELD_LAYERS = [
    {"product": "ECO_L2T_LSTE.002", "layer": "LST"},  # 70 m land-surface temperature, Kelvin
    {"product": "ECO_L2T_LSTE.002", "layer": "cloud"},  # 1 = cloud
    {"product": "ECO_L3T_JET.002", "layer": "ETdaily"},  # 70 m daily evapotranspiration
    {"product": "ECO_L3T_JET.002", "layer": "cloud"},
    {"product": "HLSL30_VI.020", "layer": "NDVI"},  # Landsat 8/9, 30 m, scale 0.0001, fill -19999
    {"product": "HLSS30_VI.020", "layer": "NDVI"},  # Sentinel-2, 30 m
    {"product": "HLSL30.020", "layer": "Fmask"},  # cloud / shadow bits for the NDVI above
    {"product": "HLSS30.020", "layer": "Fmask"},
]
LAYER_SETS = {"satellite": LAYERS, "field": FIELD_LAYERS}
# Terrain is static, so it is an area task: slope needs neighbouring pixels, not one point.
TERRAIN_LAYERS = [{"product": "NASADEM_NC.001", "layer": "NASADEM_HGT"}]  # 30 m elevation, metres
TERRAIN_HALF_BOX_DEG = 0.05  # ~11 km x 11 km around each district point
POLL_SECONDS = 30
MAX_WAIT_SECONDS = 2 * 60 * 60


def build_terrain_task(name: str) -> dict:
    features = []
    for district, (lat, lon) in DEMO_DISTRICTS.items():
        d = TERRAIN_HALF_BOX_DEG
        ring = [[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]
        features.append({"type": "Feature", "properties": {"id": district.lower()},
                         "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [{"startDate": "02-11-2000", "endDate": "02-21-2000"}],  # the SRTM/NASADEM mission
            "layers": TERRAIN_LAYERS,
            "geo": {"type": "FeatureCollection", "features": features},
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
        },
    }


def build_task(start: date, end: date, name: str, layers: list[dict] | None = None) -> dict:
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start.strftime("%m-%d-%Y"), "endDate": end.strftime("%m-%d-%Y")}],
            "layers": layers or LAYERS,
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


def run(start: date, end: date, http: httpx.Client | None = None, settings: Settings | None = None,
        layer_set: str = "satellite") -> Path:
    settings = settings or get_settings()
    http = http or httpx.Client(timeout=120)
    token = login(http, settings)
    auth = {"Authorization": f"Bearer {token}"}
    if layer_set == "terrain":
        name = "cropwatch_terrain_nasadem"
        body = build_terrain_task(name)
    else:
        prefix = "cropwatch" if layer_set == "satellite" else f"cropwatch_{layer_set}"
        name = f"{prefix}_{start:%Y%m%d}_{end:%Y%m%d}"
        body = build_task(start, end, name, LAYER_SETS[layer_set])

    task = http.post(f"{API}/task", json=body, headers=auth)
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
    (out / "task.json").write_text(json.dumps({"task_id": task_id, **body}, indent=2))
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
    # --set satellite (default: MODIS NDVI + SMAP) | field (ECOSTRESS + HLS) | terrain (NASADEM area, no dates)
    layer_set = "satellite"
    if len(args) >= 2 and args[0] == "--set":
        layer_set, args = args[1], args[2:]
        if layer_set not in (*LAYER_SETS, "terrain"):
            sys.exit(f"Unknown set {layer_set!r}; use satellite, field or terrain.")
    rng = (date.fromisoformat(args[0]), date.fromisoformat(args[1])) if len(args) == 2 else DEFAULT_RANGE
    run(*rng, layer_set=layer_set)
