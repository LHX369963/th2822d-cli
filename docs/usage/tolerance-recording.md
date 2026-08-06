# Tolerance and recording

Enable tolerance before selecting its range:

```bash
th2822d configure --tolerance ON --tolerance-range 5
th2822d tolerance
th2822d configure --tolerance OFF
```

Tolerance bins are `BIN1` 1%, `BIN2` 5%, `BIN3` 10%, and `BIN4` 20%. Firmware
ignores range writes while tolerance is off.

Meter-side statistics:

```bash
th2822d configure --recording ON
th2822d recording
th2822d configure --recording OFF
```

Firmware `VER4.5.2307` can return `-----` for PRESENT while maximum, minimum,
and average remain valid. The CLI preserves PRESENT as JSON null; use `read` or
`monitor` for the live value.
