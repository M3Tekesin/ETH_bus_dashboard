from __future__ import annotations

import csv
import sys
from pathlib import Path

import httpx

API = "http://localhost:8000/api/telemetry/batch"
CHUNK = 5000

# CSV column -> API field
FIELD_MAP = {
    "time_iso": "time",
    "odometry_vehicleSpeed": "speed_ms",
    "temperature_ambient": "ambient_temp_k",
    "electric_powerDemand": "power_w",
    "traction_tractionForce": "traction_force_n",
    "itcs_numberOfPassengers": "passengers",
    "itcs_busRoute": "bus_route",
    "itcs_stopName": "stop_name",
    "status_doorIsOpen": "door_open",
    "status_gridIsAvailable": "grid_available",
    "gnss_latitude": "lat",
    "gnss_longitude": "lon",
    "gnss_altitude": "altitude",
}
BOOL_FIELDS = {"door_open", "grid_available"}


def bus_id_from_name(path: Path) -> str:
    return path.name.split("_", 1)[0]  # "B183_..." -> "B183"


def to_record(row: dict, bus_id: str) -> dict:
    rec: dict = {"bus_id": bus_id}
    for csv_col, field in FIELD_MAP.items():
        val = row.get(csv_col)
        if field in BOOL_FIELDS:
            rec[field] = None if val in (None, "", "NaN") else bool(float(val))
        else:
            rec[field] = val
    return rec


def load_file(client: httpx.Client, path: Path) -> int:
    bus_id = bus_id_from_name(path)
    total = 0
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        chunk: list[dict] = []
        for row in reader:
            chunk.append(to_record(row, bus_id))
            if len(chunk) >= CHUNK:
                total += _post(client, chunk)
                chunk = []
        if chunk:
            total += _post(client, chunk)
    return total


def _post(client: httpx.Client, chunk: list[dict]) -> int:
    resp = client.post(API, json={"records": chunk}, timeout=120)
    resp.raise_for_status()
    return resp.json()["inserted"]


def main() -> None:
    samples_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    files = sorted(samples_dir.glob("B*_*.csv"))
    if not files:
        print(f"No mission CSVs found in {samples_dir}")
        sys.exit(1)
    with httpx.Client() as client:
        grand = 0
        for path in files:
            n = load_file(client, path)
            grand += n
            print(f"{path.name}: {n} rows")
        print(f"TOTAL inserted: {grand}")


if __name__ == "__main__":
    main()
