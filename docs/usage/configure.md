# Configuration and readings

```bash
th2822d read
th2822d configure --primary C --secondary ESR \
  --frequency 100 --voltage 0.3 --equivalent PAL
```

Primary modes are L, C, R, Z, and DCR; secondary modes are D, Q, THETA, and ESR.
TH2822D supports 100/120 Hz and 1/10 kHz, 0.3/0.6/1 V, and series/parallel
equivalents. Measurements use SI base units, so display prefixes need no parsing.

Use `--secondary NULL` to hide the secondary display. Firmware does not accept
`FUNCtion:IMPB NULL` directly; the CLI performs the observed primary-reset
workflow. DCR has an implicit NULL secondary and non-applicable fields are JSON
`null`.

Typed configuration verifies final readback. Do not add separate configuration
snapshots, restoration, or health checks around ordinary changes.
