# Transport and firmware behavior

Any received command enters remote mode; only RMT and POWER remain local. `*LLO`
locks RMT and `*GTL` requests local operation. An E10 was initially correlated
with `*GTL`, but repeated isolated tests later passed. It may have involved the
former close delay, Linux `HUPCL`, low power, or a busy measurement cycle; it
does not prove firmware rejects `*GTL`.

On `VER4.5.2307`, setting a high-impedance low-frequency mode can begin a full
SLOW measurement cycle. Traffic before completion can be silently dropped. The
transport waits 800 ms after non-query commands and retries a side-effect-free
timed-out query once. On transport failure, transactional configuration stops
traffic instead of rollback; readback mismatches are rolled back only while
communication remains proven.

Later AC settings can reset secondary. Apply non-NULL secondary after primary,
equivalent, frequency, and voltage. To select NULL, rewrite primary once before
remaining AC settings; rewriting it last can reset equivalent to series.

Linux disables `HUPCL`: otherwise closing a short-lived CLI process deasserts
CP2102 DTR and the next open can miss all responses. The Windows app instead
holds one COM session; disabling hangup supports independent CLI invocations.
