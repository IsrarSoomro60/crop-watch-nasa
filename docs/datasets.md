# Datasets: status

Updated 2026-11-14.

| Dataset | What for | Access | Status |
| --- | --- | --- | --- |
| **NASA POWER** daily (AG) | Temperature, rain, humidity, wind, sunlight (MJ/m²/day), soil wetness → risk, ETo | No key | **Live** in the API. Cached per ~50 km cell; saved samples for 4 districts |
| **SoilGrids 2.0** (ISRIC) | Topsoil texture, organic carbon, pH, bulk density → paddy percolation, soil context | No key, ≤5 requests/min | **Live** in the API (`/api/soil`, and in every comparison). Saved samples for 4 districts |
| FAO-56 Tables 11–12 | Stage lengths, crop coefficients | Static tables | In crop profiles |
| FAO Irrigation Manual 3 | Effective rainfall, paddy water | Static formulas | In `services/water` |
| **MODIS NDVI** (MOD13Q1.061, 250 m, 16-day) | Observed green-cover pattern, bare periods, crop stress | AppEEARS, Earthdata login | **Fetch script ready** (`scripts/fetch_appeears.py`), not run yet. App reader to be written from the first real files. ORNL's no-login MODIS service was unreachable from our network. |
| **SMAP L4** (SPL4SMGP.008, 9 km, daily) | Satellite root-zone soil moisture vs POWER's model soil wetness | AppEEARS, Earthdata login | Same script as MODIS; not run yet |
| **GPM IMERG** daily | Higher-resolution rainfall, extremes | GES DISC, Earthdata login | Not started (not in AppEEARS) |
| **GRACE / GRACE-FO** mascons | Groundwater storage trend per district | PO.DAAC, Earthdata login | Not started (not in AppEEARS) |
| FAOSTAT / AMIS Punjab | Yields, prices for income | Free | Not started (phase 5) |
| ECOSTRESS, Landsat/HLS, NASADEM, GEDI | Field-scale ET, imagery, slope, biomass | AppEEARS | Deferred |

## Getting the Earthdata datasets running

1. Create a free account at <https://urs.earthdata.nasa.gov/users/new>.
2. Copy `.env.example` to `backend/.env` and fill in `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`.
   `.env` is git-ignored; never commit it or paste it into chat.
3. From `backend/`: `uv run python -m scripts.fetch_appeears` (default range 2025-06-01 to
   2026-05-31). It prints the task status while AppEEARS processes it, then saves the result files
   under `app/data/sample/appeears/`.
