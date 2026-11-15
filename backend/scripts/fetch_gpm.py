"""Fetch GPM IMERG daily precipitation for the demo districts from NASA Earthdata Cloud OPeNDAP.

Needs EARTHDATA_USERNAME / EARTHDATA_PASSWORD in backend/.env, and the "NASA GESDISC
DATA ARCHIVE" application approved once in your Earthdata profile
(https://urs.earthdata.nasa.gov/profile -> Applications -> Authorized Apps).

Run from backend/:
    uv run python -m scripts.fetch_gpm [START END]                  # Final run (default)
    uv run python -m scripts.fetch_gpm --product late START END     # fill days the Final run lacks

Products (0.1 deg, daily, mm/day):
* final: GPM_3IMERGDF V07, gauge-calibrated; currently ends months to a year behind real time.
* late:  GPM_3IMERGDL V07, near real time (~1 day), NOT gauge-calibrated, so less accurate, mainly for
  heavy rain. Used only to fill days with no Final value; every day records which product it came from.

Granule names (V07B, V07C, ...) are looked up in NASA's CMR catalogue instead of guessed. Each day is one
request for a small box covering all districts. The output file is merged, not replaced:
app/data/sample/gpm_imerg_daily.json
  {"products": {...}, "districts": {name: {"cell", "dates", "precipitation_mm", "sources"}}}
"""

import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import get_settings
from app.services.nasa.earthdata import EarthdataSession
from scripts.fetch_sample_data import DEFAULT_RANGE, DEMO_DISTRICTS

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
OPENDAP = "https://opendap.earthdata.nasa.gov/collections"
# CMR collection ids, version 07 (looked up 2026-11-15).
PRODUCTS = {
    "final": {"collection": "C2723754864-GES_DISC", "name": "GPM_3IMERGDF.07",
              "description": "IMERG Final Run daily, gauge-calibrated"},
    "late": {"collection": "C2723754859-GES_DISC", "name": "GPM_3IMERGDL.07",
             "description": "IMERG Late Run daily, near real time, not gauge-calibrated (less accurate)"},
}
FILL = -9999.9


def lat_index(lat: float) -> int:
    return round((lat + 89.95) / 0.1)


def lon_index(lon: float) -> int:
    return round((lon + 179.95) / 0.1)


