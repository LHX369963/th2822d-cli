# Windows LCR Software Parity

The supplied Windows package identifies itself as `LCR Software` version 2.0.0
and contains a LabVIEW 8.5 application built on `TH2822.vi`. Its deployable
payload contains:

- `Com_readwrite.vi` and `Com_write.vi` for serial instrument traffic
- a persisted COM-port file (the supplied default is COM3)
- `Save as *.txt`
- `Save as *.xls`, the LabVIEW Excel report toolkit, and Excel chart helpers

The meter's user manual defines the complete remote protocol used by that
application. There is no separate binary transport or undocumented device
subsystem in the package inventory.

## Workflow Mapping

| Windows workflow | CLI equivalent |
|---|---|
| select COM port | automatic TH2822 identity discovery or `--port` |
| show model/version/serial | `info` |
| read all current controls | `config` |
| select L/C/R/Z/DCR | `configure --primary` |
| select D/Q/THETA/ESR | `configure --secondary` |
| hide secondary value | `configure --secondary NULL` |
| select frequency/level/equivalent | `configure --frequency/--voltage/--equivalent` |
| live reading | `read` |
| continuous graph/data acquisition | `monitor` |
| tolerance compare | `configure --tolerance ON --tolerance-range ...`, then `tolerance` |
| min/max/average record | `configure --recording ON`, then `recording` |
| save text | `monitor --format txt --output ...` |
| save Excel-readable data | `monitor --format csv --output ...` |
| send a protocol command | catalog `get`/`set`/`action`, `raw`, or `batch` |
| return front-panel control | automatic on close, or `action general.go-local` |

The CLI deliberately replaces legacy binary `.xls` and Excel COM automation
with CSV. CSV opens directly in Excel, streams without buffering the whole
capture, is straightforward to parse, and avoids a spreadsheet-specific
runtime dependency. JSONL is also available for typed automation.

Evidence is limited to the supplied installer resources, the official manual,
and connected firmware behavior. Cosmetic GUI replication is not a CLI goal;
every device operation and persistent data/report workflow has a CLI path.
