---
name: th2822d-cli
description: Operate, test, debug, or document the Tonghui TH2822D LCR meter through the public th2822d CLI, including discovery, configuration, L/C/R/Z/DCR readings, D/Q/THETA/ESR secondary values, tolerance comparison, recording statistics, continuous JSONL/CSV/text capture, raw SCPI, batch commands, and connected validation with passive components. Use for TH2822D hardware work, th2822d command changes, LCR data acquisition, protocol diagnosis, or deployment; distinguish TH2822E-only 100 kHz support and exclude firmware modification.
---

# TH2822D CLI

## Establish Context

Resolve the repository as the directory two levels above this Skill's real
path. Read `README.md` before device work and `docs/validation.md` before
coverage claims. Read `docs/protocol.md` when command semantics or firmware
quirks matter.

The validated meter is `TH2822D Handheld LCR Meter`, firmware
`VER4.5.2307`, serial `SNQ48C240168`. It uses a CP2102 at 9600 8N1 and has
appeared as `/dev/ttyUSB0`; discover it rather than assuming the node.

## Use The Public CLI

Use `th2822d`, preferring the repository's `.venv/bin/th2822d` when present.
Do not open the serial node directly or call transport classes when a public
CLI workflow exists.

Start with:

```bash
th2822d list
th2822d info
th2822d config
th2822d read
```

Configure through the high-level command:

```bash
th2822d configure --primary C --secondary ESR \
  --frequency 100 --voltage 0.3 --equivalent PAL
```

Use `configure --secondary NULL` to hide the secondary parameter. Firmware
does not accept `FUNCtion:IMPB NULL` directly; the CLI implements the observed
primary-reset workflow.

For tolerance, enable the mode before selecting a range:

```bash
th2822d configure --tolerance ON --tolerance-range 5
th2822d tolerance
th2822d configure --tolerance OFF
```

For meter-side statistics:

```bash
th2822d configure --recording ON
th2822d recording
th2822d configure --recording OFF
```

Prefer catalog-backed `get`, `set`, and `action` for individual manual
commands. Inspect them with `commands show`. Use `raw` only for a valid SCPI
operation that lacks a typed workflow, and `batch` for line-oriented command
files.

Ordinary invocations send `*GTL` on close and restore front-panel control.
Use `--stay-remote` only when another process is intentionally continuing
remote work. `action general.local-lock` intentionally remains locked until
`action general.go-local`.

## Capture Across Time

A single `read` cannot establish stability or drift. Use `monitor` with a
finite count or duration:

```bash
th2822d monitor --count 20
th2822d monitor --duration 60 --format csv --output capture.csv
```

JSONL is the stable streaming default. Prefer CSV for durable tabular capture
and spreadsheet use; use `txt` only when tab separation is required. Records
use SI base units.

Host polling does not change the meter's front-panel RATE setting. Polling
faster than the active measurement rate can repeat the most recent reading.
Record sample count, timestamps, primary and secondary modes, units, minimum,
maximum, median, spread, overloads, and outliers for stability claims. Repeat
windows after varied waits when intermittent behavior is possible.

## Enforce Measurement Safety

Use only discharged, unpowered components. Discharge capacitors before
connecting or removing them. Never apply external voltage to the LCR
terminals, measure a powered circuit, modify firmware, or invoke undocumented
bootloader behavior.

Before changing modes, record `config`. Restore frequency, voltage, primary,
secondary, equivalent, tolerance state, and recording state in cleanup. Use
`tools/live_acceptance.py` for the connected matrix because it performs this
restoration in `finally`.

Do not infer component identity or calibration from one broad reading. Report
the exact frequency, level, equivalent mode, and secondary parameter. Treat
the connected 680 uF result as a functional fixture check, not a calibration
certificate.

## Handle Firmware Behavior

Allow the transport's 200 ms delay after settings/actions and query retry;
firmware can silently drop commands sent too soon.

Interpret tolerance bins as `BIN1` = 1%, `BIN2` = 5%, `BIN3` = 10%, and
`BIN4` = 20%. Range writes are ignored while tolerance is off.

Firmware `VER4.5.2307` returns a single `-----` for recording PRESENT even
while maximum, minimum, and average are valid. Use `read` or `monitor` for the
live value and preserve PRESENT as JSON nulls.

Do not offer 100 kHz through typed TH2822D configuration; that mode belongs
to TH2822E. Do not generalize connected TH2822D findings to other models.

## Verify Changes And Claims

Run:

```bash
python -m pytest
python tools/live_acceptance.py --port /dev/ttyUSB0
```

Retain connected evidence under `validation/`. Verify final `config` matches
the starting state. Separate protocol readback, functional component response,
and metrological accuracy in all reports.
