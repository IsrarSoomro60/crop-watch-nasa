# Presentation data sheet

Numbers for the Space Apps 2026 slides, gathered 2026-11-14. Every figure says where it came from.
**Model outputs are estimates from our prototype, not field measurements.** Re-run before the final
deck if inputs change (commands at the bottom).

Labels used below:
- **[MODEL]** produced by Crop-Watch AI from live NASA/ISRIC data on 2026-11-14
- **[DATA]** read directly from a dataset we hold
- **[CONTEXT]** published statistic from an outside source
- **[ASSUMPTION]** a choice we made; say so on the slide or in the speaker notes
- **[GAP]** missing, unverified or weak; don't present as fact

---

## 1. Pakistan context (problem slide)

| Figure | Value | Source |
|---|---|---|
| Agriculture share of GDP | ~23% (22.9%) | [CONTEXT] FAO in Pakistan, "Pakistan at a Glance" (fao.org/pakistan), FY2023 basis |
| Labour force in agriculture | 37.4% of 71.76 million | [CONTEXT] same FAO page |
| Exports derived from agriculture | ~70% (directly or indirectly) | [CONTEXT] same FAO page |
| Cultivated land that is irrigated | >82% (18% rainfed) | [CONTEXT] same FAO page |
| Total cropped area | 24.1 million ha | [CONTEXT] same FAO page |
| Wheat / rice share of crop area | 37% / 11% | [CONTEXT] same FAO page |
| Rice exports | 4th largest rice exporter in the world | [CONTEXT] same FAO page |
| Total water availability | 72.7 MAF (million acre-feet) | [CONTEXT] same FAO page |
| Farmers / average farm size | >10 million farmers, ~2 ha average (2025 estimate) | [GAP] Wikipedia "Agriculture in Pakistan", ref. not checked; verify before use |
| Water per person | ~1,101 m³ (2004–05), "high stress" | [GAP] Wikipedia citing Planning & Development Division, **20 years old**; find a current figure (e.g. Pakistan Economic Survey, IMF/World Bank) |

**Still to source ([GAP]):** groundwater's share of irrigation water; number of tubewells; area under
the rice–wheat system; yield losses from heat waves; production cost per ha (Punjab/Sindh agriculture
departments); market size for the business slide. Web search was unavailable while compiling this sheet.

---

## 2. What the prototype contains

| Item | Value | Source |
|---|---|---|
| Crops | 5: wheat, rice, maize, mung bean, berseem (2 legumes: mung bean, berseem) | [DATA] `backend/app/domain/crop_profiles/` |
| Risk types | 5 defined; **3 scored** (heat, cold, drought); waterlogging and disease have no sourced thresholds, so they are not assessed | [DATA] crop profiles, `docs/architecture.md` |
| NASA POWER variables | 9 daily: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN, WS2M, GWETTOP, GWETROOT | [DATA] `docs/architecture.md` |
| POWER grid | ~50 km cell (0.5° × 0.625°), 2–3 day lag | [DATA] API data note |
| Historical replay | 20 seasons per crop (sowing years 2006–2026) | [MODEL] `/api/history` |
| GRACE/GRACE-FO record | Apr 2002 – Sep 2026, monthly, ~300 km mascons, all of Pakistan | [DATA] `app/data/grace_pakistan.npz` |
| MODIS NDVI sample | 24 composites per district (16-day, 250 m), Jun 2025–May 2026 | [DATA] `satellite_samples.json` |
| SMAP L4 sample | 365 daily means per district (9 km), Jun 2025–May 2026 | [DATA] same file |
| SoilGrids | 250 m, 6 topsoil properties, 0–30 cm | [DATA] `/api/soil` |
| Demo districts | Multan (30.20, 71.47), Bahawalpur (29.40, 71.68), Larkana (27.56, 68.21), Hyderabad (25.40, 68.37) | [DATA] `scripts/fetch_sample_data.py` |
| Automated tests | 72 passing | [DATA] `uv run pytest`, 2026-11-14 |
| Languages | English + Urdu tips (**Urdu not yet reviewed**: `ur_reviewed: false`) | [DATA] `app/domain/advice.json` |

