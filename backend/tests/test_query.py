import pytest

pytestmark = pytest.mark.asyncio


async def _seed(client):
    recs = []
    # 120 seconds of data, speed ramps 0..10 m/s, constant 3600 W, B183
    for i in range(120):
        recs.append({
            "time": f"2021-07-26T04:00:{i:02d}Z" if i < 60
                    else f"2021-07-26T04:01:{i-60:02d}Z",
            "bus_id": "B183",
            "speed_ms": float(i % 11),
            "ambient_temp_k": 300.15,
            "power_w": 3600.0,
        })
    await client.post("/api/telemetry/batch", json={"records": recs})
    # refresh continuous aggregate so KPIs/trend see the data
    from app.db import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "CALL refresh_continuous_aggregate('telemetry_1min', NULL, NULL)"
        )


async def test_buses_lists_seeded_bus(client, clean_db):
    await _seed(client)
    resp = await client.get("/api/buses")
    assert resp.json() == ["B183"]


async def test_kpis_energy_and_temp(client, clean_db):
    await _seed(client)
    k = (await client.get("/api/kpis")).json()
    # 3600 W * 120 samples = 432000 Wh? No: sum=432000 W -> /3600/1000 = 0.12 kWh
    assert abs(k["total_energy_kwh"] - 0.12) < 1e-6
    assert abs(k["max_temp_c"] - 27.0) < 1e-6
    assert k["sample_count"] == 120


async def test_trend_returns_points(client, clean_db):
    await _seed(client)
    pts = (await client.get("/api/trend?metric=speed&bucket=60")).json()
    assert len(pts) >= 2
    assert all("bucket" in p and "value" in p for p in pts)


async def test_distribution_bins_sum_to_count(client, clean_db):
    await _seed(client)
    d = (await client.get("/api/distribution?metric=speed&bins=5")).json()
    assert sum(b["count"] for b in d["bins"]) == 120
    assert d["median"] is not None


async def _refresh(pool):
    async with pool.acquire() as conn:
        await conn.execute(
            "CALL refresh_continuous_aggregate('telemetry_1min', NULL, NULL)"
        )


async def _seed_second_bus(client):
    recs = [{
        "time": f"2022-07-16T05:30:{i:02d}Z",
        "bus_id": "B208",
        "speed_ms": float(i % 7),
        "ambient_temp_k": 295.15,
        "power_w": 5000.0,
    } for i in range(60)]
    await client.post("/api/telemetry/batch", json={"records": recs})
    from app.db import get_pool
    await _refresh(get_pool())


async def test_time_range_reports_min_and_max(client, clean_db):
    await _seed(client)
    tr = (await client.get("/api/time-range?bus=B183")).json()
    assert tr["min"] is not None and tr["max"] is not None
    assert tr["min"] <= tr["max"]


async def test_trend_by_bus_returns_all_buses(client, clean_db):
    await _seed(client)
    await _seed_second_bus(client)
    rows = (await client.get("/api/trend-by-bus?metric=speed&bucket=300")).json()
    assert {r["bus_id"] for r in rows} == {"B183", "B208"}


async def test_trend_by_bus_filters_to_requested_buses(client, clean_db):
    await _seed(client)
    await _seed_second_bus(client)
    rows = (await client.get("/api/trend-by-bus?metric=speed&buses=B208")).json()
    assert {r["bus_id"] for r in rows} == {"B208"}


async def test_unknown_metric_returns_422(client, clean_db):
    await _seed(client)
    assert (await client.get("/api/trend?metric=bogus")).status_code == 422
    assert (await client.get("/api/distribution?metric=bogus")).status_code == 422
    assert (await client.get("/api/trend-by-bus?metric=bogus")).status_code == 422


async def test_negative_speed_clamped_on_ingest(client, clean_db):
    await client.post("/api/telemetry/batch", json={"records": [
        {"time": "2021-07-26T04:00:00Z", "bus_id": "B183", "speed_ms": -0.2},
    ]})
    from app.db import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        speed = await conn.fetchval("SELECT speed_ms FROM telemetry LIMIT 1")
    assert speed == 0.0
