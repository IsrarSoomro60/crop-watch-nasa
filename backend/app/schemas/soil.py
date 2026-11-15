"""Soil schemas (SoilGrids 2.0, ISRIC)."""

from pydantic import BaseModel, Field

from app.schemas.farm import DataSource, Location


class SoilLayer(BaseModel):
    depth: str = Field(description="e.g. '0-5cm'")
    top_cm: int
    bottom_cm: int
    clay_pct: float | None = None
    sand_pct: float | None = None
    silt_pct: float | None = None
    organic_carbon_g_kg: float | None = None
    ph_h2o: float | None = None
    bulk_density_kg_dm3: float | None = None


class SoilInfo(BaseModel):
    """Modelled topsoil properties near a location. Not a field measurement."""

    requested_location: Location
    used_location: Location = Field(description="Point SoilGrids returned data for")
    distance_km: float = Field(description="Distance from the requested point to the used point")
    layers: list[SoilLayer]
    topsoil_0_30cm: SoilLayer = Field(description="Depth-weighted average of the 0-30 cm layers")
    texture_class: str | None = Field(default=None, description="USDA texture class of the 0-30 cm average")
    source: str = "SoilGrids 2.0 (ISRIC), 250 m machine-learning predictions, https://soilgrids.org"
    data_source: DataSource = DataSource.ESTIMATED
    from_sample: bool = False
    notes: list[str] = Field(default_factory=list)
