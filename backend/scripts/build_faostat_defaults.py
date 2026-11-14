"""Build app/domain/economics/faostat_pakistan.json from FAOSTAT bulk downloads.

Download (no login) and pass the two zip files:
    https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Asia.zip
    https://bulks-faostat.fao.org/production/Prices_E_Asia.zip

Run from backend/:
    uv run python -m scripts.build_faostat_defaults PRODUCTION_ZIP PRICES_ZIP

Choices (engineering defaults, shown to the user with their years):
  * Yield: mean of the latest 3 years (FAOSTAT element 5412, kg/ha -> t/ha).
  * Price: the latest annual producer price (element 5530, PKR/tonne). Prices in PKR rose fast
    after 2021, so averaging older years would understate them. The previous annual values are
    kept so the user can see how much the series moves.
  * A crop gets a default only when FAOSTAT has a matching item. Mung bean (Vigna radiata) has no
    item of its own (FAOSTAT "Beans, dry" is mostly Phaseolus) and berseem is a fodder crop with no
    FAOSTAT price, so both are left for the farmer to enter.
"""

import csv
import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

from app.core.config import APP_DIR

OUT = APP_DIR / "domain" / "economics" / "faostat_pakistan.json"
PAKISTAN = "165"
ITEMS = {"wheat": "15", "rice": "27", "maize": "56"}  # FAOSTAT item codes
YIELD_YEARS = 3
VOLATILE_RATIO = 1.5  # flag when the latest price differs from the previous one by more than this factor

NOTES = {
    "rice": [
        "FAOSTAT item 'Rice' is paddy (unmilled) rice for all varieties; basmati and coarse rice prices differ a lot.",
    ],
}
NO_DEFAULT = {
    "mung_bean": "No FAOSTAT item for mung bean in Pakistan ('Beans, dry' is a different crop); enter local values.",
    "berseem": "Berseem is a fodder crop with no FAOSTAT yield or price; enter local values.",
}


def _open_csv(zf: zipfile.ZipFile, suffix: str):
    name = next(n for n in zf.namelist() if n.endswith(suffix))
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="latin-1"))


def read_yields(path: Path) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    with zipfile.ZipFile(path) as zf:
        for row in _open_csv(zf, "_NOFLAG.csv"):
            if row["Area Code"] != PAKISTAN or row["Element Code"] != "5412":
                continue
            crop = next((c for c, code in ITEMS.items() if row["Item Code"] == code), None)
            if crop is None:
                continue
            assert row["Unit"] == "kg/ha", row["Unit"]
            out[crop] = {int(k[1:]): float(v) / 1000 for k, v in row.items() if k.startswith("Y") and v}
    return out


def read_prices(path: Path) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {c: {} for c in ITEMS}
    with zipfile.ZipFile(path) as zf:
        for row in _open_csv(zf, "_All_Data_(Normalized).csv"):
            if (row["Area Code"] != PAKISTAN or row["Element Code"] != "5530"
                    or row["Months"] != "Annual value" or not row["Value"]):
                continue
            crop = next((c for c, code in ITEMS.items() if row["Item Code"] == code), None)
            if crop is not None:
                out[crop][int(row["Year"])] = float(row["Value"])
    return out


def build(yields: dict[str, dict[int, float]], prices: dict[str, dict[int, float]]) -> dict:
    crops: dict[str, dict] = {}
    for crop in ITEMS:
        entry: dict = {"notes": list(NOTES.get(crop, []))}
        ys = yields.get(crop, {})
        if ys:
            years = sorted(ys)[-YIELD_YEARS:]
            entry["yield_t_ha"] = round(sum(ys[y] for y in years) / len(years), 2)
            entry["yield_years"] = f"{years[0]}-{years[-1]} mean"
            entry["yield_by_year"] = {str(y): round(ys[y], 3) for y in years}
        ps = prices.get(crop, {})
        if ps:
            years = sorted(ps)
            latest = years[-1]
            entry["price_per_t"] = round(ps[latest])
            entry["price_years"] = str(latest)
            entry["price_by_year"] = {str(y): round(ps[y]) for y in years[-5:]}
            if len(years) >= 2:
                prev = ps[years[-2]]
                ratio = max(ps[latest], prev) / min(ps[latest], prev)
                if ratio > VOLATILE_RATIO:
                    entry["notes"].append(
                        f"FAOSTAT price changed {ratio:.1f}x between {years[-2]} ({prev:,.0f}) and {latest} "
                        f"({ps[latest]:,.0f} PKR/t); check against a local market price."
                    )
        crops[crop] = entry
    for crop, note in NO_DEFAULT.items():
        crops[crop] = {"notes": [note]}
    return {
        "source": "FAOSTAT (FAO), Pakistan: Crops and livestock products (QCL) yield; Producer Prices (PP) annual",
        "currency": "PKR",
        "built": date.today().isoformat(),
        "method": [
            f"Yield = mean of the latest {YIELD_YEARS} FAOSTAT years (national average, all irrigation types).",
            "Price = latest annual FAOSTAT producer price, nominal PKR per tonne (not adjusted for inflation).",
            "National averages: local yields and prices can differ a lot. No production costs are included.",
        ],
        "crops": crops,
    }


def main(production_zip: Path, prices_zip: Path) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(read_yields(production_zip), read_prices(prices_zip)), indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
