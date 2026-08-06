# Documented SCPI surface

| CLI name | SCPI | Operation |
|---|---|---|
| `general.idn/local-lock/go-local/trigger` | `*IDN?`/`*LLO`/`*GTL`/`*TRG` | identity, lock, local, trigger |
| `frequency.test` | `FREQuency[?]` | 100, 120, 1000, 10000 Hz |
| `voltage.level` | `VOLTage[?]` | 0.3, 0.6, 1 V RMS |
| `function.primary` | `FUNCtion:IMPA[?]` | L, C, R, Z, DCR |
| `function.secondary` | `FUNCtion:IMPB[?]` | D, Q, THETA, ESR; query may NULL |
| `function.equivalent` | `FUNCtion:EQUivalent[?]` | series or parallel |
| `tolerance.*` | `CALCulate:TOLerance:*` | state, nominal, value, range |
| `recording.*` | `CALCulate:RECording:*` | state, maximum/minimum/average/present |
| `measurement.fetch` | `FETCh?` | measurement values and tolerance bin |

Primary values are SI base units (H/F/ohm); THETA is degrees, ESR ohms, D/Q
dimensionless. The CLI keeps base units rather than display prefixes.

The manual defines E10 unknown command, E11 invalid parameter, E12 syntax error
on the meter display, not serial responses. The CLI validates catalog operations
before sending them.
