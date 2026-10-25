# Numeric879: conditional baseBuild output layout

The selected static decoder route places the official wire field
`m_version.m_baseBuild` at **root output +0xA0**, using four separate little-endian
byte stores, under the normal decoding conditions below. The last local gate
was the native tag accessor: its contiguous-metadata branch now connects the
wire tags to the previously verified native field indices.

## Source and label authority

The source client is build **98348**, version **2.57.0.98348**, executable length
**53,573,840 bytes**, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction evidence comes from an **analyst-derived statically transformed
text patch**, **36,581,376 bytes**, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
Unaltered PE text and a runtime capture are not claimed.

Both pinned Blizzard schemas41810 and96477 identify header18 tag1 as `m_version`
(type11), then version11 tag5 as `m_baseBuild` (unsigned type6,32 bits).
This authenticates the official wire label. It does not recover a native C++
symbol name. The schemas are compared only along this selected field path.

## Native composition

| Selected metadata | Wire tag and index | Destination increment | Child |
| --- | --- | ---: | --- |
| Root879 | 1 | 0x98 | USER881, then STRUCT20 |
| STRUCT20 | 5 | 8 | USER28, then INT3 |
| INT3 | Accepted unsigned32-bit value | 0 | Four byte writes |

The tag accessor at `0x1A6D580` was decoded from109 captured bytes into34
instructions. For the signed-negative metadata header used here (`0x8E`), it
forms the lower bound plus the supplied index and checks that value with the
inclusive bounds predicate. Root879 and STRUCT20 have lower bounds zero and
upper bounds7 and5. Selected indices1 and5 therefore produce the corresponding
expected tags and a successful return.

The actual STRUCT matching-field route obtains the native offset and child type,
adds the offset to the parent destination, and calls decoder `0x1A76740`.
The observed BE32 metadata reader supplies the declared USER child ids. Those
wrappers add no destination offset under the stated conditions. The increments
therefore compose as **0x98 +8 =0xA0**. INT3's constructed unsigned range and
admitted leading count4 then select the previously proved four-byte storage
contract. The writes are separate byte operations; atomic DWORD storage is not
proved.

## Conditions and remaining scope

This result assumes a valid pinned1192-type context with matching stable program
and AUX data; valid nonaliasing metadata, reader, cursor, output and stack regions;
ordinary normal x64 helper behavior; and no wrap, exception or asynchronous
interference. The selected input is well formed and fully buffered, with all
selected declared fields present in ascending order. These conditions avoid
opaque refill, missing-field callback and unknown-field skip paths.

The109-byte tag selection ends at the last included RET. Its bytes and all five
relative control targets match the saved capture and IDA output; the analysis
process exited0. This is a selected-path argument, without a metadata function
extent or complete sparse-path claim. No target execution or emulation occurred.

The conditional per-field layout does not prove later header/caller/cache
ownership, object lifetime, unchanged propagation through later helpers, runtime
values, version/package acceptance, full replay conversion or playback.
The [sanitized observation](../observations/numeric879-basebuild-output-layout-2026-10-25.json)
records the fingerprints and boundaries. REA results and CI success are not
used as proof for this pair.
