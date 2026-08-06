# Exhaustive parameter-space acceptance

`tools/exhaustive_acceptance.py` covered the complete documented AC product:

```text
L/C/R/Z x D/Q/THETA/ESR/NULL x SER/PAL x 100/120/1000/10000 Hz x 0.3/0.6/1 V
= 480 unique combinations
```

Each combination verified primary, secondary, equivalent, frequency, and voltage
before `FETCh?`. It also covered DCR-safe subset, tolerance ranges/queries,
recording statistics, identity, trigger, `*LLO`, and `*GTL`.

The 1154.597 s run passed 3985 checks with no transport/protocol/readback error
or missing combination. It produced 480 CSV measurements and 14,152 trace
events. Initial/restored state was DCR with non-applicable fields null; final
command was `*GTL`.

Two earlier runs stopped on final-state mismatch and sent no further traffic.
They established ordering: write non-NULL secondary last; establish NULL by one
primary rewrite before remaining AC settings.

Artifacts remain in `../../validation/exhaustive-2026-07-24/`: `summary.json`,
`measurements.csv`, and `trace.jsonl`.
