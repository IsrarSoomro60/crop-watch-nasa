# Architecture

## Request flow: compare rotations

`POST /api/rotations/compare` with a location, the current rotation, two or more alternatives and
farmer priorities:

1. **NASA data** — `services/nasa/client.py` fetches daily NASA POWER data for the full span of
   all seasons (parameters below). The point is snapped to its weather grid-cell centre
   (0.5° × 0.625°), so all points in a cell share one cache entry (6 h TTL). If NASA is unreachable,
   a saved sample for that cell in `app/data/sample/` is used. `data_processor.py` turns the
   response into `DailyObservation`s (POWER `-999` fill values become `null`) and a `DataNote`
   ("as of" date, grid cell, cache/sample flags) that the API returns with results.
2. **Risk** — `services/risk/risk_engine.py` maps each season day to a growth stage, applies the
   crop profile's stage-specific thresholds per risk (heat, cold, drought, waterlogging, disease),
   and computes `R_crop = 100·Σ(w_d·s_d)/(D·w_max)` via `risk_calculator.py`. Each risk is kept
   separate. Daily rule: inside optimal = Low (0), beyond the optimal edge (`warning`) = Moderate
   (0.5), at or past the `critical` limit = High (1.0). Each risk also gets a Low/Moderate/High
   level (worst day) and up to three tips from `domain/advice.json`.
3. **Rotation** — `services/rotation/rotation_evaluator.py` combines crop results into
   area-weighted rotation risk plus the highest single crop-season risk.
4. **Water** — `services/water/et0.py` computes daily reference evapotranspiration with FAO
   Penman-Monteith (FAO-56 eq. 6; Hargreaves eq. 52 when radiation, humidity or wind is missing),
   using POWER weather and the grid cell's elevation. `crop_water.py` builds the FAO-56 Kc curve
   over the scaled growth stages, sums crop water use (Kc × ETo), subtracts FAO effective rainfall,
   and adds paddy soaking, percolation and water layer for rice. Irrigation need × area gives m³ per
   rotation. Tested against FAO-56 Examples 8 and 18.
5. **Soil and ground cover** — `services/soil/soilgrids.py` fetches SoilGrids 2.0 topsoil
   (0–30 cm clay, sand, silt, organic carbon, pH, bulk density) and the USDA texture class. Town
   centres are masked by SoilGrids, so it steps out ~5 km and reports the point used. Texture sets
   paddy percolation (FAO: 4 mm/day heavy clay, 8 sandy, 6 otherwise). `services/rotation/ground_cover.py`
   counts bare-soil days over a year from the sowing and harvest dates.
6. **History** (`POST /api/history`, `services/history/vulnerability.py`) — replays each season's
   sowing/harvest month-day over the last ~20 years of POWER data with the same risk engine and water
   method: how often each risk reached High, mean High days, a descriptive trend (OLS slope per decade,
   no significance test), and median / 1-in-5 irrigation need. In comparisons, seasons that end after
   the latest weather (future seasons) use that historical median for water and the mean past risk
   score per risk (level = most common worst level, ties to the more severe) for risk and resilience,
   both flagged `estimated_from_history`. This is a typical-year estimate, not a forecast.
7. **Quick check** (`POST /api/quick-check`, `services/quick_check.py`) — the research brief's
   single-crop view: last 7 days of POWER weather, stage from the sowing date (FAO-56 reference
   lengths) or a farmer-picked stage, Low/Moderate/High per risk with the brief's rule (Moderate 3+
   days in a row → High), worst risk as the badge, up to 3 cards with the number against the limit,
   tips, and a 7-day strip.
7b. **Satellite add-ons** (`GET /api/satellite`, `services/satellite.py`) — GRACE/GRACE-FO water
   storage for any location in Pakistan (grid from `scripts/build_grace_pakistan.py`, full-record and
   10-year OLS trends), plus MODIS NDVI and SMAP L4 soil moisture samples for the four demo districts
   (`scripts/build_satellite_samples.py`). Every comparison adds a plain-language GRACE line and how
   much irrigation each alternative saves versus the current rotation. Context only: not scored.
7c. **Income defaults** — `services/income/income.py` uses farmer values first, then FAOSTAT Pakistan
   national averages from `scripts/build_faostat_defaults.py` (wheat, rice, maize). Crops without a
   default (mung bean, berseem) leave income missing, so the overall score is withheld, not guessed.
8. **Recommendation** — `services/recommendation/recommendation_engine.py` builds dimension scores,
   applies farmer priorities with `services/rotation/scoring.py`, ranks rotations and lists
   limitations. `explanations.py` adds, per strategy, why it's considered, benefits versus the
   current rotation, evidence, information gaps and what needs local review.

## Layers

| Path | Role |
| --- | --- |
| `app/api/routes` | HTTP endpoints (`farms`, `environmental_data`, `rotations`) |
| `app/api/dependencies.py` | Dependency providers (swap in fakes for tests) |
| `app/schemas` | Pydantic request/response and domain models |
| `app/services` | Data access to NASA and all calculations |
| `app/domain/crop_profiles` | One JSON per crop: stages, thresholds, evidence status, gaps |
| `app/domain/scoring_config.py` | Provisional severity levels and stage weights |
| `app/repositories` | Crop profile loading; in-memory farm store |
| `app/core/config.py` | Settings from env / `.env` |

