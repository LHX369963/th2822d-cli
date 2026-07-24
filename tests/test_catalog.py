import pytest

from th2822d_cli.catalog import COMMANDS, get_command, readback_matches, validate_value
from th2822d_cli.errors import ProtocolError


def test_catalog_names_are_unique_and_complete():
    names = [item.name for item in COMMANDS]
    assert len(names) == len(set(names)) == 19
    assert {item.section for item in COMMANDS} == {
        "general", "measurement", "function", "tolerance", "recording"
    }


def test_command_capabilities():
    assert get_command("measurement.fetch").can_query
    assert not get_command("measurement.fetch").can_write
    assert get_command("frequency.test").can_query
    assert get_command("frequency.test").can_write
    assert get_command("general.go-local").kind == "action"


def test_value_validation():
    assert validate_value(get_command("function.primary"), "dcr") == "DCR"
    assert validate_value(get_command("function.equivalent"), "parallel") == "PARALLEL"
    with pytest.raises(ProtocolError):
        validate_value(get_command("voltage.level"), "5")
    with pytest.raises(ProtocolError):
        get_command("missing")


def test_readback_matching():
    assert readback_matches(get_command("frequency.test"), "1000", "1kHz")
    assert readback_matches(get_command("voltage.level"), "1", "1V")
    assert readback_matches(get_command("function.equivalent"), "parallel", "PAL")
    assert readback_matches(get_command("tolerance.range"), "5", "BIN2")
    assert not readback_matches(get_command("tolerance.range"), "5", "BIN3")
