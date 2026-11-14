"""Income per rotation from yield x price (minus costs when the farmer gives them).

Defaults are FAOSTAT national averages for Pakistan (see app/domain/economics/
faostat_pakistan.json and scripts/build_faostat_defaults.py): they are country-level
annual figures, not local or current market prices, and no default cost exists, so
default results are gross revenue only.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import APP_DIR
from app.schemas.crop import CropName
from app.schemas.income import CropEconomics, RotationIncome, SeasonIncome
from app.schemas.rotation import Rotation

DEFAULTS_PATH = APP_DIR / "domain" / "economics" / "faostat_pakistan.json"


@lru_cache
def load_defaults(path: Path = DEFAULTS_PATH) -> dict:
    if not path.exists():
        return {"crops": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def season_income(crop: CropName, area: float, given: CropEconomics | None, defaults: dict) -> SeasonIncome:
    d = defaults.get("crops", {}).get(crop.value, {})
    result = SeasonIncome(crop=crop, area_hectares=area)
    currency = defaults.get("currency", "PKR")
    if given and given.currency != currency and (given.yield_t_ha is None or given.price_per_t is None):
        result.notes.append(
            f"Given values are in {given.currency}; FAOSTAT defaults are {currency}, so they are not mixed."
        )
        d = {}

    if given and given.yield_t_ha:
        result.yield_t_ha, result.yield_source = given.yield_t_ha, "farmer"
    elif d.get("yield_t_ha"):
        result.yield_t_ha = d["yield_t_ha"]
        result.yield_source = f"FAOSTAT Pakistan average {d['yield_years']}"
    if given and given.price_per_t:
        result.price_per_t, result.price_source = given.price_per_t, "farmer"
    elif d.get("price_per_t"):
        result.price_per_t = d["price_per_t"]
        result.price_source = f"FAOSTAT Pakistan producer price {d['price_years']}"
    if given and given.cost_per_ha is not None:
        result.cost_per_ha = given.cost_per_ha

    if result.yield_t_ha is None or result.price_per_t is None:
        result.notes.append("No yield or price available; enter local values to include this crop.")
        return result
    result.gross_revenue = round(area * result.yield_t_ha * result.price_per_t, 0)
    if result.cost_per_ha is not None:
        result.net_income = round(result.gross_revenue - area * result.cost_per_ha, 0)
    return result


def rotation_income(rotation: Rotation, economics: dict[CropName, CropEconomics] | None) -> RotationIncome:
    defaults = load_defaults()
    economics = economics or {}
    seasons = [season_income(s.crop, s.area_hectares, economics.get(s.crop), defaults) for s in rotation.seasons]
    currency = next((e.currency for e in economics.values()), defaults.get("currency", "PKR"))
    complete = all(s.gross_revenue is not None for s in seasons)
    net = complete and all(s.net_income is not None for s in seasons)
    return RotationIncome(
        currency=currency,
        seasons=seasons,
        gross_revenue=round(sum(s.gross_revenue for s in seasons), 0) if complete else None,  # type: ignore[misc]
        net_income=round(sum(s.net_income for s in seasons), 0) if net else None,  # type: ignore[misc]
        basis="net" if net else "gross",
    )


def income_scores(incomes: list[RotationIncome]) -> list[float | None]:
    """Highest income = 1.0, others = own / highest. Net income only if every rotation has it."""
    use_net = all(i.net_income is not None for i in incomes)
    values = [(i.net_income if use_net else i.gross_revenue) for i in incomes]
    known = [v for v in values if v is not None]
    if not known or max(known) <= 0:
        return [None] * len(values)
    top = max(known)
    return [None if v is None else round(max(v, 0) / top, 3) for v in values]
