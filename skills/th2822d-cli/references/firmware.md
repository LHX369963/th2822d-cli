# Firmware behaviour

Validated target: `TH2822D Handheld LCR Meter`, firmware `VER4.5.2307`, serial
`SNQ48C240168`, CP2102 at 9600 8N1.

Allow the transport's 800 ms write delay and query retry; this firmware can drop
commands sent too soon. Linux `HUPCL` is disabled so short processes do not
deassert CP2102 DTR. Typed settings verify readback without resending actions.

Never query `FUNCtion:IMPB?` in DCR mode: firmware displays E10 and stops
responding. Treat the secondary as implicit NULL.

Do not offer 100 kHz through typed TH2822D configuration; it belongs to TH2822E.
Do not generalize connected TH2822D findings to other models.
