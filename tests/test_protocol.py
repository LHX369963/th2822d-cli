import pytest

from th2822d_cli.errors import ProtocolError
from th2822d_cli.protocol import (
    parse_identity,
    parse_measurement,
    parse_number,
    parse_pair,
    parse_tolerance_range,
)


def test_parse_identity():
    value = parse_identity("TH2822D Handheld LCR Meter,VER4.5.2307,SNQ48C240168")
    assert value.model == "TH2822D Handheld LCR Meter"
    assert value.firmware == "VER4.5.2307"
    assert value.serial == "SNQ48C240168"


def test_reject_other_identity():
    with pytest.raises(ProtocolError):
        parse_identity("Other,1.0,123")


def test_parse_capacitance_measurement():
    value = parse_measurement("+6.71462e-04,+2.50000e-02,N", "C", "D")
    assert value.primary_value == pytest.approx(0.000671462)
    assert value.primary_unit == "F"
    assert value.secondary == "D"
    assert value.secondary_value == pytest.approx(0.025)
    assert value.secondary_unit is None
    assert value.tolerance_bin == "N"
    assert not value.overload


def test_parse_dcr_measurement():
    value = parse_measurement("+1.23456e+02,2", "DCR", "NULL")
    assert value.primary_value == pytest.approx(123.456)
    assert value.primary_unit == "ohm"
    assert value.secondary is None
    assert value.tolerance_bin == "2"


def test_parse_overload_and_pair():
    value = parse_measurement("-----,-----,N", "L", "Q")
    assert value.overload
    assert value.primary_value is None
    assert parse_pair("-----,+1.2E+00") == {"primary_value": None, "secondary_value": 1.2}
    assert parse_pair("-----") == {"primary_value": None, "secondary_value": None}
    assert parse_number("----") is None


def test_null_secondary_discards_placeholder():
    value = parse_measurement("+6.8e-4,+0.0e+0,N", "C", "NULL")
    assert value.secondary is None
    assert value.secondary_value is None


def test_reject_bad_fetch_shape_and_number():
    with pytest.raises(ProtocolError):
        parse_measurement("1,2", "C", "D")
    with pytest.raises(ProtocolError):
        parse_number("not-a-number")
    with pytest.raises(ProtocolError):
        parse_number("nan")


def test_tolerance_bin_mapping():
    assert [parse_tolerance_range(f"BIN{x}") for x in range(1, 5)] == [1, 5, 10, 20]
    assert parse_tolerance_range("----") is None
    with pytest.raises(ProtocolError):
        parse_tolerance_range("BIN5")