---

## 3. Headline result: rotation comparison, 4 districts [MODEL]

**Inputs ([ASSUMPTION]):** 1 ha per season. Sowing/harvest dates: rice 15 Jun–20 Oct 2025 (128 days);
maize 15 Jun–30 Sep (108 days); mung bean 15 Jun–10 Sep (88 days); wheat 15 Nov 2025–20 Apr 2026
(157 days). Equal priorities (0.25 each for soil, water, income, resilience). Live NASA POWER and SoilGrids.

### Irrigation need (m³ per ha per year)

| District | Rice–Wheat (current) | Maize–Wheat | Mung–Wheat |
|---|---|---|---|
| Multan | 24,162 | 10,277 (**−57%**) | 8,685 (**−64%**) |
| Bahawalpur | 24,607 | 10,589 (**−57%**) | 9,008 (**−63%**) |
| Larkana | 26,630 | 12,106 (**−55%**) | 10,453 (**−61%**) |
| Hyderabad | 21,051 | 7,180 (**−66%**) | 5,795 (**−72%**) |

**Slide line:** *"Across all four districts, replacing rice with maize cuts estimated irrigation need
by 55–66%; replacing it with mung bean cuts it by 61–72%."*

Scale example: on a 10 ha Multan farm, Maize–Wheat saves about **138,850 m³** a year (13,885 × 10).

### Overall ranking (equal priorities)

| District | #1 | #2 | Not scored |
|---|---|---|---|
| Multan | Maize–Wheat 0.59 | Rice–Wheat 0.54 | Mung–Wheat (no income data) |
| Bahawalpur | Maize–Wheat 0.60 | Rice–Wheat 0.54 | Mung–Wheat |
| Larkana | Maize–Wheat 0.58 | Rice–Wheat 0.54 | Mung–Wheat |
| Hyderabad | Maize–Wheat 0.62 | Rice–Wheat 0.53 | Mung–Wheat |

### Dimension scores, Multan (0–1, higher is better)

| | Soil-health indicator | Water | Income | Resilience | Highest crop-season risk (0–100) | Bare-soil days/yr |
|---|---|---|---|---|---|---|
| Rice–Wheat | 0.39 | 0.36 | 1.00 | 0.41 | 59.5 | 80 |
| Maize–Wheat | 0.36 | 0.85 | 0.64 | 0.51 | 49.4 | 100 |
| Mung–Wheat | **0.59** | **1.00** | — | **0.72** | **43.8** | 120 |

Resilience in the other districts: Mung–Wheat 0.72 / 0.68 / 0.67, Maize–Wheat 0.53 / 0.47 / 0.67,
Rice–Wheat 0.41 / 0.39 / 0.44 (Bahawalpur / Larkana / Hyderabad).

### Income (gross revenue per ha per year, PKR, FAOSTAT national defaults)

| Rotation | Gross | vs current |
|---|---|---|
| Rice–Wheat | 1,367,472 | — |
| Maize–Wheat | 874,132 | −493,340 (**−36%**) |
| Mung–Wheat | not available | no FAOSTAT price for mung bean |

Per crop: wheat 3.10 t/ha × 89,217 PKR/t = 276,573; rice 3.83 × 284,830 = 1,090,899;
maize 6.15 × 97,164 = 597,559. Same in every district because the defaults are national.

**Price sensitivity:** at the **2022** FAOSTAT rice price (150,596 PKR/t), Rice–Wheat would gross
853,356 PKR/ha, **less than Maize–Wheat (874,132)**. The income ranking depends on which year's rice
price you use. This is why the tool asks farmers for their local price, and it's a good slide point.

**Slide line:** *"57% less water for about 36% less gross revenue at 2024 national prices. The tool
puts a number on the tradeoff so the farmer can decide."*

---

## 4. Is it a one-off year? 20-season NASA POWER replay [MODEL]

