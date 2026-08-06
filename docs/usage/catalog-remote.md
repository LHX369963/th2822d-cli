# Catalog and front-panel control

```bash
th2822d commands show function.primary
th2822d get frequency.test
th2822d set voltage.level 0.6
th2822d action general.trigger
th2822d batch commands.scpi
```

Prefer catalog-backed `get`, `set`, and `action`. Use `raw` only for a valid SCPI
operation without a maintained command.

SCPI leaves the meter in remote mode. Use `action general.go-local` or the RMT
key only when the user explicitly wants front-panel control. Avoid
`general.local-lock` unless disabling the physical RMT key is intentional.

An earlier E10 was correlated with `*GTL`, but isolated tests passed after the
transport delay and Linux `HUPCL` fixes. Do not add automatic go-local or state
restoration to normal commands.
