---
name: th2822d-cli
description: Operate, test, debug, or develop the Tonghui TH2822D LCR meter through the th2822d CLI, including configuration, readings, monitoring, tolerance, recording statistics, catalog SCPI, and connected validation; distinguish TH2822E-only features and exclude firmware modification.
---

# TH2822D CLI

Use the repository-local `.venv/bin/th2822d` when present. Resolve the repository
two levels above this Skill before opening linked files.

## Core workflow

- Omit `--port`; the CLI auto-selects the only attached TH2822-series meter.
  Specify it only when selection is genuinely ambiguous.
- Prefer `read`, `configure`, `monitor`, `recording`, `tolerance`, and catalog
  operations. Use `raw` only when no maintained interface exists.
- Read only the relevant guide: [configuration](../../docs/usage/configure.md),
  [monitoring](../../docs/usage/monitor.md),
  [tolerance/recording](../../docs/usage/tolerance-recording.md), or
  [catalog/remote](../../docs/usage/catalog-remote.md).
- For firmware-sensitive work, read [firmware.md](references/firmware.md).
- For stability or connected claims, read
  [validation.md](references/validation.md).

## Guardrails

- Use only discharged, unpowered components; never apply external voltage.
- Do not require state snapshots, restoration, routine preflight, or post-checks.
- Leave remote mode unchanged unless the user requests front-panel control.
- Do not expose TH2822E-only 100 kHz as typed TH2822D configuration.
- Do not modify firmware or invoke undocumented bootloader behaviour.
