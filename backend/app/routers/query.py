from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from ..conversions import k_to_c, ms_to_kmh, w_to_kwh
from ..db import get_pool
from ..models import (
    Distribution, DistributionBin, Kpis, TrendByBusPoint, TrendPoint,
)

router = APIRouter(prefix="/api", tags=["query"])

_TREND_EXPR = {
    "speed": "avg(avg_speed_ms)",
    "temp": "avg(avg_temp_k)",
    "power": "avg(avg_power_w)",
}
_DIST_EXPR = {
    "speed": "speed_ms * 3.6",
    "temp": "ambient_temp_k - 273.15",
    "power": "power_w / 1000.0",
}


def _convert_trend(metric: str, v):
    if v is None:
        return None
    if metric == "temp":
        return k_to_c(v)
    if metric == "speed":
        return ms_to_kmh(v)
    return v / 1000.0  # power W -> kW


def _filters(bus, start, end, params: list, col_prefix: str = ""):
    clauses = []
    if bus:
        params.append(bus)
        clauses.append(f"bus_id = ${len(params)}")
    if start:
        params.append(start)
        clauses.append(f"{col_prefix} >= ${len(params)}")
    if end:
        params.append(end)
        clauses.append(f"{col_prefix} <= ${len(params)}")
    return (" WHERE " + " AND ".join(clauses)) if clauses else ""


@router.get("/buses", response_model=list[str])
async def buses() -> list[str]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT bus_id FROM telemetry ORDER BY bus_id")
    return [r["bus_id"] for r in rows]


@router.get("/time-range")
async def time_range(bus: str | None = None) -> dict[str, datetime | None]:
    # Min/max timestamp of available data (optionally per bus), read from the
    # continuous aggregate so it stays fast at scale. Lets the UI default to a
    # bounded recent window instead of querying all-time on first load.
    params: list = []
    where = _filters(bus, None, None, params, "bucket")
    sql = f"SELECT min(bucket) AS min, max(bucket) AS max FROM telemetry_1min{where}"
    pool = get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow(sql, *params)
    return {"min": r["min"] if r else None, "max": r["max"] if r else None}


@router.get("/kpis", response_model=Kpis)
async def kpis(bus: str | None = None, start: datetime | None = None,
               end: datetime | None = None) -> Kpis:
    params: list = []
    where = _filters(bus, start, end, params, "bucket")
    sql = f"""
        SELECT
            sum(sum_speed_ms) AS sum_speed,
            sum(sample_count) AS samples,
            max(max_speed_ms) AS max_speed,
            max(max_temp_k)   AS max_temp,
            sum(sum_power_w)  AS sum_power,
            avg(avg_passengers) AS avg_pax,
            max(max_passengers) AS max_pax
        FROM telemetry_1min{where}
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow(sql, *params)
    if not r or r["samples"] is None:
        return Kpis()
    samples = int(r["samples"])
    sum_speed = float(r["sum_speed"] or 0.0)
    return Kpis(
        avg_speed_kmh=ms_to_kmh(sum_speed / samples) if samples else None,
        max_speed_kmh=ms_to_kmh(r["max_speed"]) if r["max_speed"] is not None else None,
        max_temp_c=k_to_c(r["max_temp"]) if r["max_temp"] is not None else None,
        total_energy_kwh=w_to_kwh(r["sum_power"]) if r["sum_power"] is not None else None,
        distance_km=(sum_speed / 1000.0),  # Σ(m/s · 1s) = meters -> km
        avg_passengers=r["avg_pax"],
        max_passengers=r["max_pax"],
        sample_count=samples,
    )


@router.get("/trend", response_model=list[TrendPoint])
async def trend(metric: str = Query("speed"), bucket: int = Query(300, gt=0),
                bus: str | None = None, start: datetime | None = None,
                end: datetime | None = None) -> list[TrendPoint]:
    if metric not in _TREND_EXPR:
        raise HTTPException(status_code=422, detail=f"unknown metric: {metric}")
    expr = _TREND_EXPR[metric]
    params: list = [timedelta(seconds=bucket)]
    where = _filters(bus, start, end, params, "bucket")
    sql = f"""
        SELECT time_bucket($1, bucket) AS b, {expr} AS v
        FROM telemetry_1min{where}
        GROUP BY b ORDER BY b
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [TrendPoint(bucket=r["b"], value=_convert_trend(metric, r["v"])) for r in rows]


