"""Fetch GPM IMERG daily precipitation for the demo districts from NASA GES DISC (OPeNDAP).

Needs EARTHDATA_USERNAME / EARTHDATA_PASSWORD in backend/.env, and the "NASA GESDISC
DATA ARCHIVE" application approved once in your Earthdata profile
(https://urs.earthdata.nasa.gov/profile -> Applications -> Authorized Apps).

Run from backend/:
    uv run python -m scripts.fetch_gpm [START END]     # dates YYYY-MM-DD

Each day is one request for a small box covering all districts. Output:
app/data/sample/gpm_imerg_daily.json  {district: {"cell": [lat, lon], "dates": [...], "precipitation_mm": [...]}}
Product: GPM_3IMERGDF V07 (final run, 0.1 deg, daily, mm/day), https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07
"""

import json
import re
import sys
from datetime import date, timedelta

from app.core.config import get_settings
from app.services.nasa.earthdata import EarthdataSession
from scripts.fetch_sample_data import DEFAULT_RANGE, DEMO_DISTRICTS

BASE = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07"
FILL = -9999.9


def lat_index(lat: float) -> int:
    return round((lat + 89.95) / 0.1)


def lon_index(lon: float) -> int:
    return round((lon + 179.95) / 0.1)


def day_url(d: date, lon0: int, lon1: int, lat0: int, lat1: int) -> str:
    name = f"3B-DAY.MS.MRG.3IMERG.{d:%Y%m%d}-S000000-E235959.V07B.nc4"
    return f"{BASE}/{d:%Y}/{d:%m}/{name}.ascii?precipitation[0:0][{lon0}:{lon1}][{lat0}:{lat1}]"


def parse_ascii_grid(text: str) -> list[list[float]]:
    """Rows of the OPeNDAP ASCII grid: one row per lon index, values along lat."""
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\s*precipitation(?:\.precipitation)?\[0\]\[\d+\],\s*(.+)$", line)
        if m:
            rows.append([float(v) for v in m.group(1).split(",")])
    return rows


def run(start: date, end: date) -> None:
    settings = get_settings()
    cells = {name: (lat_index(lat), lon_index(lon)) for name, (lat, lon) in DEMO_DISTRICTS.items()}
    lat0, lat1 = min(c[0] for c in cells.values()), max(c[0] for c in cells.values())
    lon0, lon1 = min(c[1] for c in cells.values()), max(c[1] for c in cells.values())
    out = {name: {"cell": [round(-89.95 + i * 0.1, 2), round(-179.95 + j * 0.1, 2)], "dates": [],
                  "precipitation_mm": []} for name, (i, j) in cells.items()}

    with EarthdataSession(settings) as s:
        d = start
        while d <= end:
            r = s.get(day_url(d, lon0, lon1, lat0, lat1))
            if r.status_code == 401:
                sys.exit("Earthdata refused access: approve 'NASA GESDISC DATA ARCHIVE' in your Earthdata profile.")
            r.raise_for_status()
            grid = parse_ascii_grid(r.text)
            for name, (i, j) in cells.items():
                value = grid[j - lon0][i - lat0]
                out[name]["dates"].append(d.isoformat())
                out[name]["precipitation_mm"].append(None if value <= FILL + 1 else round(value, 2))
            if d.day == 1:
                print(f"  {d:%Y-%m} ...", flush=True)
            d += timedelta(days=1)

    path = settings.sample_data_dir / "gpm_imerg_daily.json"
    path.write_text(json.dumps({"product": "GPM_3IMERGDF.07", "units": "mm/day", "districts": out}), encoding="utf-8")
    print(f"saved {path.name}")


if __name__ == "__main__":
    args = sys.argv[1:]
    rng = (date.fromisoformat(args[0]), date.fromisoformat(args[1])) if len(args) == 2 else DEFAULT_RANGE
    run(*rng)
