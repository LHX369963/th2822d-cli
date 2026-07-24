import json

import pytest

from th2822d_cli import cli
from th2822d_cli.errors import ProtocolError, TransportError
from th2822d_cli.instrument import Configuration


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


def test_go_local_action_is_sent(monkeypatch, capsys):
    class Transport:
        def __init__(self):
            self.writes = []

        def write(self, command):
            self.writes.append(command)

    class Meter:
        def __init__(self):
            self.transport = Transport()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def identity(self):
            return None

    meter = Meter()
    monkeypatch.setattr(cli, "_connect", lambda args: (meter, "/dev/fake"))
    assert cli.main(["action", "general.go-local"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["name"] == "general.go-local"
    assert meter.transport.writes == ["*GTL"]


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
        value = self.responses[command]
        if isinstance(value, list):
            return value.pop(0)
        return value


class ConfigureMeter:
    def __init__(self, responses=None, configuration=None):
        self.transport = ConfigureTransport(responses)
        self._configuration = configuration

    def configuration(self):
        return self._configuration or Configuration(
            frequency_hz=100,
            voltage_v=0.3,
            primary="C",
            secondary="NULL",
            equivalent="PAL",
            tolerance_enabled=False,
            tolerance_range=None,
            recording_enabled=False,
        )


def test_configure_null_secondary_resets_primary():
    args = cli.parser().parse_args(["configure", "--secondary", "NULL"])
    meter = ConfigureMeter({"FUNCtion:IMPA?": "C", "FUNCtion:IMPB?": ["NULL", "NULL"]})
    changed = cli._configure(args, meter)
    assert meter.transport.writes == ["FUNCtion:IMPA C"]
    assert changed["FUNCtion:IMPB"] == "NULL"


def test_configure_dcr_null_secondary_never_queries_secondary():
    args = cli.parser().parse_args([
        "configure", "--primary", "DCR", "--secondary", "NULL"
    ])
    meter = ConfigureMeter({"FUNCtion:IMPA?": ["DCR", "DCR"]})
    changed = cli._configure(args, meter)
    assert meter.transport.writes == ["FUNCtion:IMPA DCR"]
    assert changed["FUNCtion:IMPB"] == "NULL"


def test_configure_enables_tolerance_before_range():
    args = cli.parser().parse_args([
        "configure", "--tolerance", "ON", "--tolerance-range", "5"
    ])
    meter = ConfigureMeter({
        "CALCulate:TOLerance:STATe?": ["ON", "ON"],
        "CALCulate:TOLerance:RANGe?": ["BIN2", "BIN2"],
    })
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


def test_verified_set_retries_dropped_write():
    meter = ConfigureMeter({"FREQuency?": ["100Hz", "1kHz"]})
    response = cli._verified_set(meter, "frequency.test", "1000")
    assert response == "1kHz"
    assert meter.transport.writes == ["FREQuency 1000", "FREQuency 1000"]


def test_configure_rolls_back_after_failed_write(monkeypatch):
    args = cli.parser().parse_args(["configure", "--frequency", "1000"])
    meter = ConfigureMeter({"FREQuency?": ["100Hz", "100Hz", "100Hz"]})
    restored = []
    monkeypatch.setattr(cli, "_restore_configuration", lambda current, original: restored.append(original))
    with pytest.raises(ProtocolError, match="rolled back"):
        cli._configure(args, meter)
    assert len(restored) == 1


def test_configure_preserves_unspecified_secondary():
    args = cli.parser().parse_args(["configure", "--frequency", "1000"])
    original = Configuration(
        frequency_hz=100,
        voltage_v=0.3,
        primary="Z",
        secondary="THETA",
        equivalent="SER",
        tolerance_enabled=False,
        tolerance_range=None,
        recording_enabled=False,
    )
    meter = ConfigureMeter(
        {"FREQuency?": ["1kHz", "1kHz"], "FUNCtion:IMPB?": ["THETA", "THETA"]},
        configuration=original,
    )
    cli._configure(args, meter)
    assert meter.transport.writes == ["FREQuency 1000", "FUNCtion:IMPB THETA"]


def test_final_configuration_mismatch_rolls_back(monkeypatch):
    args = cli.parser().parse_args(["configure", "--primary", "Z", "--frequency", "100"])
    meter = ConfigureMeter({
        "FUNCtion:IMPA?": ["Z", "L"],
        "FREQuency?": ["100Hz", "100Hz"],
    })
    restored = []
    monkeypatch.setattr(cli, "_restore_configuration", lambda current, original: restored.append(original))
    with pytest.raises(ProtocolError, match="final configuration mismatch"):
        cli._configure(args, meter)
    assert len(restored) == 1


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
