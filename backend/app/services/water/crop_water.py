"""Crop water use and irrigation need per season and per rotation.

Method (all FAO, simplified):
- Crop water use ETc = Kc x ETo (FAO-56 single crop coefficient, chapter 6). The Kc curve is
  Kc ini over the initial stage, linear to Kc mid over development, Kc mid over mid-season,
  then linear to Kc end over the late season (FAO-56 Fig. 25).
- Effective rainfall Pe per calendar month: 0.8P - 25 if P > 75 mm/month, else 0.6P - 10,
  never negative (FAO Irrigation Water Management Training Manual 3, section 4.2).
- Irrigation need IN = ETc - Pe. Paddy rice adds soaking (200 mm), percolation/seepage
  (6 mm/day average) and water-layer establishment (100 mm) (same manual, section 4.4).
"""

from collections import defaultdict
from datetime import date, timedelta

from app.schemas.crop import CropProfile
from app.schemas.environment import DailyObservation
from app.schemas.rotation import CropSeason, RotationWater, SeasonWater
from app.services.risk.risk_engine import stage_spans
from app.services.water.et0 import daily_et0

FAO_MANUAL_3 = "FAO Irrigation Water Management Training Manual 3, ch. 4, https://www.fao.org/4/s2022e/s2022e08.htm"
PADDY_SATURATION_MM = 200.0
PADDY_PERCOLATION_MM_DAY = 6.0  # manual's average of 4 (heavy clay) to 8 (sandy) mm/day
PADDY_WATER_LAYER_MM = 100.0
M3_PER_MM_HA = 10.0

# FAO manual: 4 mm/day for heavy clay, 8 for sandy soils, 6 on average. Mapping USDA texture
# classes onto those three cases is our choice.
_HEAVY_CLAY = {"clay", "silty clay"}
_SANDY = {"sand", "loamy sand", "sandy loam"}


def paddy_percolation(texture: str | None) -> tuple[float, str]:
    if texture in _HEAVY_CLAY:
        return 4.0, f"heavy clay ({texture}, SoilGrids)"
    if texture in _SANDY:
        return 8.0, f"sandy soil ({texture}, SoilGrids)"
    if texture:
        return PADDY_PERCOLATION_MM_DAY, f"medium soil ({texture}, SoilGrids)"
    return PADDY_PERCOLATION_MM_DAY, "FAO average; soil texture unknown"


def kc_curve(profile: CropProfile, season_days: int) -> list[float] | None:
    spans = stage_spans(profile, season_days)
    if profile.kc is None or spans is None or len(spans) != 4:
        return None
    kc = profile.kc
    (_, i0, i1), (_, d0, d1), (_, m0, m1), (_, l0, l1) = spans
    curve: list[float] = []
    for day in range(season_days):
        if day < i1:
            curve.append(kc.ini)
        elif day < d1:
            curve.append(kc.ini + (kc.mid - kc.ini) * (day - d0 + 1) / max(d1 - d0, 1))
        elif day < m1:
            curve.append(kc.mid)
        else:
            curve.append(kc.mid + (kc.end - kc.mid) * (day - l0 + 1) / max(l1 - l0, 1))
    return curve


def effective_rainfall(days: list[date], rain: list[float]) -> float:
    """FAO monthly formula, applied to each calendar-month part of the season pro rata."""
    by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    for d, p in zip(days, rain, strict=True):
        by_month[(d.year, d.month)].append(p)
    total = 0.0
    for values in by_month.values():
        n = len(values)
        p30 = sum(values) * 30 / n  # scale part-month to a 30-day month
        pe30 = 0.8 * p30 - 25 if p30 > 75 else 0.6 * p30 - 10
        total += max(pe30, 0.0) * n / 30
    return total


