# Telemetry Analytics Dashboard

A web dashboard for exploring time-resolved telemetry from the
[ZTBus](https://www.research-collection.ethz.ch/handle/20.500.11850/626723)
city-bus dataset (ETH Zürich). It exposes a batch ingestion API, stores data in
a TimescaleDB hypertable, and serves filterable KPIs and charts.

## Stack

FastAPI + asyncpg + TimescaleDB (backend), React + Vite + Recharts (frontend).

## Features

- **Batch ingestion API** for telemetry records, with input validation and
  normalisation (NaN/sentinels → NULL, negative odometer noise clamped).
- **KPIs** — average speed, max temperature, total (net) energy, distance —
  that recompute under the active filters.
- **Filtering** by vehicle and UTC time range, shown as removable chips. The
  dashboard opens on one bus's most recent day to stay fast at scale.
- **Trend chart** with a metric selector (speed / temperature / power);
  negative power is coloured separately to highlight regenerative braking.
- **Multi-bus comparison** — overlay selected buses on one time-aligned chart;
  gaps between missions are rendered as breaks, not interpolated.
- **Distribution chart** — histogram plus min/Q1/median/Q3/max for the chosen
  metric under the current filters.

## Run Order

Follow this exact sequence — tests truncate the `telemetry` table, so always
run tests before loading data.

1. **Database**
   ```bash
   docker compose -f docker-compose.db.yml up -d
   ```

2. **Backend** (applies schema on startup)
   ```bash
   cd backend && uv sync && uv run uvicorn app.main:app --port 8000
   ```

3. **Load samples**
   ```bash
   cd backend && uv run python scripts/load_samples.py <path-to>/ZTBus_samples
   ```
   Then refresh the continuous aggregate rollup:
   ```bash
   docker compose -f docker-compose.db.yml exec -T db psql -U postgres -d telemetry \
     -c "CALL refresh_continuous_aggregate('telemetry_1min', NULL, NULL);"
   ```

4. **Frontend**
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Opens at http://localhost:5173

## Tests

```bash
cd backend && uv run pytest
```

> **Data caveat:** The test suite truncates the shared `telemetry` table via
> fixture teardown. Always run tests **before** loading sample data, or point
> the tests at a separate database. Reload sample data (step 3 above) after
> running tests.

## API

All query endpoints accept optional `bus`, `start`, and `end` (UTC) filters.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/telemetry/batch` | Ingest a batch of telemetry records |
| `GET`  | `/api/buses` | List vehicle IDs |
| `GET`  | `/api/time-range` | Min/max timestamp of available data |
| `GET`  | `/api/kpis` | Aggregate KPIs |
| `GET`  | `/api/trend` | Time series for one metric |
| `GET`  | `/api/trend-by-bus` | One series per bus (`buses` allow-list) |
| `GET`  | `/api/distribution` | Histogram + quartiles for one metric |

## Data model

Raw per-second signals stored in source units in the `telemetry` hypertable;
a `telemetry_1min` continuous aggregate pre-rolls per-minute stats. Conversions
(m/s→km/h, K→°C, W→kWh) happen at the API edge.

## Scaling to millions of records

- TimescaleDB **hypertable** time-partitioning prunes chunks on time filters.
- **Continuous aggregate** (`telemetry_1min`) serves KPIs and the trend chart
  from pre-rolled minute buckets instead of scanning raw rows.
- Server-side **`time_bucket` downsampling** bounds chart payload size.
- Index on `(bus_id, time)` for fast vehicle + time filtering.
- Next steps: native compression of old chunks, retention policies, extra
  rollup resolutions (hourly/daily).

## Deferred bonuses

Authentication, live (WebSocket/SSE) view, and full app containerization are
designed for but not implemented in this iteration.
