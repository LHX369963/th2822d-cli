# Tonghui TH2822D CLI

A Linux command-line replacement for the TH2822D Windows LCR Software. It
controls every SCPI operation documented by the meter and adds script-friendly
configuration snapshots, typed readings, continuous JSONL/CSV capture, raw
commands, and batch execution.

Tested with:

```text
TH2822D Handheld LCR Meter,VER4.5.2307,SNQ48C240168
```

## Coverage

- All 19 documented SCPI catalog entries, representing every query, setting,
  action, tolerance value, recording statistic, and measurement fetch
- CP2102 discovery and identity probing; explicit `--port` selection
- L/C/R/Z/DCR primary parameters and D/Q/THETA/ESR secondary parameters
- 100/120 Hz and 1/10 kHz test frequency, 0.3/0.6/1 V test level, and
  series/parallel equivalent modes
- Instrument-side tolerance and min/max/average recording
- UTC-stamped JSON, JSONL, CSV, and tab-separated text data acquisition
- Catalog-based `get`, `set`, and `action`, plus `raw` and `batch`
- Stable independent invocations without toggling front-panel control

TH2822E's 100 kHz mode is intentionally not exposed by the typed TH2822D
configuration command. It remains available through `raw` when using compatible
hardware.

## Install

Python 3.10 or newer is required.

```bash
git clone https://github.com/LHX369963/th2822d-cli.git
cd th2822d-cli
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
```

The CP210x node is normally owned by `root:dialout`. Add the user to `dialout`
once if needed, then log out and back in:

```bash
sudo usermod -aG dialout "$USER"
```

Do not run the CLI with `sudo`.

## Use

```bash
th2822d list
th2822d info
th2822d config
th2822d read

th2822d configure --primary C --secondary ESR --frequency 100 --voltage 0.3 --equivalent PAL
th2822d monitor --count 20
th2822d monitor --duration 60 --format csv --output capacitor.csv
th2822d monitor --count 100 --format txt --output capacitor.txt

th2822d configure --recording ON
th2822d recording
th2822d configure --recording OFF

th2822d configure --tolerance-range 5 --tolerance ON
th2822d tolerance
th2822d configure --tolerance OFF
```

Catalog and low-level workflows:

```bash
th2822d commands list
th2822d commands list --section recording
th2822d commands show function.primary
th2822d get frequency.test
th2822d set voltage.level 0.6
th2822d action general.trigger
th2822d raw 'FETCh?'
th2822d batch commands.scpi
```

Output is compact JSON. `monitor` emits JSONL by default so each line is a
complete record suitable for streaming tools. Measurements use SI base units
(`F`, `H`, `ohm`, `deg`); display prefixes never need to be parsed.
CSV is the recommended durable capture format and opens directly in spreadsheet
software without adding a spreadsheet-specific runtime dependency.

Use `--port /dev/ttyUSB0` when more than one compatible adapter is connected.
Automatic discovery probes CP2102 adapters with `*IDN?` and only accepts a
TH2822-series identity. The default two-second timeout can be changed with
`--timeout`.

Any SCPI command places the meter in remote mode. Although the manual documents
`*GTL`, connected firmware `VER4.5.2307` displayed E10 when it was sent.
The CLI therefore remains remote on exit and rejects the typed go-local action;
press the physical RMT key to restore front-panel control. Do not use
`general.local-lock` unless locking the physical RMT key is intentional.

## Safety

Discharge capacitors before connecting or removing them. Never measure a
powered circuit, and do not apply external voltage to the LCR terminals. USB
remote control does not change these instrument safety requirements.

## Verification

```bash
python -m pytest
python tools/live_acceptance.py --port /dev/ttyUSB0
```

The tracked Codex skill is in `skills/th2822d-cli`. Protocol details and observed
firmware behavior are in [docs/protocol.md](docs/protocol.md). Connected results
are recorded in [docs/validation.md](docs/validation.md).

The legacy Windows application's extracted resource inventory and workflow
mapping are documented in [docs/windows-parity.md](docs/windows-parity.md).
The supplied Chinese user manual and series datasheet are retained under
`docs/official/` with SHA-256 checksums.
