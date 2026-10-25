# Native header postdecode checks

The selected header parser performs two checks after decoding: a comparison at
`0x134DD06` and a decimal-suffix check at `0x134DD13`. The comparison's zero-flag
route and the suffix helper now have closed selected entry graphs. Entering
these checks with the field intact at header `+0xA0`, the valid zero-flag route
preserves that word through the previously proved transfer into temporary `T+8`,
under ordinary disjoint caller stack/input conditions. This does not newly prove
the path from the selected leaf store to postcheck entry: common core epilogue
`0x1A77255` and later root-field handlers were not newly decoded. It also does not
observe the global flag value or establish the later gate/cache chain.

## Comparison routes

Entry `0x1A3DFEC` tests global DWORD at RVA `0x3B5A004`. When it is zero and the
inputs are nonnull with count at most `0x7FFFFFFF`, the observed normal route
tail-calls `0x1A3DF90`. That selected entry is **92 bytes /30 instructions**, with
five relative edges to included instruction boundaries and no calls. It reads
byte pairs, folds ASCII uppercase letters to lowercase in registers, and returns
their difference when count ends, the first folded byte is zero, or a mismatch
occurs. Count zero returns zero. Its sole memory write saves RBX in the ordinary
caller home slot at entry stack `+8`; it writes neither input region.

The nonzero-flag route clears its fourth argument and tail-calls `0x1A3E03C`.
Its selected **218 bytes /63 instructions** contain twelve internal noncall
edges and six calls. Positive count first calls `0x1A36598` with a local
descriptor address and zero. A context property selects the verified fast
comparison or byte-by-byte calls to `0x1A36AA8`. Those calls receive a byte value
and descriptor `+8`, rather than either input pointer. The observed normal
writes are register saves on the stack and, when a descriptor flag is set,
clearing bit 1 in a DWORD at the descriptor's context pointer `+0x3A8`.

Valid context objects disjoint from the header make that direct context write
safe for header `+0xA0`. Preserving the header across the two opaque hooks also
requires their writes to remain within the descriptor/context domain. This is
a specific conditional context contract, not a result derived from ABI or
address disjointness alone. The remaining source-backed contracts are
`0x1A36598` and, for the byte-mapping branch, `0x1A36AA8`. No native or standard
library symbol names are assigned. Invalid-input error paths are excluded from
these normal valid-input conclusions.

## Decimal suffix and scope

Entry `0x133C440` receives header `+0x10`; its caller requires return value **11**.
Its selected **112 bytes /39 instructions**, including two returns, have eight
internal relative edges and no calls, indirect branches or memory writes. For a
valid readable NUL-terminated input, it returns the final contiguous ASCII
decimal suffix modulo `2^32`, or zero if no trailing digit run exists. It
preserves the decoded header on this selected normal route.

The original client is build **98348**, version **2.57.0.98348**, length
**53,573,840 bytes**, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction evidence comes from an analyst-derived statically transformed text
patch of **36,581,376 bytes**, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
Unaltered PE text and runtime capture are not claimed.

Both comparison analyses exited zero; captured windows were 128 and512 bytes.
The closed local branches are selected entry-route evidence, without a whole
function-metadata or whole-engine CFG claim. The global flag/context values were
not observed at runtime. Later `0x134D9D0`, gate helpers, callback, object-instance
continuity and controller cache remain separate. No full replay upgrade,
playback or CI success is established. The
[observation](../observations/native-header-suffix-check-2026-10-25.json)
records fingerprints and these boundaries.