Median irrigation need per season in mm (1 mm on 1 ha = 10 m³), sowing years 2006–2026:

| District | Rice | Maize | Mung bean | Wheat |
|---|---|---|---|---|
| Multan | 2,077 | 649 | 503 | 465 |
| Bahawalpur | 2,107 | 664 | 513 | 489 |
| Larkana | 2,196 | 715 | 550 | 559 |
| Hyderabad | 1,990 | 551 | 403 | 658 |

1-in-5-year (80th percentile) rice need: 2,143 / 2,161 / 2,310 / 2,131 mm.

Rotation totals (sum of per-season medians): Multan Rice–Wheat 2,542 mm vs Maize–Wheat 1,114 mm
(**−56%**) vs Mung–Wheat 968 mm (**−62%**). Other districts: −54% to −56% (maize), −60% to −61% (mung).
**The water saving holds across 20 years, not just 2025–26.**

Share of the 20 seasons with at least one High-risk day (Multan):
- Heat: rice 100% (mean 98 High days), maize 100% (71 days), mung bean 95% (21 days), wheat 90% (9 days)
- Rainfed drought stress: maize 90%, mung bean 95%, wheat 100%
- Cold: wheat 15% (3 of 20 seasons), all others 0%

Trend (High days per decade, descriptive OLS, **no significance test**): wheat heat +2.1 (Multan),
+2.2 (Bahawalpur), +3.6 (Larkana), +4.8 (Hyderabad). Wheat is the only crop whose heat days rise in
every district. Present it as "a pattern worth watching", not a proven trend.

---

## 5. Water and weather detail, 2025–26 season [MODEL]

FAO-56 Penman-Monteith reference ET (ETo) and crop water use, Multan:

| Crop | ETo (mm) | Crop water use (mm) | Rain (mm) | Effective rain (mm) | Paddy extra (mm) | Irrigation need (mm) |
|---|---|---|---|---|---|---|
| Rice | 881 | 987 | 238 | 100 | 1,068 | 1,955 |
| Maize | 796 | 653 | 204 | 86 | 0 | 566 |
| Mung bean | 667 | 505 | 203 | 97 | 0 | 407 |
| Wheat | 562 | 477 | 67 | 16 | 0 | 461 |

**Slide line:** *"Over half of rice's irrigation need isn't evaporation at all. It's paddy soaking,
percolation and the standing water layer (1,068 mm)."*

High-risk days in 2025–26 (out of season length):

| District | Rice heat (/128) | Maize heat (/108) | Wheat heat (/157) | Wheat rainfed drought (/157) |
|---|---|---|---|---|
| Multan | 97 | 64 | 20 | 63 |
| Bahawalpur | 96 | 58 | 26 | 67 |
| Larkana | 100 | 74 | 33 | 66 |
| Hyderabad | 88 | 13 | 33 | 45 |

---

## 6. NASA satellite context layers [DATA] (shown, **not scored**)

### GRACE/GRACE-FO regional water storage (JPL mascon RL06.3Mv04 CRI)

| District | Trend 2002–2026 | Trend last 10 yrs | Sep 2026 vs 2004–09 average |
|---|---|---|---|
| Multan | −0.78 cm/yr | −0.12 cm/yr | −14.2 cm (±7.3) |
| Bahawalpur | −0.78 cm/yr | −0.12 cm/yr | −14.3 cm (±7.3) |
| Larkana | +0.01 cm/yr | +0.24 cm/yr | −0.4 cm (±6.5) |
| Hyderabad | −0.29 cm/yr | +0.43 cm/yr | −4.3 cm (±11.1) |

- Multan and Bahawalpur fall in the same ~300 km mascon, so they share one value.
- **Be honest:** storage declined in the southern Punjab region over 24 years, but the decline has
  **slowed** in the last decade, and the Sindh points show no clear loss. Don't say "accelerating
  depletion". GRACE is total water storage (groundwater + soil + surface water), not the water table.
