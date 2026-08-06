# Monitoring and file formats

```bash
th2822d monitor --count 20
th2822d monitor --duration 60 --format csv --output capture.csv
th2822d monitor --count 100 --format txt --output capture.txt
```

JSONL is the streaming default. Prefer CSV for durable tabular capture; use TXT
only when tab separation is required. Records contain UTC timestamps and SI
base units.

Polling does not change the meter's RATE setting. Polling faster than the active
measurement rate may repeat the latest reading. A single `read` cannot establish
stability or drift; see the Skill's `references/validation.md` when making such
claims.
