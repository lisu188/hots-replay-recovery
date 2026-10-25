# Main-client product IPC table - 2026-10-25

The current 98348 client contains a one-entry product lookup table and a small
getter that caches its record for ID 1. This connects the previously identified
product constructor to an actual lookup/getter path. It does not identify the
mapped IPC handler or the owner of old-client downloading.

The [companion observation](../observations/main-product-ipc-table-2026-10-25.json)
contains source hashes, addresses, export quality and limits. All addresses
below are RVAs unless explicitly marked VA. The source is the pinned 98348
`HeroesOfTheStorm_x64.exe`, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.

## Authenticated table and getter

The bounded `.rdata` and `.data` inspection found one absolute pointer to
constructor VA `0x1413844E0`. It is stored at RVA `0x27CC578`, offset `+0x20`
within the record at `0x27CC558`. The record's first value is ID 1. A pointer
to that record appears in the table at `0x2F82E18`.

The leaf lookup beginning at `0x1384460` loads that table, compares the first
DWORD of its sole inspected record with incoming ECX, and returns the matching
record pointer or zero. Its entry is the authenticated target of the getter's
E8 call. The decoded flow comprises 15 instructions and 42 bytes through the
second RET at `0x1384489`. This leaf has no `.pdata` RuntimeFunction record.
The retained 64-byte decoding window contains trailing bytes after the two
returns; those bytes remain unclassified and are excluded from this result.

| Getter location | Observed operation |
| --- | --- |
| `0x24C7F0..0x24C829` | Complete selected RuntimeFunction interval, 57 bytes. |
| `0x24C7F4`, `0x24C806` | Reads and updates guard bit 0 at `0x2FE32F0`. |
| `0x24C801` | Supplies product ID 1 in ECX. |
| `0x24C80C` | Calls lookup `0x1384460`. |
| `0x24C811` | Stores the returned record pointer at `0x2FE32E8`. |
| `0x24C81D` | Returns the cached record pointer on the initialized branch. |

The new Ghidra export completed with 14 selected instructions, 14 expanded
instructions, no outside blocks and no size-limit truncation. The caller's
57 bytes and all 15 decoded leaf instructions match the pinned decoded patch.
The Ghidra job opened the existing project with `readOnly` and `noanalysis`;
its completion and change-discard log is retained. Export payloads remain
below 64 KiB. These are static verification results, not native runtime tests.

## Three different owners

The lookup record contains a constructor pointer at **record `+0x20`**. The
getter above returns this record; it does not instantiate the product object.

The previously inspected constructor `0x13844E0` initializes a separate
**product object**. At `0x13848EE` it loads the literal at `0x27CCED8`,
`Heroes of the Storm IPC Mem`, and at `0x13848F5` stores it in product field
**`+0x340`**.

A **mapped IPC buffer** would be a third owner. Its Switcher-side state/result
offsets `+0x20/+0x24` cannot be assigned to either object above. In particular,
the constructor-pointer slot in the record is not IPC state.

No mapping API, mapped-buffer pointer, state-3/result-3 consumer, constructor
invocation through the record, or downloader was recovered in this step.
The next concrete source is callers of getter `0x24C7F0` or consumers of its
cached record pointer `0x2FE32E8`, followed through the actual constructor call
and destination-object chain. No address of that next consumer is guessed.

The source inspection read 10,174,464 bytes from data sections. Including both
bounded PE-metadata passes, metadata plus data reads were 15,076,360 bytes,
below 16 MiB; the two complete PE hash streams are accounted separately.
No imports were inferred from the previously rejected import-directory metadata.

No game launch, Computer Use, IPC send, network request, replay read/write or
sync modification occurred. No 41810 payload was recovered. Full replay
upgrade and playback remain unproved. The public pair contains no raw PE,
raw ASM, private filesystem paths or unrelated native identifiers.