- **Slide line:** *"From orbit, NASA's GRACE satellites measured southern Punjab's water store
  14 cm below its 2004–09 level."*

### SMAP L4 soil moisture (m³/m³, daily means, Jun 2025–May 2026)

| District | Root-zone mean | Root-zone range | Wettest day | Surface mean |
|---|---|---|---|---|
| Multan | 0.154 | 0.131–0.219 | 9 Sep 2025 | 0.091 |
| Bahawalpur | 0.112 | 0.092–0.141 | 8 Sep 2025 | 0.071 |
| Larkana | 0.148 | 0.128–0.188 | 10 Sep 2025 | 0.091 |
| Hyderabad | 0.156 | 0.131–0.233 | 9 Sep 2025 | 0.094 |

All four peak in the same week (8–10 Sep 2025), after the monsoon. SMAP L4 is a 9 km model analysis
that assimilates satellite data. **[GAP]** Irrigation is not fully represented in it, so it reads drier
than irrigated fields.

### MODIS NDVI (250 m, usable composites only)

| District | Usable / total | NDVI range | Peak |
|---|---|---|---|
| Multan | 19 / 24 | 0.09–0.23 | late Aug 2025 |
| Bahawalpur | 18 / 24 | 0.16–0.44 | Aug 2025 (0.44), second peak Nov–Jan (0.37–0.39) |
| Larkana | 19 / 24 | 0.12–0.23 | Feb 2026 |
| Hyderabad | 22 / 24 | 0.08–0.18 | Sep 2025 |

**[GAP] Major:** the sample points are district centre coordinates. Values below ~0.25 all year mean
three of the four pixels are probably **built-up or mixed land, not cropland**. Only Bahawalpur shows
a two-season (kharif + rabi) crop pattern. **Don't show NDVI as crop health.** If you want an NDVI
visual, show Bahawalpur's two peaks as "kharif and rabi visible from space", or re-fetch cropland
pixels before the deck.

### SoilGrids 2.0 topsoil (0–30 cm, 250 m, ~5.6 km from the town centre)

| District | Texture | Clay / sand / silt % | Organic C (g/kg) | pH |
|---|---|---|---|---|
| Multan | Loam | 24 / 42 / 34 | 5.9 | 7.6 |
| Bahawalpur | Sandy clay loam | 26 / 47 / 27 | 6.1 | 7.8 |
| Larkana | Loam | 20 / 50 / 31 | 6.8 | 8.2 |
| Hyderabad | Silty clay loam | 37 / 13 / 50 | 4.5 | 8.4 |

Modelled predictions, not a soil test. All four are alkaline (pH 7.6–8.4) and low in organic carbon
(4.5–6.8 g/kg).

---

## 7. Thresholds and scoring choices (trust / method slide)

### Temperature limits [ASSUMPTION], all marked `provisional` except berseem cold

| Crop | Stage | Heat warning / critical (Tmax °C) | Cold critical |
|---|---|---|---|
| Wheat | establishment, vegetative | 25 / 30 | Tmin 0 °C |
| Wheat | mid-season (flowering, grain fill) | 25 / 32 | Tmin 2 °C |
| Rice | all scored stages | 33 / 35 | Tmin 15 °C |
| Maize | establishment, vegetative | 35 / 40 | Tmin 10 °C |
| Maize | mid-season | 35 / 38 | Tmin 10 °C |
| Mung bean | mid-season | 35 / 40 | Tmean 15 °C (all stages) |
| Berseem | all | none | Tmin −6 °C (**sourced**) |

Source: team research brief, Appendix B (FAO, Jagadish 2007; maize partly from a third-party site).
No limits in the late season (maturity) for any crop.

### Scoring [ASSUMPTION], provisional engineering choices

