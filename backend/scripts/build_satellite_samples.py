"""Build app/data/sample/satellite_samples.json for the demo districts.

Inputs (downloaded once, not committed when large):
  * AppEEARS point results (scripts/fetch_appeears.py) for MODIS MOD13Q1 NDVI and SMAP L4 SPL4SMGP
    soil moisture, in app/data/sample/appeears/<task>/.
  * JPL GRACE/GRACE-FO mascon RL06.3Mv04 CRI netCDF (PO.DAAC, ~46 MB, Earthdata login).

Run from backend/:
    uv run python -m scripts.build_satellite_samples GRACE_NC APPEEARS_DIR

What it keeps:
  * NDVI: one value per 16-day composite with its pixel reliability (0 good, 1 marginal,
    2 snow/ice, 3 cloudy). The API reports only reliability 0-1 values as usable.
  * SMAP: 3-hourly model values averaged to daily means (m3/m3). SMAP L4 is a model
    analysis that assimilates satellite brightness temperature, not a direct measurement.
  * GRACE: monthly equivalent water thickness anomaly (cm, vs the 2004.0-2009.999 mean) for
    the 0.5 deg cell holding the district, multiplied by the file's CRI scale factor as its
    metadata directs. Mascons are ~3 deg wide, so this is a regional signal, not a farm one.
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np

from app.core.config import APP_DIR
from scripts.fetch_sample_data import DEMO_DISTRICTS

OUT = APP_DIR / "data" / "sample" / "satellite_samples.json"
FILL = -99999.0


def read_ndvi(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            ndvi = float(row["MOD13Q1_061__250m_16_days_NDVI"])
            rel = int(float(row["MOD13Q1_061__250m_16_days_pixel_reliability"]))
            out[row["ID"]].append({
                "date": row["Date"][:10],
                "ndvi": None if ndvi < -0.2 else round(ndvi, 4),  # fill is -0.3 after AppEEARS scaling
                "reliability": rel,
            })
    return out


def read_smap(path: Path) -> dict[str, list[dict]]:
    acc: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            rz = float(row["SPL4SMGP_008_Geophysical_Data_sm_rootzone"])
            sf = float(row["SPL4SMGP_008_Geophysical_Data_sm_surface"])
            if rz < 0 or sf < 0:
                continue
            acc[(row["ID"], row["Date"][:10])].append((rz, sf))
    out: dict[str, list[dict]] = defaultdict(list)
    for (district, day), vals in sorted(acc.items()):
        out[district].append({
            "date": day,
            "rootzone_m3m3": round(sum(v[0] for v in vals) / len(vals), 4),
            "surface_m3m3": round(sum(v[1] for v in vals) / len(vals), 4),
        })
    return out


def read_grace(path: Path) -> dict[str, dict]:
    out = {}
    with h5py.File(path, "r") as f:
        lat, lon, t = f["lat"][:], f["lon"][:], f["time"][:]
        base = date(2002, 1, 1)
        for name, (la, lo) in DEMO_DISTRICTS.items():
            i = int(np.abs(lat - la).argmin())
            j = int(np.abs(lon - (lo % 360)).argmin())
            lwe = f["lwe_thickness"][:, i, j]
            unc = f["uncertainty"][:, i, j]
            scale = float(f["scale_factor"][i, j])
            series = [
                {
                    "date": (base + timedelta(days=float(d))).isoformat(),
                    "lwe_cm": round(float(v) * scale, 2),
                    "uncertainty_cm": round(float(u), 2),
                }
                for d, v, u in zip(t, lwe, unc, strict=True)
                if v != FILL
            ]
            out[name.lower()] = {
                "cell_lat": float(lat[i]),
                "cell_lon": float(lon[j]) if lon[j] <= 180 else float(lon[j]) - 360,
                "scale_factor": round(scale, 4),
                "series": series,
            }
    return out


def main(grace_nc: Path, appeears_dir: Path) -> None:
    ndvi = read_ndvi(next(appeears_dir.glob("*MOD13Q1*-results.csv")))
    smap = read_smap(next(appeears_dir.glob("*SPL4SMGP*-results.csv")))
    grace = read_grace(grace_nc)
    districts = {}
    for name, (la, lo) in DEMO_DISTRICTS.items():
        key = name.lower()
        districts[key] = {
            "name": name, "latitude": la, "longitude": lo,
            "ndvi": ndvi.get(key, []), "soil_moisture": smap.get(key, []), "grace": grace.get(key),
        }
    OUT.write_text(json.dumps({
        "sources": {
            "ndvi": "MODIS/Terra MOD13Q1 v061, 250 m 16-day NDVI, via NASA AppEEARS",
            "soil_moisture": "SMAP L4 SPL4SMGP v008, 9 km 3-hourly model analysis, daily mean, via NASA AppEEARS",
            "grace": "JPL GRACE/GRACE-FO mascon RL06.3Mv04 CRI (PO.DAAC), anomaly vs 2004.0-2009.999",
        },
        "districts": districts,
    }, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
