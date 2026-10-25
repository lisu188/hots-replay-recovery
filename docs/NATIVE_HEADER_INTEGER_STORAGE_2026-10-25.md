# Native header integer storage: static contract

The decoded entry at RVA `1A79150` has a byte-counted integer-store loop. With
an input count of four, it produces the low 32 bits of the supplied value as
four separate byte writes in little-endian order.

## Source identity and analysis scope

The source client is **2.57.0.98348**, executable length **53,573,840 bytes**,
SHA-256 `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction analysis uses an **analyst-derived static text patch** of
**36,581,376 bytes**, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
The patch is a derived analysis artifact; unaltered PE text and a runtime memory
capture are not claimed. IDA performed static decoding without executing the
HotS client or the analyzed code.

A 64-byte window was loaded, and decoding stopped at the first RET. The emitted
prefix is **34 bytes / nine instructions**, ending at exclusive RVA `1A79172`.
Both conditional targets stay inside it: `1A79153 -> 1A79171` and
`1A7916F -> 1A79160`. There are no calls or outside direct targets. Inspection of
all branch and fallthrough edges establishes a closed entry-reachable graph
with a RET exit under the assumptions below. Loaded bytes after that RET were
not analyzed.

This graph result does not authenticate a metadata function extent. The selected
RuntimeFunction floor `[1A78F10,1A79109)` does not cover `1A79150`; the lookup
also makes no global claim that a covering metadata record is absent.

## Storage contract

Let `V` be the initial unsigned 64-bit value in RCX, `n` the count in RDX, and
`D` the destination in R8. A zero count reaches RET without a destination write.
For a nonzero count, each iteration stores the low byte, advances the destination
by one, shifts the value right by eight, and decrements the count. Thus:

`M_after[D+i] = (V >> (8*i)) & 255`, for `0 <= i < n`.

Bytes beyond the low 64-bit value are zero. For `n=4`, the four final bytes at
`D..D+3` are the little-endian low-32-bit representation. RDX becomes zero,
R8 becomes `D+4`, and RCX becomes `V>>32`. The observed memory instruction is an
8-bit store used four times; a single MOV DWORD instruction and atomic four-byte
storage are not established.

The contract assumes stable decoded code, no exceptions or asynchronous
interference, an ordinary valid writable destination range without address wrap,
no overlap with executing code or return-control storage, and a valid normal
x64 call/RET stack.

## Conditional INT3 composition

The caller at RVA `1A76CF9` supplies RCX from the value in RBX, R8 from the current
request destination, and RDX from `P[0]`, where `P=[descriptor+0x20]`.
A guarded **16-byte metadata read** from the identified source PE observed
INT type 3's AUX array slot **4** contains QWORD **1198**. That table-word
index selects RVA **27C1220**, whose leading QWORD is **4**. All 16 recorded identity comparisons matched.

That observation supplies a static count-of-four composition only when the
active context/type selects this auxiliary table and the context/AUX data and
descriptor pointer retain their binding through opaque initializer subcalls,
`1A77FF0`, stream-refill and integer-value helpers until the count load. A live
RDX value of four and unconditional descriptor stability were not observed.

Native baseBuild or other named-field binding, whole-header compatibility,
full replay conversion, and playback remain unproved. The accompanying
[observation](../observations/native-header-integer-storage-2026-10-25.json)
records the source fingerprints and these scope boundaries without raw code.
