from fastapi import APIRouter

from ..db import get_pool
from ..models import BatchResponse, TelemetryBatch

router = APIRouter(prefix="/api", tags=["ingest"])

_COLUMNS = [
    "time", "bus_id", "speed_ms", "ambient_temp_k", "power_w",
    "traction_force_n", "passengers", "bus_route", "stop_name",
    "door_open", "grid_available", "lat", "lon", "altitude",
]


@router.post("/telemetry/batch", response_model=BatchResponse)
async def ingest_batch(batch: TelemetryBatch) -> BatchResponse:
    if not batch.records:
        return BatchResponse(inserted=0)
    rows = [r.to_row() for r in batch.records]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.copy_records_to_table(
            "telemetry", records=rows, columns=_COLUMNS
        )
    return BatchResponse(inserted=len(rows))
