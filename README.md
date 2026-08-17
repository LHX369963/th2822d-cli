# Tonghui TH2822D CLI

Linux CLI for TH2822D configuration, typed LCR readings, continuous capture,
meter-side statistics, tolerance comparison, and catalog-backed SCPI access.

## Install

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

If CP210x access is denied, add the user to `dialout` once and log in again:

```bash
sudo usermod -aG dialout "$USER"
```

Do not run the CLI with `sudo`.

## Quick use

```bash
th2822d measure
th2822d configure --primary C --secondary ESR --frequency 100 --voltage 0.3
th2822d monitor --duration 60 --format csv --output capacitor.csv
```

Use a known `--port` directly. `list`, `info`, and `config` are only for
uncertain selection, identity, or configuration.

Discharge components before connection. Never measure a powered circuit or
apply external voltage to the LCR terminals.

## Read only what the task needs

- [Configuration and readings](docs/usage/configure.md)
- [Monitoring and file formats](docs/usage/monitor.md)
- [Tolerance and recording](docs/usage/tolerance-recording.md)
- [Catalog and front-panel control](docs/usage/catalog-remote.md)
- [Protocol and firmware behaviour](docs/protocol.md)
- [Connected evidence](docs/validation.md)
- [Windows feature parity](docs/windows-parity.md)

The Codex skill is in [`skills/th2822d-cli`](skills/th2822d-cli).
