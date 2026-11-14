"""Satellite add-on schemas: MODIS NDVI, SMAP soil moisture, GRACE water storage."""

from datetime import date

from pydantic import BaseModel, Field


class NdviPoint(BaseModel):
    date: date
    ndvi: float | None
    reliability: int = Field(description="MODIS pixel reliability: 0 good, 1 marginal, 2 snow/ice, 3 cloudy")
    usable: bool = Field(description="True when reliability is 0 or 1 and a value exists")


class SoilMoisturePoint(BaseModel):
    date: date
    rootzone_m3m3: float
    surface_m3m3: float


class GracePoint(BaseModel):
    date: date
    lwe_cm: float = Field(description="Equivalent water thickness anomaly vs the 2004.0-2009.999 mean")
    uncertainty_cm: float


class GraceSummary(BaseModel):
    cell_lat: float
    cell_lon: float
    trend_cm_per_year: float | None = Field(description="OLS slope over all months; descriptive only")
    latest: GracePoint | None
    series: list[GracePoint]


class SatelliteData(BaseModel):
    district: str
    distance_km: float = Field(description="From the requested point to the district sample point")
    ndvi: list[NdviPoint]
    soil_moisture: list[SoilMoisturePoint]
    grace: GraceSummary | None
    sources: dict[str, str]
    limitations: list[str]
