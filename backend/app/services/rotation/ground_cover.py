"""Bare-soil days: how long the land has no crop over the rotation cycle (1 or more years).

Uses only the farmer's sowing and harvest dates. Land is counted as covered on a
day when the crops growing that day cover the farm area (the largest season area).
This counts growing crops only; residue or weeds are not known (see the challenge's
NDVI caveat: vegetation indices also can't reliably tell residue from bare soil).
"""

from datetime import timedelta

from app.schemas.rotation import GroundCover, Rotation
from app.services.rotation.cycle import add_years, cycle_years


def ground_cover(rotation: Rotation) -> GroundCover:
    start = min(s.sowing_date for s in rotation.seasons)
    years = cycle_years(rotation)
    cycle_days = (add_years(start, years) - start).days
    farm_area = max(s.area_hectares for s in rotation.seasons)
    covered_ha_days = 0.0
    bare_days = 0
    for i in range(cycle_days):
        day = start + timedelta(days=i)
        area = sum(s.area_hectares for s in rotation.seasons if s.sowing_date <= day <= s.harvest_date)
        covered = min(area, farm_area)
        covered_ha_days += covered
        bare_days += covered == 0
    return GroundCover(
        cycle_start=start,
        cycle_end=start + timedelta(days=cycle_days - 1),
        bare_soil_days=bare_days,
        cover_fraction=round(covered_ha_days / (farm_area * cycle_days), 3),
        cycle_years=years,
        bare_soil_days_per_year=round(bare_days / years, 1),
    )
