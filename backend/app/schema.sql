CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS telemetry (
    time              timestamptz      NOT NULL,
    bus_id            text             NOT NULL,
    speed_ms          double precision,
    ambient_temp_k    double precision,
    power_w           double precision,
    traction_force_n  double precision,
    passengers        integer,
    bus_route         text,
    stop_name         text,
    door_open         boolean,
    grid_available    boolean,
    lat               double precision,
    lon               double precision,
    altitude          double precision
);

SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS telemetry_bus_time_idx ON telemetry (bus_id, time DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    bus_id,
    avg(speed_ms)        AS avg_speed_ms,
    max(speed_ms)        AS max_speed_ms,
    sum(speed_ms)        AS sum_speed_ms,
    avg(ambient_temp_k)  AS avg_temp_k,
    max(ambient_temp_k)  AS max_temp_k,
    avg(power_w)         AS avg_power_w,
    sum(power_w)         AS sum_power_w,
    avg(passengers)      AS avg_passengers,
    max(passengers)      AS max_passengers,
    count(*)             AS sample_count
FROM telemetry
GROUP BY bucket, bus_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_1min',
    start_offset => NULL,
    end_offset   => NULL,
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);
