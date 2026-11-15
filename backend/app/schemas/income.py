"""Income schemas (phase 5)."""

from pydantic import BaseModel, Field

from app.schemas.crop import CropName


class CropEconomics(BaseModel):
    """Farmer-provided values; any left empty fall back to FAOSTAT national averages (yield, price)."""

    yield_t_ha: float | None = Field(default=None, gt=0)
    price_per_t: float | None = Field(default=None, gt=0, description="Farm-gate price, in `currency` per tonne")
    cost_per_ha: float | None = Field(default=None, ge=0, description="Production cost per hectare; no default")
    currency: str = "PKR"


class SeasonIncome(BaseModel):
    crop: CropName
    area_hectares: float
    yield_t_ha: float | None = None
    yield_source: str | None = None
    price_per_t: float | None = None
    price_source: str | None = None
    cost_per_ha: float | None = None
    gross_revenue: float | None = None
    net_income: float | None = Field(default=None, description="Only when costs are given")
    notes: list[str] = Field(default_factory=list)


class RotationIncome(BaseModel):
    currency: str
    seasons: list[SeasonIncome]
    gross_revenue: float | None = Field(default=None, description="Before costs, whole cycle")
    net_income: float | None = Field(default=None, description="After the farmer's costs, whole cycle")
    cycle_years: int = 1
    gross_revenue_per_year: float | None = None
    net_income_per_year: float | None = None
    basis: str = Field(description="'net' when every season has costs, else 'gross'")
