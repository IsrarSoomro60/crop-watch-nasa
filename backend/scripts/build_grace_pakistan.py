"""Cut a Pakistan-sized extract from the JPL GRACE/GRACE-FO mascon file.

Input: GRCTellus.JPL.*.RL06.3Mv04.CRI.nc from PO.DAAC (global, 0.5 deg, ~46 MB, Earthdata login;
dataset TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4). Output: app/data/grace_pakistan.npz (~1-2 MB),
read by app/services/satellite.py for any location in the box.

Run from backend/:
    uv run python -m scripts.build_grace_pakistan GRACE_NC

The values are equivalent water thickness anomalies (cm, vs the 2004.0-2009.999 mean) multiplied by
the file's CRI scale factor, as the file's metadata directs. The uncertainty is the file's own value,
unscaled. Re-run monthly to add new months.
"""

import sys
from pathlib import Path

import h5py
import numpy as np

from app.core.config import APP_DIR

OUT = APP_DIR / "data" / "grace_pakistan.npz"
LAT_RANGE = (23.0, 38.0)  # Pakistan with a small margin
LON_RANGE = (60.0, 78.0)
FILL = -99999.0


def main(nc: Path) -> None:
    with h5py.File(nc, "r") as f:
        lat, lon, t = f["lat"][:], f["lon"][:], f["time"][:]
        i = np.where((lat >= LAT_RANGE[0]) & (lat <= LAT_RANGE[1]))[0]
        j = np.where((lon >= LON_RANGE[0]) & (lon <= LON_RANGE[1]))[0]
        i0, i1, j0, j1 = i[0], i[-1] + 1, j[0], j[-1] + 1
        lwe = f["lwe_thickness"][:, i0:i1, j0:j1]
        unc = f["uncertainty"][:, i0:i1, j0:j1]
        scale = f["scale_factor"][i0:i1, j0:j1]
        land = f["land_mask"][i0:i1, j0:j1]
        title = f.attrs["title"].decode()
    bad = (lwe == FILL) | (scale == FILL)
    lwe = np.where(bad, np.nan, lwe * np.where(scale == FILL, np.nan, scale)[None, :, :])
    unc = np.where(unc == FILL, np.nan, unc)
    np.savez_compressed(
        OUT,
        lat=lat[i0:i1].astype("float32"),
        lon=lon[j0:j1].astype("float32"),
        days_since_2002=t.astype("float32"),
        lwe_cm=lwe.astype("float32"),
        uncertainty_cm=unc.astype("float32"),
        land=land.astype("int8"),
        title=np.array(title),
    )
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), {lwe.shape[0]} months, grid {lwe.shape[1]}x{lwe.shape[2]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
