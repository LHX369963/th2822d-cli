"""Response parsing and typed TH2822D state."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .errors import ProtocolError


PRIMARY_UNITS = {"L": "H", "C": "F", "R": "ohm", "Z": "ohm", "DCR": "ohm"}
SECONDARY_UNITS = {"D": None, "Q": None, "THETA": "deg", "ESR": "ohm", "NULL": None}
OVERLOAD_MARKERS = {"-----", "----", ""}
TOLERANCE_BIN_PERCENT = {"BIN1": 1, "BIN2": 5, "BIN3": 10, "BIN4": 20}


def parse_number(value: str) -> float | None:
    text = value.strip()
    if text in OVERLOAD_MARKERS:
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise ProtocolError(f"invalid numeric response {value!r}") from exc
    if not math.isfinite(number):
        raise ProtocolError(f"non-finite numeric response {value!r}")
    return number


@dataclass(frozen=True)
class Identity:
    model: str
    firmware: str
    serial: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_identity(response: str) -> Identity:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) != 3 or not parts[0].upper().startswith("TH2822"):
        raise ProtocolError(f"unexpected identity response {response!r}")
    return Identity(*parts)


@dataclass(frozen=True)
class Measurement:
    primary: str
    primary_value: float | None
    primary_unit: str
    secondary: str | None
    secondary_value: float | None
    secondary_unit: str | None
    tolerance_bin: str
    overload: bool

    def to_dict(self) -> dict:
        return asdict(self)


def parse_measurement(response: str, primary: str, secondary: str) -> Measurement:
    primary = primary.strip().upper()
    secondary = secondary.strip().upper()
    if primary not in PRIMARY_UNITS:
        raise ProtocolError(f"unknown primary parameter {primary!r}")
    parts = [part.strip() for part in response.split(",")]
    expected = 2 if primary == "DCR" else 3
    if len(parts) != expected:
        raise ProtocolError(f"expected {expected} fetch fields, received {response!r}")
    primary_value = parse_number(parts[0])
    if primary == "DCR":
        secondary_name = None
        secondary_value = None
        tolerance_bin = parts[1]
    else:
        if secondary not in SECONDARY_UNITS:
            raise ProtocolError(f"unknown secondary parameter {secondary!r}")
        secondary_name = None if secondary == "NULL" else secondary
        secondary_value = None if secondary == "NULL" else parse_number(parts[1])
        tolerance_bin = parts[2]
    return Measurement(
        primary=primary,
        primary_value=primary_value,
        primary_unit=PRIMARY_UNITS[primary],
        secondary=secondary_name,
        secondary_value=secondary_value,
        secondary_unit=SECONDARY_UNITS.get(secondary),
        tolerance_bin=tolerance_bin,
        overload=primary_value is None,
    )


def parse_pair(response: str) -> dict:
    parts = [part.strip() for part in response.split(",")]
    if len(parts) == 1 and parts[0] in OVERLOAD_MARKERS:
        return {"primary_value": None, "secondary_value": None}
    if len(parts) != 2:
        raise ProtocolError(f"expected two values, received {response!r}")
    return {"primary_value": parse_number(parts[0]), "secondary_value": parse_number(parts[1])}


def parse_tolerance_range(response: str) -> int | None:
    value = response.strip().upper()
    if value in OVERLOAD_MARKERS:
        return None
    try:
        return TOLERANCE_BIN_PERCENT[value]
    except KeyError as exc:
        raise ProtocolError(f"invalid tolerance range response {response!r}") from exc
