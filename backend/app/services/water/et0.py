"""Reference evapotranspiration (ETo) following FAO-56 (Allen et al. 1998).

Equation numbers refer to FAO Irrigation and Drainage Paper 56, chapters 2-4:
https://www.fao.org/4/x0490e/x0490e00.htm

Daily inputs come from NASA POWER: Tmax/Tmin (C), mean relative humidity (%),
2 m wind speed (m/s), all-sky surface solar radiation (MJ/m2/day in the AG community).
"""

import math
from datetime import date

GSC = 0.0820  # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9  # Stefan-Boltzmann, MJ K-4 m-2 day-1


def sat_vapour_pressure(t: float) -> float:
    """e°(T), kPa (eq. 11)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def psychrometric_constant(elevation_m: float) -> float:
    """gamma, kPa/C, from atmospheric pressure at elevation (eqs. 7-8)."""
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26
    return 0.000665 * pressure


def extraterrestrial_radiation(latitude: float, day: date) -> float:
    """Ra, MJ m-2 day-1 (eqs. 21-25)."""
    j = day.timetuple().tm_yday
    phi = math.radians(latitude)
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    delta = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return (24 * 60 / math.pi) * GSC * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def penman_monteith(
    tmax: float,
    tmin: float,
    ea: float,
    rs: float,
    u2: float,
    latitude: float,
    day: date,
    elevation_m: float,
) -> float:
    """FAO Penman-Monteith ETo, mm/day (eq. 6). `rs` in MJ m-2 day-1, `ea` in kPa."""
    tmean = (tmax + tmin) / 2
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2  # eq. 12
    delta = 4098 * sat_vapour_pressure(tmean) / (tmean + 237.3) ** 2  # eq. 13
    gamma = psychrometric_constant(elevation_m)

    ra = extraterrestrial_radiation(latitude, day)
    rso = (0.75 + 2e-5 * elevation_m) * ra  # eq. 37
    rns = (1 - 0.23) * rs  # eq. 38, albedo 0.23
    rs_rso = min(rs / rso, 1.0) if rso > 0 else 1.0
    rnl = (
        SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2
        * (0.34 - 0.14 * math.sqrt(max(ea, 0.0)))
        * (1.35 * rs_rso - 0.35)
    )  # eq. 39
    rn = rns - rnl  # eq. 40; soil heat flux G ~ 0 for daily steps (eq. 42)

    et0 = (0.408 * delta * rn + gamma * (900 / (tmean + 273)) * u2 * (es - ea)) / (
        delta + gamma * (1 + 0.34 * u2)
    )
    return max(et0, 0.0)


def actual_vapour_pressure_from_rh_mean(tmax: float, tmin: float, rh_mean: float) -> float:
    """ea from mean relative humidity, kPa (eq. 19)."""
    return rh_mean / 100 * (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2


def hargreaves(tmax: float, tmin: float, latitude: float, day: date) -> float:
    """Hargreaves ETo, mm/day (eq. 52), FAO-56's fallback when radiation/humidity/wind are missing."""
    tmean = (tmax + tmin) / 2
    ra_mm = 0.408 * extraterrestrial_radiation(latitude, day)
    return max(0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0)) * ra_mm, 0.0)


def daily_et0(
    day: date,
    latitude: float,
    elevation_m: float,
    tmax: float | None,
    tmin: float | None,
    rh_mean: float | None,
    u2: float | None,
    rs_mj: float | None,
) -> tuple[float | None, str | None]:
    """Returns (ETo mm/day, method) or (None, None) when temperature is missing."""
    if tmax is None or tmin is None:
        return None, None
    if rh_mean is not None and u2 is not None and rs_mj is not None:
        ea = actual_vapour_pressure_from_rh_mean(tmax, tmin, rh_mean)
        return penman_monteith(tmax, tmin, ea, rs_mj, u2, latitude, day, elevation_m), "penman_monteith"
    return hargreaves(tmax, tmin, latitude, day), "hargreaves"
