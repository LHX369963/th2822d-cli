"""The complete SCPI command surface documented by the TH2822D manual."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import ProtocolError


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: str
    kind: str
    section: str
    parameters: str = ""
    description: str = ""
    choices: tuple[str, ...] = ()

    @property
    def can_query(self) -> bool:
        return self.kind in {"query", "query-set"}

    @property
    def can_write(self) -> bool:
        return self.kind in {"set", "action", "query-set"}

    def to_dict(self) -> dict:
        value = asdict(self)
        value["choices"] = list(self.choices)
        return value


def _s(
    name: str,
    command: str,
    kind: str,
    section: str,
    parameters: str = "",
    description: str = "",
    choices: tuple[str, ...] = (),
) -> CommandSpec:
    return CommandSpec(name, command, kind, section, parameters, description, choices)


COMMANDS: tuple[CommandSpec, ...] = (
    _s("general.idn", "*IDN", "query", "general", description="Instrument model, firmware, and serial"),
    _s("general.local-lock", "*LLO", "action", "general", description="Lock all front-panel keys except power"),
    _s("general.go-local", "*GTL", "action", "general", description="Return control to the front panel"),
    _s("general.trigger", "*TRG", "action", "general", description="Request a measurement trigger"),
    _s(
        "frequency.test", "FREQuency", "query-set", "measurement", "100|120|1000|10000",
        "AC test frequency in hertz", ("100", "120", "1000", "10000"),
    ),
    _s(
        "voltage.level", "VOLTage", "query-set", "measurement", "0.3|0.6|1",
        "AC test level in volts", ("0.3", "0.6", "1"),
    ),
    _s(
        "function.primary", "FUNCtion:IMPA", "query-set", "function", "L|C|R|Z|DCR",
        "Primary measurement parameter", ("L", "C", "R", "Z", "DCR"),
    ),
    _s(
        "function.secondary", "FUNCtion:IMPB", "query-set", "function", "D|Q|THETA|ESR",
        "Secondary measurement parameter; query may return NULL", ("D", "Q", "THETA", "ESR"),
    ),
    _s(
        "function.equivalent", "FUNCtion:EQUivalent", "query-set", "function", "SERies|PAL",
        "Series or parallel equivalent circuit", ("SER", "SERIES", "PAL", "PARALLEL"),
    ),
    _s(
        "tolerance.enabled", "CALCulate:TOLerance:STATe", "query-set", "tolerance", "ON|OFF",
        "Tolerance comparison mode", ("ON", "OFF"),
    ),
    _s("tolerance.nominal", "CALCulate:TOLerance:NOMinal", "query", "tolerance",
       description="Captured nominal primary value"),
    _s("tolerance.value", "CALCulate:TOLerance:VALUe", "query", "tolerance",
       description="Current deviation from nominal in percent"),
    _s(
        "tolerance.range", "CALCulate:TOLerance:RANGe", "query-set", "tolerance", "1|5|10|20",
        "Tolerance limit in percent", ("1", "5", "10", "20"),
    ),
    _s(
        "recording.enabled", "CALCulate:RECording:STATe", "query-set", "recording", "ON|OFF",
        "Instrument-side min/max/average recording", ("ON", "OFF"),
    ),
    _s("recording.maximum", "CALCulate:RECording:MAXimum", "query", "recording",
       description="Recorded maximum primary and secondary"),
    _s("recording.minimum", "CALCulate:RECording:MINimum", "query", "recording",
       description="Recorded minimum primary and secondary"),
    _s("recording.average", "CALCulate:RECording:AVERage", "query", "recording",
       description="Recorded average primary and secondary"),
    _s("recording.present", "CALCulate:RECording:PRESent", "query", "recording",
       description="Present primary and secondary during recording"),
    _s("measurement.fetch", "FETCh", "query", "measurement",
       description="Primary value, secondary value, and tolerance bin"),
)

COMMAND_BY_NAME = {spec.name: spec for spec in COMMANDS}


def get_command(name: str) -> CommandSpec:
    try:
        return COMMAND_BY_NAME[name]
    except KeyError as exc:
        raise ProtocolError(f"unknown command {name!r}; use 'th2822d commands list'") from exc


def validate_value(spec: CommandSpec, value: str) -> str:
    normalized = value.strip().upper()
    if spec.choices and normalized not in spec.choices:
        allowed = ", ".join(spec.choices)
        raise ProtocolError(f"{spec.name} expects one of: {allowed}")
    return normalized


def readback_matches(spec: CommandSpec, requested: str, response: str) -> bool:
    requested = requested.strip().upper()
    response = response.strip().upper()
    if spec.name == "frequency.test":
        expected = {"100": "100HZ", "120": "120HZ", "1000": "1KHZ", "10000": "10KHZ"}
        return response == expected.get(requested)
    if spec.name == "voltage.level":
        expected = {"0.3": "0.3V", "0.6": "0.6V", "1": "1V"}
        return response == expected.get(requested)
    if spec.name == "function.equivalent":
        expected = {"SER": "SER", "SERIES": "SER", "PAL": "PAL", "PARALLEL": "PAL"}
        return response == expected.get(requested)
    if spec.name == "tolerance.range":
        expected = {"1": "BIN1", "5": "BIN2", "10": "BIN3", "20": "BIN4"}
        return response == expected.get(requested)
    return response == requested
