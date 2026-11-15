from datetime import date

from app.schemas.crop import CropName
from app.schemas.income import CropEconomics
from app.schemas.rotation import CropSeason, Rotation
from app.services.income.income import income_scores, load_defaults, rotation_income, season_income
from scripts.build_faostat_defaults import build


def _rot(name: str, *crops: CropName, area: float = 2) -> Rotation:
    return Rotation(name=name, seasons=[
        CropSeason(crop=c, sowing_date=date(2025, 6, 1), harvest_date=date(2025, 9, 30), area_hectares=area)
        for c in crops
    ])


def test_build_uses_latest_price_and_mean_yield_and_flags_jumps():
    out = build(
        yields={"wheat": {2020: 2.0, 2022: 3.0, 2023: 3.0, 2024: 3.3}},
        prices={"wheat": {2023: 100_000, 2024: 90_000}, "rice": {2022: 100_000, 2024: 250_000}, "maize": {}},
    )
    wheat = out["crops"]["wheat"]
    assert wheat["yield_t_ha"] == 3.1 and wheat["yield_years"] == "2022-2024 mean"
    assert wheat["price_per_t"] == 90_000 and wheat["price_years"] == "2024"
    assert not any("changed" in n for n in wheat["notes"])
    assert any("changed 2.5x" in n for n in out["crops"]["rice"]["notes"])
    assert "yield_t_ha" not in out["crops"]["mung_bean"] and out["crops"]["mung_bean"]["notes"]


def test_committed_defaults_cover_cereals_only():
    crops = load_defaults()["crops"]
    for c in ("wheat", "rice", "maize"):
        assert crops[c]["yield_t_ha"] > 0 and crops[c]["price_per_t"] > 0
    assert "price_per_t" not in crops["mung_bean"] and "price_per_t" not in crops["berseem"]


def test_default_income_and_farmer_override():
    defaults = load_defaults()
    wheat = season_income(CropName.WHEAT, 2, None, defaults)
    d = defaults["crops"]["wheat"]
    assert wheat.gross_revenue == round(2 * d["yield_t_ha"] * d["price_per_t"])
    assert wheat.yield_source.startswith("FAOSTAT") and wheat.net_income is None

    given = CropEconomics(yield_t_ha=4, price_per_t=100_000, cost_per_ha=150_000)
    mine = season_income(CropName.WHEAT, 2, given, defaults)
    assert mine.yield_source == "farmer" and mine.gross_revenue == 800_000 and mine.net_income == 500_000

    mung = season_income(CropName.MUNG_BEAN, 2, None, defaults)
    assert mung.gross_revenue is None and any("mung bean" in n for n in mung.notes)


def test_rotation_without_defaults_gets_no_income_score():
    cereals = rotation_income(_rot("RW", CropName.RICE, CropName.WHEAT), None)
    with_mung = rotation_income(_rot("MW", CropName.MUNG_BEAN, CropName.WHEAT), None)
    assert cereals.gross_revenue and with_mung.gross_revenue is None
    assert income_scores([cereals, with_mung]) == [1.0, None]
