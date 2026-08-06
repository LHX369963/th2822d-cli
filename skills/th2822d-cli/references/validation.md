# Measurement and change validation

For stability claims, use bounded `monitor` windows and retain timestamps,
modes, units, minimum, maximum, median, spread, overloads, and outliers. Repeat
after varied waits when intermittency matters.

Report frequency, level, equivalent mode, and secondary parameter. Distinguish
protocol readback, functional component response, and metrological accuracy. A
680 uF fixture result is not a calibration certificate.

Use `tools/live_acceptance.py` only for explicit connected acceptance, never as
a normal measurement prerequisite. After code changes, run `python -m pytest`
and only the focused connected test required by the change.

Commit and push only completed, verified, related changes. If repair or push is
incomplete, report the remaining risk rather than claiming completion.

Keep README and Skill as short navigation; put feature examples in `docs/usage/`.