@router.get("/trend-by-bus", response_model=list[TrendByBusPoint])
async def trend_by_bus(metric: str = Query("speed"), bucket: int = Query(300, gt=0),
                       start: datetime | None = None, end: datetime | None = None,
                       buses: str | None = None) -> list[TrendByBusPoint]:
    # One series per bus for the chosen metric, for overlaying buses on one
    # chart. Groups by (time bucket, bus_id). `buses` is an optional
    # comma-separated allow-list (filtered server-side); omitted = all buses.
    # Reads the continuous aggregate, like /trend.
    if metric not in _TREND_EXPR:
        raise HTTPException(status_code=422, detail=f"unknown metric: {metric}")
    expr = _TREND_EXPR[metric]
    params: list = [timedelta(seconds=bucket)]
    clauses: list[str] = []
    if start:
        params.append(start)
        clauses.append(f"bucket >= ${len(params)}")
    if end:
        params.append(end)
        clauses.append(f"bucket <= ${len(params)}")
    bus_list = [b for b in (buses.split(",") if buses else []) if b]
    if bus_list:
        params.append(bus_list)
        clauses.append(f"bus_id = ANY(${len(params)})")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT time_bucket($1, bucket) AS b, bus_id, {expr} AS v
        FROM telemetry_1min{where}
        GROUP BY b, bus_id ORDER BY b, bus_id
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        TrendByBusPoint(bucket=r["b"], bus_id=r["bus_id"],
                        value=_convert_trend(metric, r["v"]))
        for r in rows
    ]


@router.get("/distribution", response_model=Distribution)
async def distribution(metric: str = Query("speed"), bins: int = Query(20, gt=0, le=200),
                       bus: str | None = None, start: datetime | None = None,
                       end: datetime | None = None) -> Distribution:
    if metric not in _DIST_EXPR:
        raise HTTPException(status_code=422, detail=f"unknown metric: {metric}")
    expr = _DIST_EXPR[metric]
    params: list = []
    where = _filters(bus, start, end, params, "time")
    # value not null guard
    null_guard = (" AND " if where else " WHERE ") + f"{expr} IS NOT NULL"
    base = f"FROM telemetry{where}{null_guard}"

    stats_sql = f"""
        SELECT min({expr}) lo, max({expr}) hi,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY {expr}) q1,
               percentile_cont(0.5)  WITHIN GROUP (ORDER BY {expr}) med,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY {expr}) q3
        {base}
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        s = await conn.fetchrow(stats_sql, *params)
        if not s or s["lo"] is None or s["hi"] is None or s["hi"] == s["lo"]:
            return Distribution(
                min=s["lo"] if s else None, max=s["hi"] if s else None,
                q1=s["q1"] if s else None, median=s["med"] if s else None,
                q3=s["q3"] if s else None,
            )
        lo, hi = s["lo"], s["hi"]
        width = (hi - lo) / bins
        hist_params = params + [lo, width, bins]
        idx = len(hist_params)
        hist_sql = f"""
            SELECT least(floor(({expr} - ${idx-2}) / ${idx-1})::int, ${idx}-1) AS bin,
                   count(*) AS c
            {base}
            GROUP BY bin ORDER BY bin
        """
        hrows = await conn.fetch(hist_sql, *hist_params)

    counts = {r["bin"]: r["c"] for r in hrows}
    out_bins = [
        DistributionBin(lower=lo + i * width, upper=lo + (i + 1) * width,
                        count=counts.get(i, 0))
        for i in range(bins)
    ]
    return Distribution(bins=out_bins, min=lo, max=hi,
                        q1=s["q1"], median=s["med"], q3=s["q3"])