## Evidence rules in code

- A `Threshold` has `warning`/`critical` values, `min_duration_days`, `evidence_status` and
  `sources`. Values are `null` until backed by a citation.
- Unsourced thresholds and unknown stage durations are **not** guessed: the risk is scored as
  undetected and an entry is added to `evidence_gaps`, which the API returns.
- Dimensions no rotation has yet (water, income) are `null` and excluded from the preference
  score; the remaining farmer weights are renormalised.
- Missing data never counts as low risk. Resilience compares the risk types assessed for every crop
  in the **current** rotation (returned as `resilience_risks`); an alternative that can't be assessed
  on all of them gets no resilience score instead of shrinking the comparison for every rotation. If a rotation
  lacks a weighted dimension that other rotations have (e.g. resilience, because a crop has no
  limits), its overall score is withheld, `missing_dimensions` says why, and it is listed last.
- Legume share is reported only as a soil-health *indicator*.

- Stage lengths come from FAO-56 Table 11 and are scaled to each season's length
  (`docs/research/fao56-stage-lengths.md`).
- Without stage durations (currently berseem only), a threshold is applied season-wide only if it is identical in every
  stage that sets it (e.g. rice heat 33/35 °C); risks whose limits differ by stage (e.g. wheat heat)
  are left unassessed and listed in `evidence_gaps`.

## NASA POWER parameters

| Code | Field | Unit | Used for |
| --- | --- | --- | --- |
| T2M | `tmean_c` | °C | General suitability |
| T2M_MAX | `tmax_c` | °C | Heat stress |
| T2M_MIN | `tmin_c` | °C | Cold and frost |
| PRECTOTCORR | `precipitation_mm` | mm/day | Drought and excess rain |
| RH2M | `relative_humidity_pct` | % | Humid-weather disease |
| ALLSKY_SFC_SW_DWN | `solar_radiation_mj_m2` | MJ/m²/day (AG community; the brief lists kWh) | Cloudy spells, ETo (lags 5–7 days) |
| WS2M | `wind_speed_ms` | m/s | Lodging, spray timing |
| GWETTOP | `surface_soil_moisture` | 0–1 | Sowing moisture |
| GWETROOT | `soil_moisture` | 0–1 | Water stress |

Offline samples: `uv run python -m scripts.fetch_sample_data [START END]` saves one response per demo
district (Multan, Bahawalpur, Larkana, Hyderabad); default range 2025-06-01 to 2026-05-31.

## Current gaps

- Future seasons get water from the 20-year median but no resilience score yet (risk could use the
  historical share of High seasons).
- Rice and maize heat limits (brief: 35 °C; 40/38 °C) are exceeded on most summer days in Multan
  (rice ~95 of 123 days, every season), so they don't separate good and bad years. Needs agronomist
  review or a sharper rule (flowering window only, minimum run of hot days). Kc is not adjusted for local wind and minimum humidity; paddy
  percolation uses FAO's 6 mm/day average until soil data (phase 4) is added.
- Temperature limits for wheat, rice and maize are provisional (see
  `docs/research/research-brief-thresholds.md`); drought, waterlogging and disease values are not set, and
  no crop has late-season limits. Berseem has no heat limit and no stage lengths, so its
  heat and water use are not calculated.
- Advice table has only three entries and no Urdu text yet.
- Water and income scoring need local water-use, yield, price and cost data.
- Farms are stored in memory only.

## Speed: parallel downloads, disk cache, warm-up

Almost all response time is waiting for NASA POWER (~2-5 s per download) and SoilGrids (~5-15 s per
request, sometimes hanging under load). Three measures keep the demo fast:

- **Parallel downloads** — a comparison fetches weather, soil and (for seasons with no weather yet)
  20 years of history at the same time (`asyncio.gather` in `api/routes/rotations.py` and `history.py`).
- **Disk cache** (`backend/var/cache/`, git-ignored; `DISK_CACHE`, `CACHE_DIR` settings) — every POWER
  download is saved for the cache lifetime (6 h, recent days are revised nightly) and any longer
  download answers a shorter request for the same grid cell. SoilGrids answers, including "no soil
  data here", are kept for good; a SoilGrids failure uses the saved sample and is retried after 15 min.
- **Warm-up** (`services/warm_up.py`, `WARM_UP_DEMO_DISTRICTS`) — at startup, in the background, one
  21-year POWER download per demo district plus their soil, so demo requests are answered from cache.

Measured on 2026-11-14 (same network, back to back): first Multan comparison 41.9 s with the old
code, 23.8 s with parallel downloads, ~0.2 s server time after warm-up (warm-up itself: weather 4 s,
soil ~60 s in the background). SoilGrids speed varied a lot between runs. Redis (shared cache across
servers) and Celery (background jobs for AppEEARS / monthly GRACE / yearly FAOSTAT) are the next step
for a multi-user deployment; they are not needed for one demo server.
