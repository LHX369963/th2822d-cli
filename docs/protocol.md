# TH2822D Serial Protocol

The TH2822D exposes a Silicon Labs CP2102 USB-to-UART bridge. The fixed serial
settings are 9600 baud, 8 data bits, no parity, one stop bit, and no flow
control. Commands are ASCII SCPI lines terminated by CR, LF, or CRLF. Query
responses terminate with CRLF.

Any received command places the meter in remote mode and disables the front
panel except for RMT and POWER. `*LLO` locks RMT and `*GTL` restores local
operation. An earlier E10 was initially correlated with `*GTL`, but the command
later passed repeated isolated tests. The earlier failure is consistent with
the old short close delay, Linux `HUPCL`, low power, or a busy measurement
cycle; it is not evidence that this firmware rejects `*GTL`.

On firmware `VER4.5.2307`, a setting can start a full SLOW measurement cycle.
Traffic sent before that cycle finishes can be silently dropped, especially
for high-impedance measurements at low frequency. The transport waits 800 ms
after non-query commands. Query-response traffic does not require this added
delay; if an otherwise side-effect-free query times out, it is retried once.

Transactional configuration stops sending traffic rather than attempting a
rollback if the transport becomes unresponsive. Protocol-level readback
mismatches are rolled back because communication is still proven to work.

Linux `HUPCL` is disabled on the serial file descriptor. Leaving it enabled
deasserts DTR whenever a short-lived CLI process closes the CP2102 and can make
the next port open miss all responses. The Windows application avoids this by
holding one COM session; disabling hangup provides equivalent behavior for
independent CLI invocations.

## Documented Surface

| CLI name | SCPI | Operation |
|---|---|---|
| `general.idn` | `*IDN?` | model, firmware, serial |
| `general.local-lock` | `*LLO` | lock front panel |
| `general.go-local` | `*GTL` | restore local control |
| `general.trigger` | `*TRG` | trigger (continuous measurement makes this effectively a no-op) |
| `frequency.test` | `FREQuency[?]` | 100, 120, 1000, or 10000 Hz on TH2822D |
| `voltage.level` | `VOLTage[?]` | 0.3, 0.6, or 1 V RMS |
| `function.primary` | `FUNCtion:IMPA[?]` | L, C, R, Z, or DCR |
| `function.secondary` | `FUNCtion:IMPB[?]` | write D, Q, THETA, or ESR; query may return `NULL` |
| `function.equivalent` | `FUNCtion:EQUivalent[?]` | series or parallel |
| `tolerance.enabled` | `CALCulate:TOLerance:STATe[?]` | tolerance mode |
| `tolerance.nominal` | `CALCulate:TOLerance:NOMinal?` | captured nominal |
| `tolerance.value` | `CALCulate:TOLerance:VALUe?` | deviation percentage |
| `tolerance.range` | `CALCulate:TOLerance:RANGe[?]` | 1, 5, 10, or 20 percent |
| `recording.enabled` | `CALCulate:RECording:STATe[?]` | meter-side statistics |
| `recording.maximum` | `CALCulate:RECording:MAXimum?` | maximum pair |
| `recording.minimum` | `CALCulate:RECording:MINimum?` | minimum pair |
| `recording.average` | `CALCulate:RECording:AVERage?` | average pair |
| `recording.present` | `CALCulate:RECording:PRESent?` | current pair |
| `measurement.fetch` | `FETCh?` | measurement values and tolerance bin |

The TH2822D reports primary values in SI base units: henries, farads, or ohms.
THETA is in degrees, ESR is in ohms, and D/Q are dimensionless. The CLI retains
base units in machine output instead of introducing display-dependent prefixes.

The manual documents `E10` (unknown command), `E11` (invalid parameter), and
`E12` (syntax error). These errors appear on the meter display and are not
described as serial responses, so the CLI validates catalog operations before
sending them.

## Fetch Variants

AC functions return:

```text
<primary NR3>,<secondary NR3>,<bin><CR><LF>
```

DCR returns:

```text
<primary NR3>,<bin><CR><LF>
```

Although the manual describes the bin as NR1, firmware `VER4.5.2307` returns
`N` when tolerance comparison is disabled. Over-range values are represented
with hyphens and become JSON `null`.

Firmware `VER4.5.2307` ignores `FUNCtion:IMPB NULL`; the manual correctly lists
`NULL` only as a query response. Writing the active primary parameter again
resets the secondary selection to `NULL`. The high-level
`configure --secondary NULL` workflow uses that observed behavior.

Tolerance range writes take effect only while tolerance mode is on. Range query
responses encode the percentage by ordinal bin: `BIN1` = 1%, `BIN2` = 5%,
`BIN3` = 10%, and `BIN4` = 20%. Turning tolerance mode off makes the range query
return `----`.

With instrument recording enabled, firmware `VER4.5.2307` returns valid
primary/secondary pairs for maximum, minimum, and average, but consistently
returns a single `-----` for `CALCulate:RECording:PRESent?`. The parser maps
that documented no-data marker to two JSON `null` values. Use `FETCh?` (the
CLI's `read` or `monitor`) for the live value.
