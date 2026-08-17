"""Aggregated TH2822D measurement summaries."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time

from .errors import ProtocolError
from .instrument import TH2822D


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
        print(json.dumps({
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
        }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    else:
        print(f"{median} {valid[-1].primary_unit} spread={maximum - minimum:.8g}")


