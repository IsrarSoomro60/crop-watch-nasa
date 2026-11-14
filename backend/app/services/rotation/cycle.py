"""Rotation cycle length, so rotations of different lengths are compared per year.

A rotation's seasons describe one cycle that then repeats. The cycle starts at the first sowing
and lasts the smallest whole number of years that contains every sowing date: rice (June) then
wheat (November) is a 1-year cycle; wheat in Nov 2025 and again in Nov 2026 is a 2-year cycle.
Water, income and bare-soil days are divided by this number before rotations are compared.
"""

from datetime import date

from app.schemas.rotation import Rotation


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February in a non-leap year
        return d.replace(year=d.year + years, day=28)


def cycle_years(rotation: Rotation) -> int:
    first = min(s.sowing_date for s in rotation.seasons)
    last = max(s.sowing_date for s in rotation.seasons)
    years = 1
    while last >= add_years(first, years):
        years += 1
    return years


def per_year(total: float | None, years: int) -> float | None:
    return None if total is None else round(total / years, 0)
