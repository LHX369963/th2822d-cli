# E10 and DCR reliability regressions

After clearing E10 using RMT, `v0.1.1` passed five identity-query reopen cycles,
combined configuration/readback, measurement, discovery, and final restoration.
`../../validation/reliability-2026-07-24.json` records final Z, NULL, 10 kHz, 0.3 V,
parallel, tolerance/recording off.

`v0.1.2` passed six isolated `*GTL` attempts and six documented-command cycles
from 09:43:50Z to 09:48:13Z: 342 checks covering all frequencies, voltages,
equivalents, primary/secondary functions, tolerance, recording, fetch, trigger,
`*LLO`, `*GTL`, identity, and restoration. Reports are
`validation/stress-all-commands-2026-07-24-run1.json` through `run6.json`.
Final state matched its L, NULL, 10 kHz, 0.3 V, SER, tolerance/recording-off
snapshot. The reports are under `../../validation/`.

`v0.1.3` found DCR itself valid; the E10 came from querying `FUNCtion:IMPB?`
after selecting DCR. Firmware treats it as invalid and sends no response. The
fix treats DCR secondary as NULL, never queries/resets IMPB in DCR, reads only
IMPA, and reports frequency/voltage/secondary/equivalent/tolerance/recording as
JSON null. Unit tests assert both command streams.
