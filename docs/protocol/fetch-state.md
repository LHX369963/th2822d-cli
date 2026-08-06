# Fetch, tolerance, and recording behavior

AC `FETCh?` returns `<primary NR3>,<secondary NR3>,<bin>`; DCR omits secondary.
Firmware `VER4.5.2307` returns bin `N` with tolerance off though the manual calls
it NR1. Over-range hyphens map to JSON `null`.

In DCR, secondary is implicitly NULL. `FUNCtion:IMPB?` produces E10/no response;
voltage, secondary, and equivalent apply only outside DCR. High-level DCR config
therefore reads only primary and reports non-applicable configuration as null.

`FUNCtion:IMPB NULL` is ignored; the manual lists NULL only as a query response.
Rewriting the active primary resets secondary to NULL, so `configure --secondary
NULL` uses that behavior.

Tolerance range writes work only while tolerance is on. Range responses are
ordinal: BIN1=1%, BIN2=5%, BIN3=10%, BIN4=20%. With tolerance off, range query
returns `----`.

With recording enabled, maximum/minimum/average return valid primary/secondary
pairs but `RECording:PRESent?` returns one `-----`; the parser maps it to two
JSON nulls. Use `FETCh?` (`read`/`monitor`) for the live value.
