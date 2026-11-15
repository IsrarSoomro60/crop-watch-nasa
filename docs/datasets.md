# Datasets: status

Updated 2026-11-14.

| Dataset | What for | Access | Status |
| --- | --- | --- | --- |
| **NASA POWER** daily (AG) | Temperature, rain, humidity, wind, sunlight (MJ/m²/day), soil wetness → risk, ETo | No key | **Live** in the API. Cached per ~50 km cell; saved samples for 4 districts |
| **SoilGrids 2.0** (ISRIC) | Topsoil texture, organic carbon, pH, bulk density → paddy percolation, soil context | No key, ≤5 requests/min | **Live** in the API (`/api/soil`, and in every comparison). Saved samples for 4 districts |
| FAO-56 Tables 11–12 | Stage lengths, crop coefficients | Static tables | In crop profiles |
| FAO Irrigation Manual 3 | Effective rainfall, paddy water | Static formulas | In `services/water` |
| **MODIS NDVI** (MOD13Q1.061, 250 m, 16-day) | Observed green-cover pattern, bare periods, crop stress | AppEEARS, Earthdata login | **Live sample**: June 2025-May 2026 for the 4 demo districts in `app/data/sample/satellite_samples.json`, served by `GET /api/satellite`. Only pixel reliability 0-1 marked usable. Not yet used in scoring. |
| **SMAP L4** (SPL4SMGP.008, 9 km, 3-hourly) | Root-zone and surface soil moisture vs POWER's model soil wetness | AppEEARS, Earthdata login | **Live sample**: same task, averaged to daily means, same endpoint. L4 is a model analysis that assimilates satellite data, not a field measurement. |
| **GPM IMERG** daily (V07, 0.1°) | Rain in the scores (water use, drought, waterlogging) | Earthdata Cloud OPeNDAP, Earthdata login | **Live in scoring** for the 4 demo districts, Nov 2024 - Aug 2026 (`app/data/sample/gpm_imerg_daily.json`, `scripts/fetch_gpm.py`). Final run (gauge-calibrated) to 2025-09-30, then Late run (not gauge-calibrated); each day labelled. Replaces POWER rain within 10 km of a district cell (`app/services/gpm.py`); every comparison reports GPM vs POWER totals and flags differences of 30% or more (Hyderabad: GPM about half of POWER). 20-year history still uses POWER. |
| **GRACE / GRACE-FO** mascons (JPL RL06.3Mv04 CRI) | Regional water-storage trend | PO.DAAC, Earthdata login | **Live for all of Pakistan**: monthly 2002-2026 grid (`app/data/grace_pakistan.npz`, 0.5 MB, CRI scale factor applied). `GET /api/satellite` and every comparison report the full-record and 10-year trends (Lahore about -1.0, Multan -0.8 cm/yr). Mascons are ~300 km wide: regional context, not scored. Coastal points use the nearest land cell within 1 deg. |
| **FAOSTAT** (QCL yield, PP producer prices) | Default yield and price for income | Free bulk download | **Live defaults** in `app/domain/economics/faostat_pakistan.json`: wheat, rice, maize (yield = 2022-2024 mean, price = latest annual PKR/t, 2024). Rice price series is erratic and flagged. No FAOSTAT item for mung bean or berseem: farmer enters those. No production costs, so default income is gross. |
| **NASA GIBS map layers** (MODIS NDVI 8-day, GPM IMERG daily rain, SMAP L4 root-zone soil moisture, MODIS monthly land-surface temperature, SRTM elevation) | Visual overlays with a date slider on the My Farm map | No key (WMTS tiles) | **Live** in the frontend (`frontend/src/lib/nasaLayers.ts`). Imagery only: not used in scoring. Layer ids checked against GIBS capabilities 2026-11-15. |
| ECOSTRESS, Landsat/HLS, NASADEM, GEDI | Field-scale ET, imagery, slope, biomass | AppEEARS | Deferred (MODIS land-surface temperature and SRTM are shown as map layers instead) |

## Getting the Earthdata datasets running

1. Create a free account at <https://urs.earthdata.nasa.gov/users/new>.
2. Copy `.env.example` to `backend/.env` and fill in `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`.
   `.env` is git-ignored; never commit it or paste it into chat.
3. From `backend/`: `uv run python -m scripts.fetch_appeears` (default range 2025-06-01 to
   2026-05-31). It prints the task status while AppEEARS processes it, then saves the result files
   under `app/data/sample/appeears/`.

### Rebuilding the satellite sample

```bash
uv run python -m scripts.fetch_appeears --task <AppEEARS task id>   # download a finished task
uv run python -m scripts.build_satellite_samples app/data/sample/appeears/<task name>
uv run python -m scripts.build_grace_pakistan <GRCTellus...RL06.3Mv04.CRI.nc>   # monthly
uv run python -m scripts.build_faostat_defaults <Production_Crops_Livestock_E_Asia.zip> <Prices_E_Asia.zip>   # yearly
```

Raw AppEEARS files are git-ignored; only the compact `satellite_samples.json` is committed.
