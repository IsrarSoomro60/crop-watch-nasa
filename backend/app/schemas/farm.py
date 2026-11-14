"""Farm input schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class DataSource(StrEnum):
    """Where an input value came from, so uncertainty stays visible."""

    MEASURED = "measured"
    SATELLITE = "satellite"
    ESTIMATED = "estimated"
    FARMER = "farmer"


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Priorities(BaseModel):
    """Farmer-selected weights; normalised to sum to 1 when scoring."""

    soil_health: float = Field(default=0.25, ge=0)
    water: float = Field(default=0.25, ge=0)
    income: float = Field(default=0.25, ge=0)
    resilience: float = Field(default=0.25, ge=0)


class FarmResources(BaseModel):
    area_hectares: float = Field(gt=0)
    irrigation_available: bool | None = None
    soil_type: str | None = None
    source: DataSource = DataSource.FARMER


class FarmCreate(BaseModel):
    name: str
    location: Location
    resources: FarmResources
    priorities: Priorities = Field(default_factory=Priorities)


class Farm(FarmCreate):
    id: str
