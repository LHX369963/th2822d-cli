"""High-level instrument operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .protocol import (
    Identity,
    Measurement,
    parse_identity,
    parse_measurement,
    parse_number,
    parse_pair,
    parse_tolerance_range,
)
from .transport import SerialTransport


@dataclass(frozen=True)
class Configuration:
    frequency_hz: int
    voltage_v: float
    primary: str
    secondary: str
    equivalent: str
    tolerance_enabled: bool
    tolerance_range: int | None
    recording_enabled: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _frequency_hz(value: str) -> int:
    text = value.strip().upper()
    if text.endswith("KHZ"):
        return int(float(text[:-3]) * 1000)
    if text.endswith("HZ"):
        return int(float(text[:-2]))
    return int(float(text))


def _voltage_v(value: str) -> float:
    text = value.strip().upper()
    return float(text[:-1] if text.endswith("V") else text)


class TH2822D:
    def __init__(self, transport: SerialTransport) -> None:
        self.transport = transport

    def __enter__(self) -> "TH2822D":
        self.transport.open()
        return self

    def close(self) -> None:
        self.transport.close()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def identity(self) -> Identity:
        return parse_identity(self.transport.query("*IDN?"))

    def configuration(self) -> Configuration:
        tolerance = self.transport.query("CALCulate:TOLerance:RANGe?")
        return Configuration(
            frequency_hz=_frequency_hz(self.transport.query("FREQuency?")),
            voltage_v=_voltage_v(self.transport.query("VOLTage?")),
            primary=self.transport.query("FUNCtion:IMPA?").upper(),
            secondary=self.transport.query("FUNCtion:IMPB?").upper(),
            equivalent=self.transport.query("FUNCtion:EQUivalent?").upper(),
            tolerance_enabled=self.transport.query("CALCulate:TOLerance:STATe?").upper() == "ON",
            tolerance_range=parse_tolerance_range(tolerance),
            recording_enabled=self.transport.query("CALCulate:RECording:STATe?").upper() == "ON",
        )

    def measurement(self, primary: str | None = None, secondary: str | None = None) -> Measurement:
        primary = primary or self.transport.query("FUNCtion:IMPA?")
        if primary.upper() == "DCR":
            secondary = "NULL"
        else:
            secondary = secondary or self.transport.query("FUNCtion:IMPB?")
        return parse_measurement(self.transport.query("FETCh?"), primary, secondary)

    def recording_stats(self) -> dict:
        return {
            "enabled": self.transport.query("CALCulate:RECording:STATe?").upper() == "ON",
            "maximum": parse_pair(self.transport.query("CALCulate:RECording:MAXimum?")),
            "minimum": parse_pair(self.transport.query("CALCulate:RECording:MINimum?")),
            "average": parse_pair(self.transport.query("CALCulate:RECording:AVERage?")),
            "present": parse_pair(self.transport.query("CALCulate:RECording:PRESent?")),
        }

    def tolerance_status(self) -> dict:
        nominal = self.transport.query("CALCulate:TOLerance:NOMinal?")
        value = self.transport.query("CALCulate:TOLerance:VALUe?")
        range_value = self.transport.query("CALCulate:TOLerance:RANGe?")
        return {
            "enabled": self.transport.query("CALCulate:TOLerance:STATe?").upper() == "ON",
            "nominal": parse_number(nominal),
            "deviation_percent": parse_number(value),
            "range_percent": parse_tolerance_range(range_value),
        }
