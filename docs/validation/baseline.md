# Baseline acceptance and differences

The original `tools/live_acceptance.py` reported 57 passed checks in
`../../validation/live-2026-07-24.json`. Its `*LLO`/`*GTL` check only proved writes;
the revised check follows actions with `*IDN?` identity verification.

Coverage included identity/local-lock actions; all TH2822D frequencies
(100/120 Hz, 1/10 kHz); all 0.3/0.6/1 V levels; series/parallel; L/C/R/Z/DCR
fetch shapes; D/Q/THETA/ESR and secondary reset; 1/5/10/20% tolerance bins;
recording state/statistics/PRESENT; trigger/fetch; and starting-state restoration.

At 100 Hz, 0.3 V, parallel C/ESR, the fixture measured C=671.994 uF and
ESR=0.0542421 ohm. This is a functional fixture result, not calibration.

Observed firmware differences: an early command can drop during SLOW cycle;
800 ms write delay and one query retry were reliable. `IMPB NULL` is ignored;
primary rewrite resets secondary. Tolerance range writes are ignored while off;
ranges return ordinal bins. PRESENT is `-----` while max/min/avg are valid;
tolerance-off fetch bin is `N`. An initial E10 near `*GTL` did not recur after
delay/HUPCL fixes, six isolated tests, and six full matrices.

The acceptance script restored `C`, secondary NULL, 100 Hz, 0.3 V, PAL,
tolerance OFF, recording OFF.
