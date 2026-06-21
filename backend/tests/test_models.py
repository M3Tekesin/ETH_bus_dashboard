from datetime import datetime, timezone

from app.models import TelemetryRecord, TelemetryBatch


def _rec(**kw):
    base = dict(
        time=datetime(2021, 7, 26, 3, 53, 27, tzinfo=timezone.utc),
        bus_id="B183",
        speed_ms=0.0,
        ambient_temp_k=295.15,
        power_w=1594.8,
        traction_force_n=0.0,
        passengers=None,
        bus_route="-",
        stop_name="-",
        door_open=True,
        grid_available=True,
        lat=47.0,
        lon=8.0,
        altitude=400.0,
    )
    base.update(kw)
    return TelemetryRecord(**base)


def test_to_row_order_and_length():
    row = _rec().to_row()
    assert len(row) == 14
    assert row[1] == "B183"
    assert row[2] == 0.0


def test_dash_text_becomes_none():
    rec = _rec(bus_route="-", stop_name="")
    assert rec.bus_route is None
    assert rec.stop_name is None


def test_zero_kelvin_becomes_none():
    rec = _rec(ambient_temp_k=0)
    assert rec.ambient_temp_k is None


def test_nan_speed_becomes_none():
    rec = _rec(speed_ms=float("nan"))
    assert rec.speed_ms is None


def test_batch_parses_list():
    batch = TelemetryBatch(records=[_rec(), _rec(bus_id="B208")])
    assert len(batch.records) == 2
    assert batch.records[1].bus_id == "B208"
