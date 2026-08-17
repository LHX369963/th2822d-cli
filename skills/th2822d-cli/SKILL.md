---
name: th2822d-cli
description: Control and measure the connected TH2822D LCR meter with the th2822d CLI.
---

# TH2822D CLI

Use `th2822d/.venv/bin/th2822d` from the instrument-cli workspace. The only
attached meter is selected automatically. Execute the requested operation
directly; do not inspect, preserve, restore, or clean up unrelated state.

Common forms:

```bash
th2822d/.venv/bin/th2822d measure
th2822d/.venv/bin/th2822d measure --expect 0.00022
th2822d/.venv/bin/th2822d configure --frequency 1000 --primary L --secondary Q
```

`measure` returns the value and observed spread. Absence of a warning means the
result was stable; warnings do not suppress it.
