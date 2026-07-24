"""PySerial transport and CP210x/TH2822D discovery."""

from __future__ import annotations

import contextlib
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterator

import serial
from serial.tools import list_ports

from .errors import ProtocolError, TransportError, TransportTimeout
from .protocol import Identity, parse_identity


VID = 0x10C4
PID = 0xEA60


@dataclass(frozen=True)
class PortInfo:
    port: str
    vid: int | None
    pid: int | None
    usb_serial: str | None
    manufacturer: str | None
    product: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def serial_ports() -> list[PortInfo]:
    result = []
    for item in list_ports.comports():
        if item.vid == VID and item.pid == PID:
            result.append(PortInfo(
                port=item.device,
                vid=item.vid,
                pid=item.pid,
                usb_serial=item.serial_number,
                manufacturer=item.manufacturer,
                product=item.product,
            ))
    return sorted(result, key=lambda item: item.port)


class SerialTransport:
    def __init__(
        self,
        port: str,
        timeout: float = 2.0,
        command_delay: float = 0.2,
        query_retries: int = 1,
    ) -> None:
        if timeout <= 0:
            raise TransportError("timeout must be positive")
        if command_delay < 0:
            raise TransportError("command delay cannot be negative")
        if query_retries < 0:
            raise TransportError("query retries cannot be negative")
        self.port = port
        self.timeout = timeout
        self.command_delay = command_delay
        self.query_retries = query_retries
        self._serial: serial.Serial | None = None

    def open(self) -> "SerialTransport":
        try:
            self._serial = serial.Serial(
                self.port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                exclusive=True,
            )
            self._serial.reset_input_buffer()
        except (OSError, serial.SerialException) as exc:
            self.close()
            raise TransportError(f"cannot open {self.port}: {exc}") from exc
        return self

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    @property
    def serial(self) -> serial.Serial:
        if self._serial is None:
            raise TransportError("serial session is not open")
        return self._serial

    @staticmethod
    def encode(command: str) -> bytes:
        command = command.strip()
        if not command:
            raise ProtocolError("SCPI command cannot be empty")
        if "\r" in command or "\n" in command:
            raise ProtocolError("SCPI command cannot contain embedded newlines")
        try:
            return (command + "\n").encode("ascii")
        except UnicodeEncodeError as exc:
            raise ProtocolError("SCPI commands must contain ASCII characters only") from exc

    def write(self, command: str) -> None:
        try:
            self.serial.write(self.encode(command))
            self.serial.flush()
            # Firmware 4.5.2307 drops a command received within roughly 100 ms
            # of a setting/action. Queries can proceed directly to their read.
            if self.command_delay and not command.rstrip().endswith("?"):
                time.sleep(self.command_delay)
        except (OSError, serial.SerialException, serial.SerialTimeoutException) as exc:
            raise TransportError(f"serial write failed on {self.port}: {exc}") from exc

    def read_line(self) -> str:
        try:
            response = self.serial.readline()
        except (OSError, serial.SerialException) as exc:
            raise TransportError(f"serial read failed on {self.port}: {exc}") from exc
        if not response:
            raise TransportTimeout(f"timed out waiting for {self.port}")
        try:
            return response.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise ProtocolError(f"instrument returned non-ASCII data: {response!r}") from exc

    def query(self, command: str) -> str:
        for attempt in range(self.query_retries + 1):
            self.write(command)
            try:
                return self.read_line()
            except TransportTimeout:
                if attempt == self.query_retries:
                    raise
                self.serial.reset_input_buffer()
        raise AssertionError("unreachable")

    def __enter__(self) -> "SerialTransport":
        return self.open()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


TransportFactory = Callable[[str, float], SerialTransport]


def choose_port(
    port: str | None,
    timeout: float,
    factory: TransportFactory = SerialTransport,
) -> tuple[str, Identity]:
    candidates = [port] if port else [item.port for item in serial_ports()]
    if not candidates:
        raise TransportError("no CP210x serial device found; use --port to select one explicitly")
    matches: list[tuple[str, Identity]] = []
    errors: list[str] = []
    for candidate in candidates:
        try:
            with factory(candidate, timeout) as transport:
                identity = parse_identity(transport.query("*IDN?"))
                with contextlib.suppress(Exception):
                    transport.write("*GTL")
                matches.append((candidate, identity))
        except (TransportError, ProtocolError) as exc:
            errors.append(f"{candidate}: {exc}")
    if not matches:
        detail = "; ".join(errors)
        raise TransportError(f"no TH2822-series instrument responded ({detail})")
    if len(matches) > 1:
        paths = ", ".join(item[0] for item in matches)
        raise TransportError(f"multiple TH2822-series instruments found ({paths}); use --port")
    return matches[0]


def discover(timeout: float, factory: TransportFactory = SerialTransport) -> list[dict]:
    found = []
    for metadata in serial_ports():
        item = metadata.to_dict()
        try:
            with factory(metadata.port, timeout) as transport:
                item["identity"] = parse_identity(transport.query("*IDN?")).to_dict()
                with contextlib.suppress(Exception):
                    transport.write("*GTL")
        except (TransportError, ProtocolError) as exc:
            item["error"] = str(exc)
        found.append(item)
    return found
