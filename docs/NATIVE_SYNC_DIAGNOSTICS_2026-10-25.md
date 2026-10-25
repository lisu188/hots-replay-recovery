# Native sync diagnostics and recorded flag — 2026-10-25

The current client has a detailed replay-desync report, gated by bit3 of a
staging setup field corresponding structurally to Blizzard's
`m_clientDebugFlags`. The preserved R8 member contains `289` (`0x121`) in this
field, so its recorded value does not enable that bit. This is a new offline
observation, not an explanation proved for a particular runtime failure.

The companion receipt is
[`native-sync-diagnostics-2026-10-25.json`](../observations/native-sync-diagnostics-2026-10-25.json).
Addresses are RVAs in the pinned 98348 client. Static Ghidra analysis under
WSL used the existing project read-only. No Computer Use, HotS launch, native
target execution, replay write, settings change or synchronization change
occurred. R8 remains the latest replay and declares 98285. Full upgrade and
deterministic playback remain unproved.

## Diagnostic gate and actual recorded value

The native offset tables and retained staging getter establish:

| Native declaration | Child | Offset |
| --- | --- | --- |
| Root775 field1, tag−2 | USER777 → STRUCT684 | `C308` |
| STRUCT684 field2, tag−26 | USER687 → STRUCT649 | `418` |
| STRUCT649 field14, tag−2 | USER664 → INT648, u64 | `18` |

The field is root-relative `C738`. Getter `1324B80`, primary vtable slot
`1A8`, returns owner `G+3D8`; the field is therefore `G+CB10`. At `132C22F`,
the report routine tests `byte[G+CB10] & 8` and returns if clear. Its official
structural correspondence is
`m_syncLobbyState.m_gameDescription.m_gameOptions.m_clientDebugFlags`.
This correspondence supplies a useful name, not a recovered native symbol.

The retained copy path `CF96B0 → CF8310` copies this u64 unchanged: the outer
copy passes root `+C308`, then `CF8455/CF845C` copies description `+430`,
where `430 = 418+18`. A constructor also initializes an embedded setup field
at `+C738` to zero; this does not establish a live playback value.

One bounded read of preserved R8 extracted its 4,262-byte initData member
only in memory. The pinned native775 reader and the separate pinned Blizzard
96477 decoder independently returned **289** for this field. The complete R8
hash and stat identity matched before and after. No other decoded player
values or raw member bytes were saved. The original 41810 archive was not
opened in this check.

The diagnostic gate reads staging `G+CB10`. The separately committed setup
used by the CRC cache begins at `G+83F78`; its corresponding field would be
`G+906B0`. Equality between these instances during playback is unobserved.
Changing the recorded flag is not an established harmless diagnostic method:
it changes a serialized setup input and may change the committed setup CRC.
No flag was changed and no missing runtime value was inferred.

## Report contents, dispatch and frame history

Routine `132C210` reads current frame `G+A13BC`, the fold of current checksum
`G+A13C4`, the expected u16 passed in DX, an optional recorded state vector,
and computed history. It constructs a `Replay Desync` report, submits its
stack object through `27E2B0`, then frees temporary strings. The inspected
caller does not save expected checksum or first failing frame in a dedicated
persistent owner field. The mismatch byte at `G+79` is a flag.

Fresh complete selected listings show `27E2B0 → 27E710`. The dispatcher
invokes registered report callbacks when its global count at `3007FD0` is
nonzero, and has additional conditional reporting paths, including a global
byte at `3004140`. These callbacks, conditions, downstream sinks and actual
report persistence have not been authenticated end to end. In particular,
this is not proof of a diagnostic file in the visible GameLogs directory.
The separately retained named sync-log objects must not be treated as this
report's sink without a connecting path.

The frame tag in computed history is now bound statically. The initial
primary vtable at `27BC518`, slot `C8`, points to leaf `1327BF0`. Its first
eight reachable bytes decode exactly to `LEA RAX,[RCX+A13BC]; RET`; no absent
RuntimeFunction extent is invented. `132F610` calls this slot at `132F640`,
reads the returned dword at `132F64F`, and stores it in record `+0` at
`132F70E`. It later stores the computed folded checksum at record `+4` and
the counted vector at `+8`, with stride `410`.

This binds the frame counter within the authenticated initial-vtable path.
Live receiver/vtable identity is unobserved. The history count is advanced
before every record field is written, so an asynchronous memory snapshot is
not automatically a coherent record or the first failing frame. No runtime
sampler, capture, patch, injected code or client launch was added.

## What the checksum still requires

Fresh fragment `133D0C2` closes a missing producer instruction gap: initialize
a CRC sink to `FFFFFFFF`, call `133D350`, complement the result, store it at
setup `+1D438`, and set valid byte `+1D43C`. Combined with retained stream
analysis, the conditional cache formula remains
`CRC32(native775_serialized_bytes || four_zero_bytes)`. Identity between the
hashed runtime setup and recorded initData is still a separate question.

The aggregate frame check also depends on a prior checksum, queued inputs,
and engine object state. A fresh `1605540` export directly shows object `+2`
u16 hashing and a call on object `+68`; later retained expanded blocks show
indexed calls through descriptor helper `1601600`. These anonymous fields
are not assigned guessed gameplay names. This export is incomplete across
fragment boundaries: its selected interval has 32 instructions and its
expanded listing omits most of block `16055AC..16055DA`, despite the export's
size-limit flag being false. No complete object-hashing implementation or
offline replay-to-world reconstruction is claimed.

These findings identify a useful future diagnostic acquisition target. They
do not supply historical rules, the missing current player/resource values,
the first actual mismatch, or a new playable replay. Required next evidence
is an authentic coherent native mismatch report/state capture, or the exact
historical engine data sufficient to reconstruct that state. No expected
sync value may be replaced merely to bypass the comparison.

## Verification boundary

Three read-only Ghidra jobs produced four selected exports in this stage.
The receipt pins the selected listings, schema/offset sources, fixed vtable
cell, actual R8 observation and producer scripts. Required instruction and
value checks passed locally; independent review checked the gate mapping,
frame getter and report-dispatch limits. No new production codec or test was
added, and earlier passing codec CI is not relabeled as runtime proof.