- Daily severity: none 0, warning 0.5, critical 1.0
- Stage weights: establishment 1.25, vegetative 1.0, flowering 2.0, grain filling 1.75, FAO mid-season 2.0, maturity 1.0
- Crop risk: `R = 100 · Σ(w_d · s_d) / (D · w_max)`, computed separately per risk
- Rotation risk: area-weighted average plus the highest single crop-season risk
- Overall score: farmer weights × dimension scores. Weights are renormalised when a dimension is missing everywhere; if only some rotations lack it, their score is withheld.
- Water score: relative (the lowest irrigation need = 1.0)
- Soil-health indicator: average of legume share and ground-cover fraction
- Resilience: from the risks assessed for every crop in the current rotation (here heat and cold)

---

## 8. Assumptions behind the numbers (speaker notes / backup)

1. Sowing and harvest dates were chosen by us, not taken from local crop calendars.
2. Growth stages: FAO-56 Table 11 lengths scaled to each season. Wheat uses "small grains, Pakistan arid region" (165 days); maize uses a 125-day row from another region. No Pakistan-specific maize or rice rows were used.
3. Crop coefficients (Kc) are not adjusted for local wind or minimum humidity.
4. Rice paddy extra: soaking, standing water layer and percolation. Percolation is FAO's 6 mm/day for every district, since none of the four textures is heavy clay or sandy.
5. Effective rainfall: FAO Irrigation Manual 3 formula.
6. **"Drought" = rainfed root-zone stress** (FAO-56 ch. 8 water balance) with **loam soil assumed everywhere**, even where SoilGrids says otherwise. Because fields are irrigated, this means "how much the crop depends on irrigation", not an actual drought.
7. Irrigation need excludes conveyance and field losses, and capillary rise from groundwater, so real pumping is higher.
8. Income is gross (yield × price). No production costs. National FAOSTAT averages: yield 2022–24 mean, price 2024, nominal PKR. FAOSTAT "rice" is paddy of all varieties (basmati and coarse differ a lot).
9. Weather is for a ~50 km grid cell, not a field.
10. 1 ha per season. Equal priority weights.

---

## 9. Known gaps (be ready to say these)

| Gap | Impact | Fix |
|---|---|---|
| Rice heat threshold (33/35 °C) is crossed on 88–100 days of a 128-day season, and in every year of 20 | Rice heat risk is always High, so it doesn't separate good and bad years | Agronomist review; apply at flowering only or require a run of hot days |
| Waterlogging and disease not assessed | 2 of 5 risks missing; Sindh waterlogging is real | Source thresholds (IRRI, CIMMYT, PARC) |
| MODIS, SMAP, GRACE not scored | The NASA satellite layers are context only | Validate, then add SMAP to the water balance and NDVI to bare-soil days |
| NDVI points are not cropland | NDVI sample can't show crop condition at 3 of 4 districts | Re-fetch at cropland pixels |
| No mung bean / berseem prices | Mung–Wheat can't get an overall score | Farmer input; local market data |
| No production costs | Income is gross, so the gap is overstated or understated | Provincial cost-of-production data |
| Rice price swings (1.9× in 2 years) | Income ranking flips depending on year | Use farmer's price; show a range |
| Berseem has no heat limit or stage lengths | Its heat risk and water use are not calculated | FAO / PARC sources |
| Hyderabad 2025–26 rabi rainfall reads 424 mm in POWER | Unusually high for Hyderabad; lowers wheat irrigation need there | Check against PMD records or GPM IMERG |
| GPM IMERG not fetched | No higher-resolution rainfall | Run `scripts/fetch_gpm.py` once GES DISC is reachable |
| Urdu tips unreviewed | Can't claim farmer-ready Urdu | Native-speaker and agronomist review |
| No farmer or expert validation | All results are model estimates | Pilot with an extension office |
| No market-size or customer data | Business slide has no numbers yet | Research before the deck |

---

## Reproducing these numbers

From `backend/`, with the API running locally:

```bash
uv run pytest -q
```

Comparisons: `POST /api/rotations/compare`; history: `POST /api/history`; satellite context:
`GET /api/satellite?latitude=..&longitude=..`; soil: `GET /api/soil`. Request bodies use the inputs in
section 3. Results change slightly as NASA POWER adds new days and as GRACE adds new months.
