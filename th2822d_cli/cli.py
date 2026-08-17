"""The ``th2822d`` command-line interface."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from . import __version__
from .catalog import COMMANDS, get_command, readback_matches, validate_value
from .errors import ProtocolError, TH2822DError, TransportError
from .instrument import TH2822D
from .transport import SerialTransport, choose_port, discover, serial_ports

EXIT_NOT_FOUND = 3
EXIT_TRANSPORT = 4
EXIT_PROTOCOL = 5


def emit(value: object, stream: TextIO | None = None) -> None:
    print(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        file=stream or sys.stdout,
        flush=True,
    )


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="th2822d", description="Control and log a Tonghui TH2822D LCR meter")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--port", help="serial device; omitted to auto-discover a TH2822-series meter")
    ap.add_argument("--timeout", type=float, default=2.0, help="serial response timeout in seconds")
    ap.add_argument("--stay-remote", action="store_true", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list attached CP210x adapters and probe TH2822 identity")
    sub.add_parser("info", help="show instrument identity")
    sub.add_parser("config", help="query the complete remote configuration")
    def add_measurement_arguments(command):
        command.add_argument("--samples", type=int, default=7)
        command.add_argument("--min-interval", type=int, default=120, metavar="MS")
        command.add_argument("--max-interval", type=int, default=380, metavar="MS")
        command.add_argument("--expect", type=float)
        command.add_argument("--tolerance", type=float, default=5.0, metavar="PERCENT")
        command.add_argument("--json", action="store_true")

    add_measurement_arguments(sub.add_parser("measure", help="sample repeatedly and return one summary"))
    add_measurement_arguments(sub.add_parser("read", help="alias of measure"))

    monitor = sub.add_parser("monitor", help="capture measurements as JSONL, CSV, or text")
    monitor.add_argument("--interval", type=float, default=0.25, help="seconds between reads")
    monitor.add_argument("--count", type=int, default=0, help="stop after N samples; 0 is unlimited")
    monitor.add_argument("--duration", type=float, default=0, help="stop after N seconds; 0 is unlimited")
    monitor.add_argument("--format", choices=("jsonl", "csv", "txt"), default="jsonl")
    monitor.add_argument("--output", type=Path, help="output path; omitted for stdout")

    configure = sub.add_parser("configure", help="set one or more measurement options")
    configure.add_argument("--frequency", choices=("100", "120", "1000", "10000"))
    configure.add_argument("--voltage", choices=("0.3", "0.6", "1"))
    configure.add_argument("--primary", type=str.upper, choices=("L", "C", "R", "Z", "DCR"))
    configure.add_argument("--secondary", type=str.upper, choices=("D", "Q", "THETA", "ESR", "NULL"))
    configure.add_argument("--equivalent", type=str.upper, choices=("SER", "PAL"))
    configure.add_argument("--tolerance", type=str.upper, choices=("ON", "OFF"))
    configure.add_argument("--tolerance-range", choices=("1", "5", "10", "20"))
    configure.add_argument("--recording", type=str.upper, choices=("ON", "OFF"))

    sub.add_parser("recording", help="query instrument min/max/average/present statistics")
    sub.add_parser("tolerance", help="query tolerance nominal, deviation, and range")

    commands = sub.add_parser("commands", help="inspect the manual-derived command catalog")
    commands_sub = commands.add_subparsers(dest="commands_command", required=True)
    commands_list = commands_sub.add_parser("list")
    commands_list.add_argument("--section")
    commands_show = commands_sub.add_parser("show")
    commands_show.add_argument("name")

    get = sub.add_parser("get", help="query one catalog command")
    get.add_argument("name")
    set_command = sub.add_parser("set", help="set one catalog command")
    set_command.add_argument("name")
    set_command.add_argument("value")
    action = sub.add_parser("action", help="invoke one catalog action")
    action.add_argument("name")

    raw = sub.add_parser("raw", help="send one SCPI command")
    raw.add_argument("scpi")
    raw.add_argument("--read", action=argparse.BooleanOptionalAction, default=None,
                     help="read a response; inferred from trailing ? when omitted")

    batch = sub.add_parser("batch", help="run SCPI lines from a file or '-' for stdin")
    batch.add_argument("path", type=Path)
    return ap


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _connect(args: argparse.Namespace) -> tuple[TH2822D, str]:
    if args.port:
        port = args.port
    else:
        candidates = serial_ports()
        if not candidates:
            raise TransportError("no CP210x serial device found; use --port to select one explicitly")
        if len(candidates) == 1:
            port = candidates[0].port
        else:
            port, _ = choose_port(None, args.timeout)
    return TH2822D(SerialTransport(port, args.timeout)), port


def _measure_many(args: argparse.Namespace, meter: TH2822D, port: str) -> None:
    if args.samples <= 0:
        raise ProtocolError("samples must be positive")
    if not 0 <= args.min_interval <= args.max_interval <= 10000:
        raise ProtocolError("measurement intervals require 0 <= min <= max <= 10000 ms")
    if args.tolerance < 0:
        raise ProtocolError("tolerance cannot be negative")
    primary = meter.transport.query("FUNCtion:IMPA?")
    secondary = "NULL" if primary.upper() == "DCR" else meter.transport.query("FUNCtion:IMPB?")
    measurements = []
    for index in range(args.samples):
        measurements.append(meter.measurement(primary, secondary))
        if index + 1 < args.samples:
            time.sleep(random.uniform(args.min_interval, args.max_interval) / 1000)
    valid = [item for item in measurements if item.primary_value is not None and not item.overload]
    if not valid:
        print("warning: no valid measurement", file=sys.stderr)
        print("None")
        return
    values = [float(item.primary_value) for item in valid]
    median, minimum, maximum = statistics.median(values), min(values), max(values)
    warnings = []
    if len(valid) != len(measurements):
        warnings.append("intermittent")
    if maximum - minimum > max(abs(median) * 0.02, 1e-15):
        warnings.append(f"unstable={minimum:.8g}..{maximum:.8g}")
    if args.expect is not None:
        allowed = max(abs(args.expect) * args.tolerance / 100, 1e-15)
        if abs(median - args.expect) > allowed:
            warnings.append(f"expected={args.expect:.8g} got={median:.8g}")
    if warnings:
        print("warning: " + " ".join(warnings), file=sys.stderr)
    if args.json:
        secondary_values = [
            float(item.secondary_value) for item in valid if item.secondary_value is not None
        ]
        emit({
            "primary": valid[-1].primary,
            "value": median,
            "unit": valid[-1].primary_unit,
            "samples": len(valid),
            "min": minimum,
            "max": maximum,
            "secondary": valid[-1].secondary,
            "secondary_value": statistics.median(secondary_values) if secondary_values else None,
            "secondary_unit": valid[-1].secondary_unit,
            "port": port,
        })
    else:
        print(f"{median} {valid[-1].primary_unit} spread={maximum - minimum:.8g}")


def _monitor(args: argparse.Namespace, meter: TH2822D, port: str) -> None:
    if args.interval < 0.05:
        raise ProtocolError("monitor interval must be at least 0.05 seconds")
    if args.count < 0 or args.duration < 0:
        raise ProtocolError("count and duration cannot be negative")
    output = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    fieldnames = [
        "timestamp", "port", "sequence", "primary", "primary_value", "primary_unit",
        "secondary", "secondary_value", "secondary_unit", "tolerance_bin", "overload",
    ]
    writer = (
        csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t" if args.format == "txt" else ",")
        if args.format in {"csv", "txt"}
        else None
    )
    if writer:
        writer.writeheader()
    started = time.monotonic()
    sequence = 0
    primary = meter.transport.query("FUNCtion:IMPA?")
    secondary = "NULL" if primary.upper() == "DCR" else meter.transport.query("FUNCtion:IMPB?")
    try:
        while (not args.count or sequence < args.count) and (
            not args.duration or time.monotonic() - started < args.duration
        ):
            tick = time.monotonic()
            sequence += 1
            record = {"timestamp": _timestamp(), "port": port, "sequence": sequence}
            record |= meter.measurement(primary, secondary).to_dict()
            if writer:
                writer.writerow(record)
                output.flush()
            else:
                emit(record, output)
            delay = args.interval - (time.monotonic() - tick)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        if args.output:
            output.close()


def _verified_set(meter: TH2822D, name: str, value: str, attempts: int = 3) -> str:
    spec = get_command(name)
    normalized = validate_value(spec, value)
    response = ""
    for _ in range(attempts):
        meter.transport.write(f"{spec.command} {normalized}")
        response = meter.transport.query(f"{spec.command}?")
        if readback_matches(spec, normalized, response):
            return response
    raise ProtocolError(
        f"{name} write was not applied after {attempts} attempts "
        f"(requested {normalized!r}, read back {response!r})"
    )


def _reset_secondary(meter: TH2822D, primary: str, attempts: int = 3) -> str:
    response = ""
    for _ in range(attempts):
        meter.transport.write(f"FUNCtion:IMPA {primary}")
        response = meter.transport.query("FUNCtion:IMPB?")
        if response.upper() == "NULL":
            return response
    raise ProtocolError(
        f"secondary reset was not applied after {attempts} attempts (read back {response!r})"
    )


def _configure(args: argparse.Namespace, meter: TH2822D) -> dict:
    requested = (
        args.frequency,
        args.voltage,
        args.primary,
        args.secondary,
        args.equivalent,
        args.tolerance,
        args.tolerance_range,
        args.recording,
    )
    if not any(value is not None for value in requested):
        raise ProtocolError("configure requires at least one option")
    if args.tolerance_range is not None:
        if args.tolerance == "OFF":
            raise ProtocolError("--tolerance-range cannot be combined with --tolerance OFF")
        if args.tolerance is None:
            args.tolerance = "ON"
    if args.primary == "DCR" and args.secondary not in {None, "NULL"}:
        raise ProtocolError("DCR does not support a secondary parameter")
    if (
        args.primary is None
        and args.secondary not in {None, "NULL"}
        and meter.transport.query("FUNCtion:IMPA?").upper() == "DCR"
    ):
        raise ProtocolError("DCR does not support a secondary parameter")

    values = (
        ("function.primary", "FUNCtion:IMPA", args.primary),
        ("function.equivalent", "FUNCtion:EQUivalent", args.equivalent),
        ("frequency.test", "FREQuency", args.frequency),
        ("voltage.level", "VOLTage", args.voltage),
        ("recording.enabled", "CALCulate:RECording:STATe", args.recording),
    )
    changed = {}
    for name, command, value in values:
        if value is not None:
            _verified_set(meter, name, value)
            changed[command] = value
    if args.secondary == "NULL":
        primary = args.primary or meter.transport.query("FUNCtion:IMPA?")
        changed["FUNCtion:IMPB"] = "NULL"
        if primary.upper() != "DCR":
            _reset_secondary(meter, primary)
    elif args.secondary is not None:
        _verified_set(meter, "function.secondary", args.secondary)
        changed["FUNCtion:IMPB"] = args.secondary
    if args.tolerance is not None:
        _verified_set(meter, "tolerance.enabled", args.tolerance)
        changed["CALCulate:TOLerance:STATe"] = args.tolerance
    if args.tolerance_range is not None:
        _verified_set(meter, "tolerance.range", args.tolerance_range)
        changed["CALCulate:TOLerance:RANGe"] = args.tolerance_range
    return changed


def _raw_line(meter: TH2822D, command: str, read: bool | None = None) -> dict:
    should_read = command.rstrip().endswith("?") if read is None else read
    if should_read:
        return {"command": command, "response": meter.transport.query(command)}
    meter.transport.write(command)
    return {"command": command, "written": True}


def _batch(args: argparse.Namespace, meter: TH2822D) -> list[dict]:
    lines = sys.stdin if str(args.path) == "-" else args.path.open(encoding="utf-8")
    results = []
    try:
        for number, line in enumerate(lines, 1):
            command = line.strip()
            if not command or command.startswith("#"):
                continue
            results.append({"line": number} | _raw_line(meter, command))
    finally:
        if lines is not sys.stdin:
            lines.close()
    return results


def run(args: argparse.Namespace) -> None:
    if args.command == "list":
        emit({"devices": discover(args.timeout)})
        return
    if args.command == "commands":
        if args.commands_command == "show":
            emit(get_command(args.name).to_dict())
        else:
            specs = [item for item in COMMANDS if not args.section or item.section == args.section]
            emit({"commands": [item.to_dict() for item in specs]})
        return
    meter, port = _connect(args)
    with meter:
        if args.command == "info":
            emit({"port": port} | meter.identity().to_dict())
        elif args.command == "config":
            emit({"port": port} | meter.configuration().to_dict())
        elif args.command in {"read", "measure"}:
            _measure_many(args, meter, port)
        elif args.command == "monitor":
            _monitor(args, meter, port)
        elif args.command == "configure":
            _configure(args, meter)
        elif args.command == "recording":
            emit({"port": port} | meter.recording_stats())
        elif args.command == "tolerance":
            emit({"port": port} | meter.tolerance_status())
        elif args.command == "get":
            spec = get_command(args.name)
            if not spec.can_query:
                raise ProtocolError(f"{spec.name} is not queryable")
            emit({"port": port, "name": spec.name, "response": meter.transport.query(spec.command + "?")})
        elif args.command == "set":
            spec = get_command(args.name)
            if spec.kind == "action" or not spec.can_write:
                raise ProtocolError(f"{spec.name} does not accept a value")
            value = validate_value(spec, args.value)
            _verified_set(meter, spec.name, value)
        elif args.command == "action":
            spec = get_command(args.name)
            if spec.kind != "action":
                raise ProtocolError(f"{spec.name} is not an action")
            meter.transport.write(spec.command)
        elif args.command == "raw":
            emit({"port": port} | _raw_line(meter, args.scpi, args.read))
        elif args.command == "batch":
            emit({"port": port, "results": _batch(args, meter)})


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        run(args)
        return 0
    except TransportError as exc:
        kind = "not_found" if "no TH2822" in str(exc) or "no CP210x" in str(exc) else "transport"
        emit({"error": kind, "message": str(exc)}, sys.stderr)
        return EXIT_NOT_FOUND if kind == "not_found" else EXIT_TRANSPORT
    except (ProtocolError, ValueError) as exc:
        emit({"error": "protocol", "message": str(exc)}, sys.stderr)
        return EXIT_PROTOCOL
    except (OSError, TH2822DError) as exc:
        emit({"error": "transport", "message": str(exc)}, sys.stderr)
        return EXIT_TRANSPORT


if __name__ == "__main__":
    raise SystemExit(main())
