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
`validation/live-2026-07-24.json`. One check only confirmed that `*LLO` and
`*GTL` bytes were written; it did not verify that the meter accepted them.
The meter later displayed E10 immediately after `*GTL`, so that check is
invalidated. The remaining 56 checks passed, and the acceptance script no
longer sends either command.

Coverage included:

- identity
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

- A command issued within roughly 100 ms after a setting can be dropped.
  A 200 ms write delay and one query-only retry were reliable.
- `FUNCtion:IMPB NULL` is ignored. Rewriting the active primary parameter
  resets the secondary response to `NULL`.
- Tolerance range writes are ignored while tolerance mode is off.
- Range responses are ordinal bins rather than literal percentages.
- `CALCulate:RECording:PRESent?` consistently returned `-----`; maximum,
  minimum, and average returned valid pairs.
- With tolerance disabled, `FETCh?` returned bin `N`, although the manual
  describes that field as NR1.
- The documented `*GTL` command produced E10 (unknown command) on
  `VER4.5.2307`. Pressing the physical RMT key restored local control. `*LLO`
  is not exercised because it could disable that recovery key.

The acceptance script restored the initial configuration:

```text
C, secondary NULL, 100 Hz, 0.3 V, PAL, tolerance OFF, recording OFF
```

## E10 Reliability Regression

After the operator cleared E10 with the physical RMT key, the `v0.1.1`
candidate passed five independent identity-query reopen cycles, a combined
configuration/readback transaction, a measurement, automatic discovery, and
final configuration restoration. No test sent `*GTL` or `*LLO`.

The retained report is `validation/reliability-2026-07-24.json`. The final
configuration was `Z`, secondary `NULL`, 10 kHz, 0.3 V, parallel equivalent,
tolerance off, and recording off.
