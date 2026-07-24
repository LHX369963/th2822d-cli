#!/usr/bin/env python3
"""Connected TH2822D documented-command acceptance matrix."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from th2822d_cli.instrument import TH2822D
from th2822d_cli.protocol import parse_identity, parse_measurement, parse_number, parse_pair
from th2822d_cli.errors import TransportError
from th2822d_cli.transport import SerialTransport, serial_ports


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port")
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--fixture", default="680 uF polymer capacitor")
    ap.add_argument("--skip-fixture-range", action="store_true")
    args = ap.parse_args()

    if args.port:
        port = args.port
    else:
        candidates = serial_ports()
        if len(candidates) != 1:
            raise TransportError(f"expected one CP210x device, found {len(candidates)}; use --port")
        port = candidates[0].port
    report = {
        "timestamp": now(),
        "port": port,
        "fixture": args.fixture,
        "checks": [],
    }

    def check(name: str, passed: bool, **evidence) -> None:
        report["checks"].append({"name": name, "passed": bool(passed)} | evidence)

    with TH2822D(SerialTransport(port, args.timeout)) as meter:
        original = meter.configuration()
        report["original_configuration"] = original.to_dict()

        def set_query(command: str, value: str, expected: set[str] | None = None) -> str:
            meter.transport.write(f"{command} {value}")
            response = meter.transport.query(f"{command}?").upper()
            accepted = expected or {value.upper()}
            check(
                f"{command} {value}",
                response in accepted,
                command=command,
                requested=value,
                response=response,
            )
            return response

        try:
            identity = meter.identity()
            report["identity"] = identity.to_dict()
            check("identity", identity.model.startswith("TH2822D"), response=identity.to_dict())

            for value, response in (
                ("100", {"100HZ"}),
                ("120", {"120HZ"}),
                ("1000", {"1KHZ"}),
                ("10000", {"10KHZ"}),
            ):
                set_query("FREQuency", value, response)

            for value, response in (("0.3", {"0.3V"}), ("0.6", {"0.6V"}), ("1", {"1V"})):
                set_query("VOLTage", value, response)

            set_query("FUNCtion:EQUivalent", "SER", {"SER"})
            set_query("FUNCtion:EQUivalent", "PAL", {"PAL"})

            set_query("FREQuency", "100", {"100HZ"})
            set_query("VOLTage", "0.3", {"0.3V"})
            set_query("FUNCtion:IMPA", "C")
            set_query("FUNCtion:EQUivalent", "PAL")
            for secondary in ("D", "Q", "THETA", "ESR", "NULL"):
                if secondary == "NULL":
                    meter.transport.write("FUNCtion:IMPA C")
                    response = meter.transport.query("FUNCtion:IMPB?").upper()
                    check(
                        "reset secondary to NULL",
                        response == "NULL",
                        command="FUNCtion:IMPA C",
                        response=response,
                    )
                else:
                    set_query("FUNCtion:IMPB", secondary)

            primary_results = {}
            for primary in ("L", "C", "R", "Z", "DCR"):
                set_query("FUNCtion:IMPA", primary)
                time.sleep(0.8)
                secondary = "NULL" if primary == "DCR" else meter.transport.query("FUNCtion:IMPB?")
                response = meter.transport.query("FETCh?")
                measurement = parse_measurement(response, primary, secondary)
                primary_results[primary] = measurement.to_dict()
                check(
                    f"fetch {primary}",
                    measurement.primary == primary,
                    response=response,
                    parsed=measurement.to_dict(),
                )

            set_query("FUNCtion:IMPA", "C")
            set_query("FUNCtion:IMPB", "ESR")
            set_query("FUNCtion:EQUivalent", "PAL")
            set_query("FREQuency", "100", {"100HZ"})
            set_query("VOLTage", "0.3", {"0.3V"})
            time.sleep(1.5)
            capacitor = meter.measurement("C", "ESR")
            capacitance_uf = None if capacitor.primary_value is None else capacitor.primary_value * 1e6
            if args.skip_fixture_range:
                check(
                    "fixture capacitance fetch",
                    capacitance_uf is not None,
                    capacitance_uf=capacitance_uf,
                    measurement=capacitor.to_dict(),
                )
            else:
                check(
                    "680 uF capacitor",
                    capacitance_uf is not None and 500 <= capacitance_uf <= 850,
                    capacitance_uf=capacitance_uf,
                    measurement=capacitor.to_dict(),
                )
            report["capacitor_measurement"] = capacitor.to_dict() | {"capacitance_uf": capacitance_uf}

            set_query("CALCulate:TOLerance:STATe", "ON")
            for value, response in (("1", {"BIN1"}), ("5", {"BIN2"}), ("10", {"BIN3"}), ("20", {"BIN4"})):
                set_query("CALCulate:TOLerance:RANGe", value, response)
            time.sleep(0.8)
            nominal_response = meter.transport.query("CALCulate:TOLerance:NOMinal?")
            deviation_response = meter.transport.query("CALCulate:TOLerance:VALUe?")
            tolerance_fetch = meter.transport.query("FETCh?")
            nominal = parse_number(nominal_response)
            deviation = parse_number(deviation_response)
            check(
                "tolerance values",
                nominal is not None and deviation is not None,
                nominal=nominal,
                deviation_percent=deviation,
                fetch=tolerance_fetch,
            )
            set_query("CALCulate:TOLerance:STATe", "OFF")

            set_query("CALCulate:RECording:STATe", "ON")
            time.sleep(2.2)
            statistics = {}
            for name, command in (
                ("maximum", "CALCulate:RECording:MAXimum?"),
                ("minimum", "CALCulate:RECording:MINimum?"),
                ("average", "CALCulate:RECording:AVERage?"),
                ("present", "CALCulate:RECording:PRESent?"),
            ):
                response = meter.transport.query(command)
                statistics[name] = parse_pair(response)
                passed = response == "-----" if name == "present" else statistics[name]["primary_value"] is not None
                check(
                    f"recording {name}",
                    passed,
                    response=response,
                    parsed=statistics[name],
                    note="VER4.5.2307 returns no PRESENT data" if name == "present" else "",
                )
            report["recording_statistics"] = statistics
            set_query("CALCulate:RECording:STATe", "OFF")

            meter.transport.write("*TRG")
            trigger_fetch = meter.transport.query("FETCh?")
            check("trigger", bool(trigger_fetch), response=trigger_fetch)
            meter.transport.write("*LLO")
            meter.transport.write("*GTL")
            local_restore_identity = parse_identity(meter.transport.query("*IDN?"))
            check(
                "local lock and local restore",
                local_restore_identity.model.startswith("TH2822D"),
                response=local_restore_identity.to_dict(),
            )
        finally:
            # The documented protocol cannot clear a stored tolerance range, but
            # disabling tolerance restores the externally observable off state.
            meter.transport.write("CALCulate:TOLerance:STATe OFF")
            meter.transport.write("CALCulate:RECording:STATe OFF")
            meter.transport.write(f"FREQuency {original.frequency_hz}")
            meter.transport.write(f"VOLTage {original.voltage_v:g}")
            meter.transport.write(f"FUNCtion:IMPA {original.primary}")
            if original.secondary != "NULL":
                meter.transport.write(f"FUNCtion:IMPB {original.secondary}")
            meter.transport.write(f"FUNCtion:EQUivalent {original.equivalent}")

        restored = meter.configuration()
        report["restored_configuration"] = restored.to_dict()
        for field in ("frequency_hz", "voltage_v", "primary", "secondary", "equivalent"):
            check(
                f"restore {field}",
                getattr(restored, field) == getattr(original, field),
                before=getattr(original, field),
                after=getattr(restored, field),
            )
        check("restore tolerance off", not restored.tolerance_enabled)
        check("restore recording off", not restored.recording_enabled)

    report["passed"] = all(item["passed"] for item in report["checks"])
    report["summary"] = {
        "passed": sum(item["passed"] for item in report["checks"]),
        "failed": sum(not item["passed"] for item in report["checks"]),
        "total": len(report["checks"]),
    }
    text = json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
