"""Environmental observation schemas."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.farm import DataSource, Location


class DailyObservation(BaseModel):
    day: date
    tmean_c: float | None = None
    tmax_c: float | None = None
    tmin_c: float | None = None
    precipitation_mm: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_ms: float | None = None
    solar_radiation_mj_m2: float | None = None
    surface_soil_moisture: float | None = Field(default=None, description="GWETTOP, 0 dry to 1 saturated")
    soil_moisture: float | None = Field(default=None, description="GWETROOT root zone, 0 dry to 1 saturated")
    source: DataSource = DataSource.SATELLITE


class DataNote(BaseModel):
    """Tells the user where the weather data came from and how current it is."""

    source: str = "NASA POWER daily point API (AG community)"
    grid_cell_center: Location
    elevation_m: float | None = Field(default=None, description="Grid-cell elevation reported by NASA POWER")
    requested_start: date
    requested_end: date
    latest_observation_date: date | None = Field(
        default=None, description="Last day with a non-missing temperature value ('as of' date)"
    )
    from_cache: bool = False
    from_sample: bool = Field(default=False, description="True when a saved offline sample was used")
    note: str = (
        "Values are for a ~50 km grid cell, not a single field, and usually lag real time by 2-3 days."
    )


class EnvironmentalData(BaseModel):
    observations: list[DailyObservation]
    data_note: DataNote