def granule_titles(product: str, start: date, end: date, http: httpx.Client | None = None) -> dict[str, str]:
    """{YYYY-MM-DD: granule title} for every day the product has in the range, from NASA CMR."""
    http = http or httpx.Client(timeout=120)
    out: dict[str, str] = {}
    page = 1
    while True:
        resp = http.get(CMR, params={
            "collection_concept_id": PRODUCTS[product]["collection"],
            "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
            "page_size": 2000, "page_num": page,
        })
        resp.raise_for_status()
        entries = resp.json()["feed"]["entry"]
        for e in entries:
            m = re.search(r"3IMERG\.(\d{8})-", e["title"])
            if m:
                d = m.group(1)
                out[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = e["title"]
        if len(entries) < 2000:
            return out
        page += 1


def day_url(product: str, granule_title: str, lon0: int, lon1: int, lat0: int, lat1: int) -> str:
    collection = PRODUCTS[product]["collection"]
    ce = quote(f"/precipitation[0:0][{lon0}:{lon1}][{lat0}:{lat1}]", safe="")
    return f"{OPENDAP}/{collection}/granules/{quote(granule_title, safe='')}.dap.csv?dap4.ce={ce}"


def parse_ascii_grid(text: str) -> list[list[float]]:
    """Rows of the OPeNDAP grid: one row per lon index, values along lat."""
    rows = []
    for line in text.splitlines():
        # Cloud DAP4 CSV: "/precipitation[0][12], v, v"; older DAP2 ASCII: "precipitation[0][12], v" or
        # named indices such as "precipitation.precipitation[precipitation.time=16627][precipitation.lon=71.45], v".
        m = re.match(r"^\s*/?precipitation(?:\.precipitation)?\[[^\]]+\]\[[^\]]+\],\s*(.+)$", line)
        if m:
            rows.append([float(v) for v in m.group(1).split(",")])
    return rows


def get_with_retry(session: EarthdataSession, url: str, tries: int = 4) -> httpx.Response | None:
    """NASA servers time out now and then; wait and retry. None if every try failed."""
    for attempt in range(1, tries + 1):
        try:
            return session.get(url)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            if attempt < tries:
                time.sleep(10 * attempt)
    return None


def load_existing(path: Path) -> dict[str, dict[str, tuple[float | None, str | None]]]:
    """{district: {date: (mm, source)}} from an earlier run; files from before 'sources' existed are Final."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for name, v in data["districts"].items():
        sources = v.get("sources") or ["final" if x is not None else None for x in v["precipitation_mm"]]
        out[name] = {d: (x, s) for d, x, s in zip(v["dates"], v["precipitation_mm"], sources, strict=True)}
    return out


def merge(existing: dict, new: dict) -> dict:
    """Keep existing values; add new ones only where the existing day has no value."""
    merged = {k: dict(v) for k, v in existing.items()}
    for name, days in new.items():
        target = merged.setdefault(name, {})
        for d, (mm, src) in days.items():
            if target.get(d, (None, None))[0] is None:
                target[d] = (mm, src)
    return merged


def run(start: date, end: date, product: str = "final") -> None:
    settings = get_settings()
    path = settings.sample_data_dir / "gpm_imerg_daily.json"
    existing = load_existing(path)
    cells = {name: (lat_index(lat), lon_index(lon)) for name, (lat, lon) in DEMO_DISTRICTS.items()}
    lat0, lat1 = min(c[0] for c in cells.values()), max(c[0] for c in cells.values())
    lon0, lon1 = min(c[1] for c in cells.values()), max(c[1] for c in cells.values())

    titles = granule_titles(product, start, end)
    print(f"{PRODUCTS[product]['name']}: {len(titles)} daily files in range", flush=True)
    new: dict[str, dict[str, tuple[float | None, str | None]]] = {name: {} for name in cells}
    failed: list[str] = []
    skipped = 0
    with EarthdataSession(settings) as s:
        d = start
        while d <= end:
            key = d.isoformat()
            have = all(existing.get(n, {}).get(key, (None, None))[0] is not None for n in cells)
            title = titles.get(key)
            if have or title is None:
                skipped += have
                for name in cells:
                    new[name][key] = (None, None)  # merge keeps any existing value
                d += timedelta(days=1)
                continue
            r = get_with_retry(s, day_url(product, title, lon0, lon1, lat0, lat1))
            if r is not None and r.status_code == 401:
                sys.exit("Earthdata refused access: approve 'NASA GESDISC DATA ARCHIVE' in your Earthdata profile.")
            grid = None
            if r is None:
                failed.append(key)
            elif r.status_code != 404:
                r.raise_for_status()
                grid = parse_ascii_grid(r.text)
            for name, (i, j) in cells.items():
                value = grid[j - lon0][i - lat0] if grid else None
                ok = value is not None and value > FILL + 1
                new[name][key] = (round(value, 2), product) if ok else (None, None)
            if d.day == 1:
                print(f"  {d:%Y-%m} ...", flush=True)
            d += timedelta(days=1)

    merged = merge(existing, new)
    districts = {}
    for name, (i, j) in cells.items():
        days = sorted(merged[name].items())
        districts[name] = {
            "cell": [round(-89.95 + i * 0.1, 2), round(-179.95 + j * 0.1, 2)],
            "dates": [d for d, _ in days],
            "precipitation_mm": [v[0] for _, v in days],
            "sources": [v[1] for _, v in days],
        }
    payload = {"products": {k: f"{v['name']}: {v['description']}" for k, v in PRODUCTS.items()},
               "units": "mm/day", "districts": districts}
    path.write_text(json.dumps(payload), encoding="utf-8")
    msg = f"saved {path.name} ({skipped} days already had values)"
    print(msg + (f"; {len(failed)} days failed after retries: {failed[:5]}" if failed else ""))


if __name__ == "__main__":
    args = sys.argv[1:]
    product = "final"
    if len(args) >= 2 and args[0] == "--product":
        product, args = args[1], args[2:]
        if product not in PRODUCTS:
            sys.exit(f"Unknown product {product!r}; use final or late.")
    rng = (date.fromisoformat(args[0]), date.fromisoformat(args[1])) if len(args) == 2 else DEFAULT_RANGE
    run(*rng, product=product)