def season_water(
    profile: CropProfile,
    season: CropSeason,
    observations: list[DailyObservation],
    latitude: float,
    elevation_m: float,
    soil_texture: str | None = None,
) -> SeasonWater:
    season_days = (season.harvest_date - season.sowing_date).days + 1
    days = [season.sowing_date + timedelta(days=i) for i in range(season_days)]
    result = SeasonWater(crop=season.crop, sowing_date=season.sowing_date, area_hectares=season.area_hectares)

    curve = kc_curve(profile, season_days)
    if curve is None:
        result.notes.append("Not calculated: crop coefficients or stage lengths missing for this crop.")
        return result

    by_day = {o.day: o for o in observations}
    et0_total = etc_total = 0.0
    rain: list[float] = []
    hargreaves_days = missing = 0
    for d, kc in zip(days, curve, strict=True):
        o = by_day.get(d)
        et0, method = (None, None) if o is None else daily_et0(
            d, latitude, elevation_m, o.tmax_c, o.tmin_c, o.relative_humidity_pct, o.wind_speed_ms,
            o.solar_radiation_mj_m2,
        )
        if et0 is None or o is None or o.precipitation_mm is None:
            missing += 1
            continue
        hargreaves_days += method == "hargreaves"
        et0_total += et0
        etc_total += kc * et0
        rain.append(o.precipitation_mm)

    if missing:
        result.notes.append(
            f"Not calculated: weather missing for {missing} of {season_days} days "
            "(future or very recent dates need a climatology, planned for phase 6)."
        )
        return result

    pe = effective_rainfall(days, rain)
    paddy = 0.0
    if profile.water_regime == "paddy":
        perc, basis = paddy_percolation(soil_texture)
        paddy = PADDY_SATURATION_MM + perc * season_days + PADDY_WATER_LAYER_MM
        result.notes.append(
            f"Paddy: adds {PADDY_SATURATION_MM:.0f} mm soaking, {perc:.0f} mm/day percolation ({basis}; "
            f"FAO: 4 heavy clay, 6 average, 8 sandy) and {PADDY_WATER_LAYER_MM:.0f} mm water layer."
        )
    if hargreaves_days:
        result.notes.append(
            f"ETo for {hargreaves_days} day(s) used the Hargreaves equation (radiation, humidity or wind missing)."
        )

    result.et0_mm = round(et0_total, 1)
    result.crop_water_use_mm = round(etc_total, 1)
    result.rainfall_mm = round(sum(rain), 1)
    result.effective_rainfall_mm = round(pe, 1)
    result.paddy_extra_mm = round(paddy, 1)
    result.irrigation_need_mm = round(max(etc_total + paddy - pe, 0.0), 1)
    return result


def rotation_water(
    profiles: dict, seasons: list[CropSeason], observations: list[DailyObservation],
    latitude: float, elevation_m: float, soil_texture: str | None = None,
    fallback: dict | None = None,
) -> RotationWater:
    """`fallback` maps (crop, sowing_date, harvest_date) to a WaterHistory used when weather is missing."""
    results = [
        season_water(profiles[s.crop], s, observations, latitude, elevation_m, soil_texture) for s in seasons
    ]
    for season, result in zip(seasons, results, strict=True):
        hist = (fallback or {}).get((season.crop, season.sowing_date, season.harvest_date))
        if result.irrigation_need_mm is None and hist is not None:
            result.irrigation_need_mm = hist.median_irrigation_need_mm
            result.crop_water_use_mm = hist.median_crop_water_use_mm
            result.estimated_from_history = True
            result.notes.append(
                f"Estimated: median of {hist.years_calculated} past seasons with the same dates "
                f"(1-in-5 seasons need more than {hist.p80_irrigation_need_mm:.0f} mm)."
            )
    complete = all(r.irrigation_need_mm is not None for r in results)
    total = (
        round(sum(r.irrigation_need_mm * r.area_hectares * M3_PER_MM_HA for r in results), 0)  # type: ignore[operator]
        if complete else None
    )
    return RotationWater(
        seasons=results,
        irrigation_need_m3=total,
        method=[
            "Crop water use = FAO-56 Kc x ETo (FAO Penman-Monteith; Hargreaves when inputs are missing).",
            "Kc not adjusted for local wind and minimum humidity (FAO-56 eq. 62); POWER mean humidity only.",
            f"Effective rainfall and paddy additions: {FAO_MANUAL_3}.",
            "Groundwater capillary rise and irrigation efficiency losses are not included.",
        ],
    )
