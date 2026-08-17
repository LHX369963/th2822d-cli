#!/usr/bin/env python3
"""Exercise every documented TH2822D command across its valid parameter space."""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from th2822d_cli.catalog import get_command, readback_matches
from th2822d_cli.errors import ProtocolError, TransportError
from th2822d_cli.instrument import TH2822D, Configuration
from th2822d_cli.protocol import (
    parse_identity,
    parse_measurement,
    parse_number,
    parse_pair,
    parse_tolerance_range,
)
from th2822d_cli.transport import SerialTransport


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Runner:
    def __init__(self, meter: TH2822D, trace_path: Path) -> None:
        self.meter = meter
        self.trace = trace_path.open("w", encoding="utf-8")
        self.sequence = 0
        self.checks = 0

    def event(self, event: str, **details) -> None:
        self.sequence += 1
        record = {"sequence": self.sequence, "timestamp": now(), "event": event} | details
        self.trace.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
        self.trace.flush()

    def close(self) -> None:
        self.trace.close()

    def write(self, command: str) -> None:
        self.event("send", command=command, expects_response=False)
        try:
            self.meter.transport.write(command)
        except Exception as exc:
            self.event("error", command=command, error=type(exc).__name__, message=str(exc))
            raise
        self.event("written", command=command)

    def query(self, command: str) -> str:
        self.event("send", command=command, expects_response=True)
        try:
            response = self.meter.transport.query(command)
        except Exception as exc:
            self.event("error", command=command, error=type(exc).__name__, message=str(exc))
            raise
        self.event("response", command=command, response=response)
        return response

    def check(self, name: str, passed: bool, **details) -> None:
        self.checks += 1
        self.event("check", name=name, passed=bool(passed), **details)
        if not passed:
            raise ProtocolError(f"check failed: {name} ({details})")

    def set_query(self, name: str, value: str) -> str:
        spec = get_command(name)
        self.write(f"{spec.command} {value}")
        response = self.query(f"{spec.command}?")
        self.check(
            f"{name}={value}",
            readback_matches(spec, value, response),
            requested=value,
            response=response,
        )
        return response

    def verify(self, name: str, value: str) -> str:
        spec = get_command(name)
        response = self.query(f"{spec.command}?")
        self.check(
            f"final {name}={value}",
            readback_matches(spec, value, response),
            requested=value,
            response=response,
        )
        return response

    def snapshot(self) -> Configuration:
        primary = self.query("FUNCtion:IMPA?").upper()
        if primary == "DCR":
            return Configuration(None, None, primary, "NULL", None, None, None, None)
        tolerance = self.query("CALCulate:TOLerance:RANGe?")
        return Configuration(
            frequency_hz=int(float(self.query("FREQuency?").upper().replace("KHZ", "000").replace("HZ", ""))),
            voltage_v=float(self.query("VOLTage?").upper().removesuffix("V")),
            primary=primary,
            secondary=self.query("FUNCtion:IMPB?").upper(),
            equivalent=self.query("FUNCtion:EQUivalent?").upper(),
            tolerance_enabled=self.query("CALCulate:TOLerance:STATe?").upper() == "ON",
            tolerance_range=parse_tolerance_range(tolerance),
            recording_enabled=self.query("CALCulate:RECording:STATe?").upper() == "ON",
        )

    def restore(self, original: Configuration) -> None:
        self.event("phase", name="restore")
        if original.primary == "DCR":
            self.set_query("function.primary", "DCR")
            return
        self.set_query("function.primary", original.primary)
        self.set_query("function.equivalent", str(original.equivalent))
        self.set_query("frequency.test", str(original.frequency_hz))
        self.set_query("voltage.level", f"{original.voltage_v:g}")
        if original.secondary == "NULL":
            self.write(f"FUNCtion:IMPA {original.primary}")
            response = self.query("FUNCtion:IMPB?")
            self.check("restore secondary NULL", response.upper() == "NULL", response=response)
        else:
            self.set_query("function.secondary", original.secondary)
        self.set_query("tolerance.enabled", "ON" if original.tolerance_enabled else "OFF")
        if original.tolerance_enabled and original.tolerance_range is not None:
            self.set_query("tolerance.range", str(original.tolerance_range))
        self.set_query("recording.enabled", "ON" if original.recording_enabled else "OFF")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", required=True)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--output-dir", type=Path, default=Path("validation/exhaustive"))
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "trace.jsonl"
    measurements_path = args.output_dir / "measurements.csv"
    summary_path = args.output_dir / "summary.json"
    started = time.monotonic()
    transport_failed = False
    error: dict | None = None
    combinations = 0
    original: Configuration | None = None
    restored_configuration: Configuration | None = None

    with TH2822D(SerialTransport(args.port, args.timeout, query_retries=0)) as meter:
        runner = Runner(meter, trace_path)
        try:
            runner.event("phase", name="initial")
            identity = parse_identity(runner.query("*IDN?"))
            runner.check("identity", identity.model.startswith("TH2822D"), identity=identity.to_dict())
            original = runner.snapshot()
            runner.event("snapshot", configuration=asdict(original))

            with measurements_path.open("w", newline="", encoding="utf-8") as output:
                fieldnames = [
                    "primary", "secondary", "equivalent", "frequency_hz", "voltage_v",
                    "primary_value", "primary_unit", "secondary_value", "secondary_unit",
                    "tolerance_bin", "overload", "response",
                ]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                runner.event("phase", name="ac_parameter_space")
                for primary in ("L", "C", "R", "Z"):
                    runner.set_query("function.primary", primary)
                    for secondary in ("D", "Q", "THETA", "ESR", "NULL"):
                        if secondary == "NULL":
                            runner.write(f"FUNCtion:IMPA {primary}")
                            response = runner.query("FUNCtion:IMPB?")
                            runner.check(
                                f"{primary} secondary NULL",
                                response.upper() == "NULL",
                                response=response,
                            )
                        for equivalent in ("SER", "PAL"):
                            runner.set_query("function.equivalent", equivalent)
                            for frequency in ("100", "120", "1000", "10000"):
                                runner.set_query("frequency.test", frequency)
                                for voltage in ("0.3", "0.6", "1"):
                                    runner.set_query("voltage.level", voltage)
                                    if secondary != "NULL":
                                        runner.set_query("function.secondary", secondary)
                                    runner.verify("function.primary", primary)
                                    runner.verify("function.equivalent", equivalent)
                                    runner.verify("frequency.test", frequency)
                                    runner.verify("voltage.level", voltage)
                                    runner.verify("function.secondary", secondary)
                                    response = runner.query("FETCh?")
                                    measurement = parse_measurement(response, primary, secondary)
                                    runner.check(
                                        "measurement shape",
                                        measurement.primary == primary
                                        and measurement.secondary == (
                                            None if secondary == "NULL" else secondary
                                        ),
                                        primary=primary,
                                        secondary=secondary,
                                        response=response,
                                    )
                                    writer.writerow({
                                        **measurement.to_dict(),
                                        "primary": primary,
                                        "secondary": secondary,
                                        "equivalent": equivalent,
                                        "frequency_hz": frequency,
                                        "voltage_v": voltage,
                                        "response": response,
                                    })
                                    output.flush()
                                    combinations += 1

            runner.event("phase", name="dcr")
            runner.set_query("function.primary", "DCR")
            for sample in range(10):
                response = runner.query("FETCh?")
                measurement = parse_measurement(response, "DCR", "NULL")
                runner.check(
                    f"DCR fetch {sample + 1}",
                    measurement.primary == "DCR" and measurement.secondary is None,
                    response=response,
                )

            runner.event("phase", name="tolerance")
            runner.set_query("function.primary", "C")
            runner.set_query("function.secondary", "ESR")
            runner.set_query("tolerance.enabled", "ON")
            for tolerance_range in ("1", "5", "10", "20"):
                runner.set_query("tolerance.range", tolerance_range)
                nominal = parse_number(runner.query("CALCulate:TOLerance:NOMinal?"))
                deviation = parse_number(runner.query("CALCulate:TOLerance:VALUe?"))
                runner.check(
                    f"tolerance values {tolerance_range}",
                    nominal is not None and deviation is not None,
                    nominal=nominal,
                    deviation=deviation,
                )
            runner.set_query("tolerance.enabled", "OFF")

            runner.event("phase", name="recording")
            runner.set_query("recording.enabled", "ON")
            time.sleep(2.2)
            for name, command in (
                ("maximum", "CALCulate:RECording:MAXimum?"),
                ("minimum", "CALCulate:RECording:MINimum?"),
                ("average", "CALCulate:RECording:AVERage?"),
                ("present", "CALCulate:RECording:PRESent?"),
            ):
                response = runner.query(command)
                parsed = parse_pair(response)
                passed = response == "-----" if name == "present" else parsed["primary_value"] is not None
                runner.check(f"recording {name}", passed, response=response, parsed=parsed)
            runner.set_query("recording.enabled", "OFF")

            runner.event("phase", name="actions")
            runner.write("*TRG")
            runner.check("trigger fetch", bool(runner.query("FETCh?")))
            runner.write("*LLO")
            runner.write("*GTL")
            restored_identity = parse_identity(runner.query("*IDN?"))
            runner.check(
                "local lock and restore",
                restored_identity.model.startswith("TH2822D"),
                identity=restored_identity.to_dict(),
            )
        except TransportError as exc:
            transport_failed = True
            error = {"type": type(exc).__name__, "message": str(exc)}
            runner.event("aborted", reason="transport", **error)
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            runner.event("aborted", reason="protocol", **error)
        finally:
            if not transport_failed and original is not None:
                try:
                    runner.restore(original)
                    restored_configuration = runner.snapshot()
                    runner.event("restored", configuration=asdict(restored_configuration))
                    runner.check(
                        "configuration restored",
                        restored_configuration == original,
                        before=asdict(original),
                        after=asdict(restored_configuration),
                    )
                    runner.write("*GTL")
                except Exception as exc:
                    error = error or {"type": type(exc).__name__, "message": str(exc)}
                    runner.event("restore_error", **error)
            runner.close()

    summary = {
        "timestamp": now(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "port": args.port,
        "combinations": combinations,
        "checks": runner.checks,
        "passed": error is None and combinations == 480,
        "error": error,
        "trace": str(trace_path),
        "measurements": str(measurements_path),
        "initial_configuration": asdict(original) if original else None,
        "restored_configuration": (
            asdict(restored_configuration) if restored_configuration else None
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
