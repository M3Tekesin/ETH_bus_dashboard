import pytest

from app.db import get_pool

pytestmark = pytest.mark.asyncio


def _sample_records():
    return {
        "records": [
            {"time": "2021-07-26T03:53:27Z", "bus_id": "B183",
             "speed_ms": 0.0, "ambient_temp_k": 295.15, "power_w": 1594.8,
             "passengers": "NaN", "bus_route": "-", "door_open": 1,
             "grid_available": 1},
            {"time": "2021-07-26T03:53:28Z", "bus_id": "B183",
             "speed_ms": 5.0, "ambient_temp_k": 295.15, "power_w": 5356.9,
             "passengers": 3, "bus_route": "33", "door_open": 0,
             "grid_available": 1},
        ]
    }


async def test_batch_insert_returns_count(client, clean_db):
    resp = await client.post("/api/telemetry/batch", json=_sample_records())
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 2


async def test_inserted_rows_are_queryable(client, clean_db):
    await client.post("/api/telemetry/batch", json=_sample_records())
    pool = get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM telemetry")
        passengers = await conn.fetchval(
            "SELECT passengers FROM telemetry ORDER BY time LIMIT 1"
        )
    assert count == 2
    assert passengers is None  # "NaN" normalized to NULL
