# Connected Validation

## Bench Setup

- Date: 2026-07-24
- Meter: `TH2822D Handheld LCR Meter`
- Firmware: `VER4.5.2307`
- Serial: `SNQ48C240168`
- USB bridge: Silicon Labs CP2102, `10c4:ea60`
- Device node during validation: `/dev/ttyUSB0`
- Fixture: nominal 680 uF polymer capacitor

## Acceptance Result

The original `tools/live_acceptance.py` run reported 57 passed checks in
`validation/live-2026-07-24.json`. Its `*LLO`/`*GTL` check only confirmed that
bytes were written. The revised check now follows those actions with `*IDN?`
and verifies the returned identity.

Coverage included:

- identity and front-panel local/lock actions
- all TH2822D frequencies: 100 Hz, 120 Hz, 1 kHz, and 10 kHz
- all levels: 0.3 V, 0.6 V, and 1 V
- series and parallel equivalent modes
- L, C, R, Z, and DCR fetch shapes
- D, Q, THETA, ESR, and secondary-display reset
- 1%, 5%, 10%, and 20% tolerance bins plus nominal/deviation queries
- recording state, maximum, minimum, average, and PRESENT response
- trigger and measurement fetch
- restoration of the starting configuration

At 100 Hz, 0.3 V, parallel C/ESR, the fixture measured:

```text
C   = 671.994 uF
ESR = 0.0542421 ohm
```

This is a functional fixture result, not an independent accuracy calibration.

## Observed Firmware Differences

- A command issued before a SLOW measurement cycle finishes can be dropped.
  An 800 ms write delay and one query-only retry were reliable.
- `FUNCtion:IMPB NULL` is ignored. Rewriting the active primary parameter
  resets the secondary response to `NULL`.
- Tolerance range writes are ignored while tolerance mode is off.
- Range responses are ordinal bins rather than literal percentages.
- `CALCulate:RECording:PRESent?` consistently returned `-----`; maximum,
  minimum, and average returned valid pairs.
- With tolerance disabled, `FETCh?` returned bin `N`, although the manual
  describes that field as NR1.
- An E10 was initially correlated with `*GTL`, but the command subsequently
  passed six isolated tests and six complete command-matrix cycles after the
  transport delay and Linux `HUPCL` fixes. The earlier event does not establish
  that `*GTL` is invalid.

The acceptance script restored the initial configuration:

```text
C, secondary NULL, 100 Hz, 0.3 V, PAL, tolerance OFF, recording OFF
```

## E10 Reliability Regression

After the operator cleared E10 with the physical RMT key, the `v0.1.1`
candidate passed five independent identity-query reopen cycles, a combined
configuration/readback transaction, a measurement, automatic discovery, and
final configuration restoration.

The retained report is `validation/reliability-2026-07-24.json`. The final
configuration was `Z`, secondary `NULL`, 10 kHz, 0.3 V, parallel equivalent,
tolerance off, and recording off.

The follow-up `v0.1.2` candidate passed six isolated `*GTL` attempts, then six
complete documented-command cycles from 09:43:50Z through 09:48:13Z. All
342 checks passed. Each cycle covered all frequencies, voltages, equivalent
modes, primary and secondary functions, tolerance operations, recording
statistics, fetch, trigger, `*LLO`, `*GTL`, identity verification, and state
restoration. Reports are retained as
`validation/stress-all-commands-2026-07-24-run1.json` through `run6.json`.

The final stress-test configuration matched its starting snapshot:

```text
L, secondary NULL, 10 kHz, 0.3 V, SER, tolerance OFF, recording OFF
```
