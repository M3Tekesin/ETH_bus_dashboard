import math

from app.conversions import (
    clean_float, clean_speed_ms, clean_temp_k, clean_text, clean_int,
    ms_to_kmh, k_to_c, w_to_kwh,
)


def test_clean_float_passes_normal():
    assert clean_float(3.5) == 3.5


def test_clean_speed_ms_clamps_negative_to_zero():
    assert clean_speed_ms(-0.2) == 0.0
    assert clean_speed_ms(0.0) == 0.0
    assert clean_speed_ms(5.0) == 5.0
    assert clean_speed_ms(float("nan")) is None
    assert clean_speed_ms(None) is None


def test_clean_float_nan_to_none():
    assert clean_float(float("nan")) is None
    assert clean_float(float("inf")) is None
    assert clean_float(None) is None


def test_clean_temp_k_zero_to_none():
    assert clean_temp_k(0) is None
    assert clean_temp_k(295.15) == 295.15


def test_clean_text_dash_to_none():
    assert clean_text("-") is None
    assert clean_text("") is None
    assert clean_text("33") == "33"


def test_clean_int_nan_to_none():
    assert clean_int(float("nan")) is None
    assert clean_int(5.0) == 5


def test_ms_to_kmh():
    assert math.isclose(ms_to_kmh(10), 36.0)


def test_k_to_c():
    assert math.isclose(k_to_c(273.15), 0.0)


def test_w_to_kwh_one_hz():
    # 3600 W summed over 3600 one-second samples = 3600 Wh = 3.6 kWh
    assert math.isclose(w_to_kwh(3600 * 3600), 3.6)
