"""Bare-soil days: how long the land has no crop over a one-year rotation cycle.

Uses only the farmer's sowing and harvest dates. Land is counted as covered on a
day when the crops growing that day cover the farm area (the largest season area).
This counts growing crops only; residue or weeds are not known (see the challenge's
NDVI caveat: vegetation indices also can't reliably tell residue from bare soil).
"""

from datetime import timedelta

from app.schemas.rotation import GroundCover, Rotation

CYCLE_DAYS = 365


def ground_cover(rotation: Rotation) -> GroundCover:
    start = min(s.sowing_date for s in rotation.seasons)
    farm_area = max(s.area_hectares for s in rotation.seasons)
    covered_ha_days = 0.0
    bare_days = 0
    for i in range(CYCLE_DAYS):
        day = start + timedelta(days=i)
        area = sum(s.area_hectares for s in rotation.seasons if s.sowing_date <= day <= s.harvest_date)
        covered = min(area, farm_area)
        covered_ha_days += covered
        bare_days += covered == 0
    return GroundCover(
        cycle_start=start,
        cycle_end=start + timedelta(days=CYCLE_DAYS - 1),
        bare_soil_days=bare_days,
        cover_fraction=round(covered_ha_days / (farm_area * CYCLE_DAYS), 3),
    )
