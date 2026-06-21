from __future__ import annotations

import math


def clean_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def clean_speed_ms(v) -> float | None:
    # The odometry speed sensor jitters slightly below zero at standstill;
    # those tiny negatives are noise, not reverse motion. Clamp them to 0.
    f = clean_float(v)
    if f is None:
        return None
    return 0.0 if f < 0 else f


def clean_temp_k(v) -> float | None:
    f = clean_float(v)
    if f is None or f <= 0:
        return None
    return f


def clean_text(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s == "-":
        return None
    return s


def clean_int(v) -> int | None:
    f = clean_float(v)
    if f is None:
        return None
    return int(f)


def ms_to_kmh(v: float) -> float:
    return v * 3.6


def k_to_c(v: float) -> float:
    return v - 273.15


def w_to_kwh(total_w: float, seconds: float = 1.0) -> float:
    # total_w is the SUM of wattage samples; at `seconds` spacing each sample
    # represents total_w * seconds joules. Wh = joules / 3600; kWh = / 1000.
    return total_w * seconds / 3600.0 / 1000.0
