from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from .conversions import (
    clean_float, clean_int, clean_speed_ms, clean_temp_k, clean_text,
)


class TelemetryRecord(BaseModel):
    time: datetime
    bus_id: str
    speed_ms: float | None = None
    ambient_temp_k: float | None = None
    power_w: float | None = None
    traction_force_n: float | None = None
    passengers: int | None = None
    bus_route: str | None = None
    stop_name: str | None = None
    door_open: bool | None = None
    grid_available: bool | None = None
    lat: float | None = None
    lon: float | None = None
    altitude: float | None = None

    @field_validator("power_w", "traction_force_n", "lat", "lon",
                     "altitude", mode="before")
    @classmethod
    def _clean_float(cls, v):
        return clean_float(v)

    @field_validator("speed_ms", mode="before")
    @classmethod
    def _clean_speed(cls, v):
        return clean_speed_ms(v)

    @field_validator("ambient_temp_k", mode="before")
    @classmethod
    def _clean_temp(cls, v):
        return clean_temp_k(v)

    @field_validator("passengers", mode="before")
    @classmethod
    def _clean_int(cls, v):
        return clean_int(v)

    @field_validator("bus_route", "stop_name", mode="before")
    @classmethod
    def _clean_text(cls, v):
        return clean_text(v)

    def to_row(self) -> tuple:
        return (
            self.time, self.bus_id, self.speed_ms, self.ambient_temp_k,
            self.power_w, self.traction_force_n, self.passengers,
            self.bus_route, self.stop_name, self.door_open,
            self.grid_available, self.lat, self.lon, self.altitude,
        )


class TelemetryBatch(BaseModel):
    records: list[TelemetryRecord]


class BatchResponse(BaseModel):
    inserted: int


class Kpis(BaseModel):
    avg_speed_kmh: float | None = None
    max_speed_kmh: float | None = None
    max_temp_c: float | None = None
    total_energy_kwh: float | None = None
    distance_km: float | None = None
    avg_passengers: float | None = None
    max_passengers: int | None = None
    sample_count: int = 0


class TrendPoint(BaseModel):
    bucket: datetime
    value: float | None = None


class TrendByBusPoint(BaseModel):
    bucket: datetime
    bus_id: str
    value: float | None = None


class DistributionBin(BaseModel):
    lower: float
    upper: float
    count: int


class Distribution(BaseModel):
    bins: list[DistributionBin] = []
    min: float | None = None
    q1: float | None = None
    median: float | None = None
    q3: float | None = None
    max: float | None = None
