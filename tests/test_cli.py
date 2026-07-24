import json

import pytest

from th2822d_cli import cli
from th2822d_cli.errors import ProtocolError, TransportError


def test_command_catalog_without_hardware(capsys):
    assert cli.main(["commands", "show", "measurement.fetch"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["command"] == "FETCh"
    assert value["kind"] == "query"


def test_protocol_error_is_structured(capsys):
    assert cli.main(["commands", "show", "missing"]) == cli.EXIT_PROTOCOL
    value = json.loads(capsys.readouterr().err)
    assert value["error"] == "protocol"


def test_not_found_is_structured(monkeypatch, capsys):
    monkeypatch.setattr(cli, "serial_ports", lambda: [])
    assert cli.main(["info"]) == cli.EXIT_NOT_FOUND
    value = json.loads(capsys.readouterr().err)
    assert value["error"] == "not_found"


def test_configure_requires_option():
    class Meter:
        pass

    args = cli.parser().parse_args(["configure"])
    with pytest.raises(ProtocolError):
        cli._configure(args, Meter())


class ConfigureTransport:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.writes = []

    def write(self, command):
        self.writes.append(command)

    def query(self, command):
        return self.responses[command]


class ConfigureMeter:
    def __init__(self, responses=None):
        self.transport = ConfigureTransport(responses)


def test_configure_null_secondary_resets_primary():
    args = cli.parser().parse_args(["configure", "--secondary", "NULL"])
    meter = ConfigureMeter({"FUNCtion:IMPA?": "C"})
    changed = cli._configure(args, meter)
    assert meter.transport.writes == ["FUNCtion:IMPA C"]
    assert changed["FUNCtion:IMPB"] == "NULL"


def test_configure_enables_tolerance_before_range():
    args = cli.parser().parse_args([
        "configure", "--tolerance", "ON", "--tolerance-range", "5"
    ])
    meter = ConfigureMeter()
    cli._configure(args, meter)
    assert meter.transport.writes == [
        "CALCulate:TOLerance:STATe ON",
        "CALCulate:TOLerance:RANGe 5",
    ]


def test_configure_range_requires_tolerance():
    args = cli.parser().parse_args([
        "configure", "--frequency", "1000", "--tolerance-range", "5"
    ])
    meter = ConfigureMeter({"CALCulate:TOLerance:STATe?": "OFF"})
    with pytest.raises(ProtocolError, match="requires tolerance mode"):
        cli._configure(args, meter)
    assert meter.transport.writes == []


def test_configure_rejects_dcr_secondary_before_writing():
    args = cli.parser().parse_args([
        "configure", "--primary", "DCR", "--secondary", "ESR"
    ])
    meter = ConfigureMeter()
    with pytest.raises(ProtocolError, match="does not support"):
        cli._configure(args, meter)
    assert meter.transport.writes == []


def test_configure_rejects_secondary_when_current_mode_is_dcr():
    args = cli.parser().parse_args(["configure", "--secondary", "Q"])
    meter = ConfigureMeter({"FUNCtion:IMPA?": "DCR"})
    with pytest.raises(ProtocolError, match="does not support"):
        cli._configure(args, meter)
    assert meter.transport.writes == []


def test_raw_infers_query():
    class Transport:
        def __init__(self):
            self.writes = []

        def query(self, command):
            return "answer"

        def write(self, command):
            self.writes.append(command)

    class Meter:
        transport = Transport()

    assert cli._raw_line(Meter(), "*IDN?")["response"] == "answer"
    assert cli._raw_line(Meter(), "*TRG")["written"]
