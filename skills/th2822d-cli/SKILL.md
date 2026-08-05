---
name: th2822d-cli
description: Operate, test, debug, or document the Tonghui TH2822D LCR meter through the public th2822d CLI, including discovery, configuration, L/C/R/Z/DCR readings, D/Q/THETA/ESR secondary values, tolerance comparison, recording statistics, continuous JSONL/CSV/text capture, raw SCPI, batch commands, and connected validation with passive components. Use for TH2822D hardware work, th2822d command changes, LCR data acquisition, protocol diagnosis, or deployment; distinguish TH2822E-only 100 kHz support and exclude firmware modification.
---

# TH2822D CLI

## Establish Context

Resolve the repository as the directory two levels above this Skill's real
path. Read `README.md`, validation evidence, or protocol details only when the
task needs them.

The validated meter is `TH2822D Handheld LCR Meter`, firmware
`VER4.5.2307`, serial `SNQ48C240168`. It uses a CP2102 at 9600 8N1 and has
appeared as `/dev/ttyUSB0`; use a known explicit node directly and discover only
when selection is uncertain.

## Use The Public CLI

Use `th2822d`, preferring the repository's `.venv/bin/th2822d` when present.
Do not open the serial node directly or call transport classes when a public
CLI workflow exists.

Run the requested operation directly when the meter and serial node are known.
Use `list`, `info`, or `config` only for discovery, identity, or configuration
diagnosis; do not make them routine preflight.

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

Ordinary invocations leave the meter remote. Use the typed go-local action or
physical RMT key only when the user explicitly requests front-panel control. An earlier E10 was
initially correlated with `*GTL`, but repeated isolated tests passed after the
transport delay and Linux `HUPCL` fixes. Avoid `general.local-lock` unless
locking the physical RMT key is intentional.

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

Do not require users to record or restore configuration around ordinary mode
changes. `tools/live_acceptance.py` is reserved for explicit connected acceptance
work and is not part of routine measurement.

Do not infer component identity or calibration from one broad reading. Report
the exact frequency, level, equivalent mode, and secondary parameter. Treat
the connected 680 uF result as a functional fixture check, not a calibration
certificate.

## Handle Firmware Behavior

Allow the transport's 800 ms write delay and query retry; firmware can silently
drop commands sent too soon. The transport disables Linux `HUPCL` so
closing a short-lived process does not deassert CP2102 DTR. Typed settings
verify readback and retry without resending actions. Multi-option `configure`
verifies the final combined state and rolls back readback mismatches. It sends
no rollback traffic after a transport failure.

DCR has no secondary parameter. Never query `FUNCtion:IMPB?` while DCR is
active; firmware `VER4.5.2307` displays E10 and returns no serial response.
Treat the DCR secondary as implicitly `NULL`.

Interpret tolerance bins as `BIN1` = 1%, `BIN2` = 5%, `BIN3` = 10%, and
`BIN4` = 20%. Range writes are ignored while tolerance is off.

Firmware `VER4.5.2307` returns a single `-----` for recording PRESENT even
while maximum, minimum, and average are valid. Use `read` or `monitor` for the
live value and preserve PRESENT as JSON nulls.

Do not offer 100 kHz through typed TH2822D configuration; that mode belongs
to TH2822E. Do not generalize connected TH2822D findings to other models.

## Handle CLI Failures Without Losing The Task

Report every CLI error to the user as soon as it occurs, including the failing
command and immediate impact, but do not stop work solely because an error
occurred. Keep the requested task as the first priority:

- If the error blocks the task, diagnose it and attempt a repair immediately so
  the task can continue.
- If the error does not block the task, record enough evidence to reproduce it,
  finish the requested task first, and then diagnose and attempt a repair.
- After a repair, run focused regression tests plus the repository's required
  test suite and any safe connected checks needed to establish the fix.
- When the repair is complete and sufficiently verified, commit only the
  repair-related changes and push that commit to the current repository remote.
  Do not include unrelated pre-existing worktree changes.
- If the repair is incomplete, cannot be pushed, or lacks sufficient testing,
  continue any remaining feasible task work and explain the error, attempted
  repair, remaining risk, and missing validation in detail in the final report.

## Verify Changes And Claims

After code changes, run the offline tests:

```bash
python -m pytest
```

Run focused connected acceptance only when the change requires it. Retain that
evidence under `validation/`; do not require final configuration comparison or
restoration as a routine user step. Separate protocol readback, functional
component response, and metrological accuracy in all reports.
