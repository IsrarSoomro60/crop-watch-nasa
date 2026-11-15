"""Drought risk as rainfed root-zone water stress (FAO-56 chapter 8).

Daily root-zone depletion (FAO-56 eq. 85, without irrigation, runoff or capillary rise):
    Dr_i = clamp(Dr_{i-1} - P_i + ETc_i, 0, TAW_i)
    TAW = 1000 (θFC - θWP) Zr        (eq. 82; θFC - θWP from Table 19 by soil texture)
    RAW = p TAW, p = p_table + 0.04 (5 - ETc), kept within 0.1-0.8   (eq. 83, Table 22)
    Ks  = (TAW - Dr) / ((1 - p) TAW) when Dr > RAW, else 1          (eq. 84)
Roots grow linearly from 0.2 m at sowing to the Table 22 maximum at the start of
mid-season (eq. 8 approximation). The soil starts at field capacity at sowing.

Severity: Moderate once stress starts (Dr > RAW, FAO's definition); High once
Ks <= 0.5, i.e. transpiration halved. The 0.5 cut-off is our provisional choice.
This is the stress a crop would face WITHOUT irrigation: on irrigated farms it shows
irrigation dependence, not proof of drought.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain import scoring_config as cfg
from app.schemas.crop import CropProfile, StageType
from app.schemas.environment import DailyObservation
from app.services.stages import stage_spans
from app.services.water.crop_water import kc_curve
from app.services.water.et0 import daily_et0

FAO56_CH8 = "FAO-56 chapter 8 (eqs. 82-85, Tables 19 and 22), https://www.fao.org/4/x0490e/x0490e0e.htm"
ZR_START_M = 0.2
KS_HIGH = 0.5

# FAO-56 Table 19: midpoint of (θFC - θWP) range, m3/m3, by USDA texture.
TABLE19_AVAILABLE_WATER = {
    "sand": 0.08, "loamy sand": 0.09, "sandy loam": 0.13, "loam": 0.155, "silt loam": 0.16,
    "silt": 0.18, "silty clay loam": 0.155, "silty clay": 0.16, "clay": 0.16,
}
FALLBACK_TEXTURE = "loam"


@dataclass(frozen=True)
class Site:
    latitude: float
    elevation_m: float
    soil_texture: str | None = None


def available_water(texture: str | None) -> tuple[float, str]:
    if texture in TABLE19_AVAILABLE_WATER:
        return TABLE19_AVAILABLE_WATER[texture], f"{texture} (FAO-56 Table 19)"
    reason = f"{texture} is not in FAO-56 Table 19" if texture else "soil texture unknown"
    return TABLE19_AVAILABLE_WATER[FALLBACK_TEXTURE], f"{reason}; loam value used"


def drought_severities(
    profile: CropProfile,
    sowing: date,
    season_days: int,
    observations: list[DailyObservation],
    site: Site,
) -> tuple[list[float | None], str] | None:
    """Daily drought severity (None = no weather that day), or None if the method can't apply."""
    ws = profile.water_stress
    spans = stage_spans(profile, season_days)
    curve = kc_curve(profile, season_days)
    if ws is None or profile.water_regime == "paddy" or spans is None or curve is None:
        return None
    aw, aw_basis = available_water(site.soil_texture)
    full_root_day = next((start for st, start, _ in spans if st == StageType.REPRODUCTIVE), season_days)
    by_day = {o.day: o for o in observations}

    severities: list[float | None] = []
    dr = 0.0
    broken = False
    for i in range(season_days):
        d = sowing + timedelta(days=i)
        o = by_day.get(d)
        et0 = None if o is None else daily_et0(d, site.latitude, site.elevation_m, o.tmax_c, o.tmin_c,
                                                o.relative_humidity_pct, o.wind_speed_ms, o.solar_radiation_mj_m2)[0]
        if broken or et0 is None or o is None or o.precipitation_mm is None:
            broken = True  # the water balance can't continue across a gap
            severities.append(None)
            continue
        zr = ZR_START_M + (ws.zr_max_m - ZR_START_M) * min(i / max(full_root_day, 1), 1.0)
        taw = 1000 * aw * zr
        etc = curve[i] * et0
        p = min(max(ws.p + 0.04 * (5 - etc), 0.1), 0.8)
        dr = min(max(dr - o.precipitation_mm + etc, 0.0), taw)
        if dr <= p * taw:
            severities.append(cfg.SEVERITY_NONE)
        else:
            ks = (taw - dr) / ((1 - p) * taw)
            severities.append(cfg.SEVERITY_CRITICAL if ks <= KS_HIGH else cfg.SEVERITY_WARNING)
    basis = (f"Drought = rainfed root-zone water stress, {FAO56_CH8}; soil water {aw_basis}; "
             f"max root depth {ws.zr_max_m} m, p {ws.p}. Shows stress without irrigation.")
    return severities, basis
