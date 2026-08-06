# TH2822D serial protocol

The meter uses a CP2102 at 9600 8N1 with no flow control; commands are ASCII
SCPI ending CR, LF, or CRLF and query responses end CRLF.

- [Transport and firmware behavior](protocol/transport-firmware.md)
- [Documented SCPI surface](protocol/catalog.md)
- [Fetch, tolerance, and recording behavior](protocol/fetch-state.md)

Use these references for protocol/firmware work, not as a required preflight for
ordinary CLI measurement.
