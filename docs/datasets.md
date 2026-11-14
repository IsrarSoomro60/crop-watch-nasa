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
| **GPM IMERG** daily | Higher-resolution rainfall, extremes | GES DISC, Earthdata login | Fetch script ready (`scripts/fetch_gpm.py`); GES DISC was unreachable, so not run yet. |
| **GRACE / GRACE-FO** mascons (JPL RL06.3Mv04 CRI) | Regional water-storage trend | PO.DAAC, Earthdata login | **Live sample**: monthly 2002-2026 for the 0.5 deg cell of each demo district (CRI scale factor applied), OLS trend in `GET /api/satellite` (Multan about -0.8 cm/yr). Mascons are ~300 km wide: regional, not per farm. |
| FAOSTAT / AMIS Punjab | Yields, prices for income | Free | Not started (phase 5) |
| ECOSTRESS, Landsat/HLS, NASADEM, GEDI | Field-scale ET, imagery, slope, biomass | AppEEARS | Deferred |

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
uv run python -m scripts.build_satellite_samples <grace_mascon.nc> app/data/sample/appeears/<task name>
```

Raw AppEEARS files are git-ignored; only the compact `satellite_samples.json` is committed.
