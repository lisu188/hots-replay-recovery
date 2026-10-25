# Main IPC bulk request source and non-1 fallback - 2026-10-25

AB90 passes a caller-supplied request block to a copy helper for the returned
buffer, then tail-calls the generic request routine. The selected caller CFB680 constructs
that block, writes a numeric type and a sentinel locally, and invokes the
known AC30 fallback for every return value other than 1, including 3. No
concrete historical-build request or downloader is established by this result.

The [companion observation](../observations/main-ipc-bulk-request-fallback-2026-10-25.json)
records addresses, source fingerprints, conditional copy semantics and the
failed export-size guard. Addresses below are RVAs. The pinned 98348 source
is 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.

## Bulk source forwarding

The [protocol-handler result](MAIN_IPC_PROTOCOL_HANDLERS_2026-10-25.md)
identified generic routine `0x115ADE0` and its result-3 return path. Newly
selected record `0x115AB90..0x115AC2B` preserves its first argument in RDI
and second argument in RBX. It attempts state 0 to 1 through helper
`0x115A0B0`, then checks that signed DWORD `buffer+4` is at most 1. Failed
claim or guard paths return 2; the latter clears state first.

On the forwarding path, the call at `0x115AC14` supplies:

| Argument to `0x1A2B250` | Selected-ASM source |
| --- | --- |
| Destination RCX | Returned-buffer pointer from global `0x37EBC48`, plus `0x30`. |
| Source RDX | AB90's original first argument. |
| Count R8D | `0x4180`. |

The tail jump at `0x115AC26` enters `0x115ADE0` with AB90's original second
argument in RCX. AB90 has no local post-return handler for result 3.

## Caller-local stores and their limit

The selected caller is `0xCFB680..0xCFBDB6`. Its incoming RCX is retained in
RDI as an owner pointer; incoming RDX is retained in R15 as an output-object
pointer. At `0xCFBC80` it places local request address `RBP+0x360` in RCX,
then calls AB90 at `0xCFBC8F`.

| Local request slot | Explicit selected instruction |
| --- | --- |
| `input+0x18 = RBP+0x378` | `0xCFBA10` stores ESI, derived from owner DWORD `+0x100E8`. Numeric mapping: 1 to 2; 2 to 3; 3 or 4 to 4; other values to 1. |
| `input+0x1C = RBP+0x37C` | `0xCFBA16` stores `FFFFFFFF`. |

The owner and numeric values have no authenticated semantic names here;
CFB680 is not established to be replay-specific.

The sentinel store is a concrete instruction, but it is not proof of the
value at copy entry. The request pointer had already been passed to opaque
helper `0xCFFD10` at `0xCFB997`. Eleven opaque calls intervene between the
store and AB90. No direct rewrite of the same literal local slot appears in
selected ASM, while complete alias and helper contracts are unavailable.
AB90's preceding claim and `buffer+0x8044` helper call add another boundary.
Runtime values and opaque helper effects were not observed.

## Narrow fixed-count transfer contract

Retained selected and expanded text for `0x1A2B250` supports a conditional
contract for count `0x4180` and source byte offsets 24 through 31. Those
bytes are transferred as two DWORDs:

- `input+0x18` to `buffer+0x48`;
- `input+0x1C` to `buffer+0x4C`.

The source snapshot is **at entry to the copy helper**, after AB90's earlier
calls. This uses the retained forward SSE, backward SSE and REP paths for
that fixed count. It does not establish global all-count memmove parity.
The transfer requires the guarded copy path, valid readable/writable ranges,
nonwrapping extents, normal completion and no concurrent mutation. The REP
path additionally requires a clear direction flag. Its retained expanded
tail lies outside the original selected RuntimeFunction; this step did not
perform another native authentication of that tail.

These conditions do not prove that caller-local `FFFFFFFF` remains unchanged
until copy entry. No actual payload bytes, concrete requested build or 41810
request were observed.

## Actual handling of returned 3

The caller compares AB90's return value with exactly 1 at `0xCFBC94`.
Equality skips to `0xCFBCD7`. Every non-1 result, including 3, reaches the
call to `0x115AC30` at `0xCFBCD2`. The earlier selected AC30 path constructs
the type-1/sentinel fallback. There is no distinct comparison with 3 here,
and this caller does not check AC30's return value before common cleanup.

On the normal common path it calls unresolved helper `0x2923D0`, writes
QWORD 0 and DWORD 9 at output-object offsets 0 and 8, and returns that object
pointer. No downloader or old-client acquisition branch was identified.

## Boundaries and failed export-size guard

| Selected RuntimeFunction interval | Bytes | Selected / expanded instructions | Outside blocks |
| --- | ---: | ---: | ---: |
| `0x115AB90..0x115AC2B` | 155 | 37 / 97 | 15 |
| `0xCFB680..0xCFBDB6` | 1,846 | 407 / 406 | 0 |

Both Ghidra jobs completed with `readOnly`, `noanalysis`, two CPUs and
recorded discarded changes. Neither expanded export was size-truncated.
Outside blocks and differing instruction counts remain explicit; opaque
interprocedural effects are outside this local proof.

The planned combined native export bound was **65,536 bytes**. Actual native
exports were 11,330 bytes for AB90 and 64,443 bytes for the caller, totaling
**75,773 bytes**, an excess of **10,237 bytes**. This size guard **failed**.
The result was preserved; no retry and no second-caller export followed.
Successful decompilation does not establish compliance with that guard.

One bounded E8/E9 scan found two raw E8 candidates and no E9 candidates for
AB90. One source identity hash stream and 2,450,948 bytes of headers/`.pdata`
authenticated both caller bounds before selection. Only CFB680 was selected;
no import or data-section scan was added.

The next retained candidate is `0xCFC16A..0xCFC7B0`, 1,606 bytes, with raw
call site `0xCFC660` targeting AB90. It remains unexported and its semantics
are unproved. A concrete non-sentinel build producer and any acquisition
path beyond the selected fallback remain open.

Execution counters cover `static_native_analysis_lane`: no client/game
execution, Computer Use, IPC send, network request, replay read/write or
sync change occurred in this lane. Full replay upgrade and playback remain
unproved. Raw PE/ASM and private filesystem paths are excluded from this pair.
