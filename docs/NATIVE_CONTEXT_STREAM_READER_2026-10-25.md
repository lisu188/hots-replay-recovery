# Native context reader: authenticated stream direction

The bounded static expansion of build 98348 entry `0x9D99E0` establishes a
stream-to-context population route. Its original `RCX` is retained as the
stream argument, and the selected code passes that argument to sixteen context
reads. The concrete replay member or caller that supplies the stream remains
unidentified. This observation does not supply historical ownership data or
establish that the stream is the replay's access matrix.

IDA decoded **984 bytes and 236 instructions**, ending at RET `0x9D9DB7`.
The capture also contains two 64-byte dispatch tables after that RET. Each
table has sixteen entries; all 32 targets resolve to actual instruction starts.
The indexed loads and jumps are guarded by unsigned indices no greater than 15.
All 41 relative calls and 39 relative non-call targets were recomputed from the
captured bytes. The resulting local graph is closed under ordinary returning
calls and stable metadata; exceptional paths and the called routines remain
separate contracts.

The selected source shows the following distinct boundaries:

| Location | Observed behavior | Remaining contract |
| --- | --- | --- |
| `0x9D9A21` | Calls `0x9D6690(context, stream)` for indices0 through15 | Saved callee evidence supports reading scalars into context fields; its full input backing remains unknown |
| `0x9D9A3D` | Calls `0x9D8970(stream, global0x35C92E8, 5)` | This next callee is not expanded here |
| Later selected body | Visits sixteen global record slots at `0x35C9B00`, stride17 bytes; conditionally fills each first byte | Buffer-transfer and short-input semantics remain separate |
| Final selected reads | Conditionally writes two byte globals and one DWORD global | Null scalar pointers skip their direct stores; aggregate success is not proved |

The reader-direction evidence combines the new call site with pinned saved
instructions for `0x9D6690`: that callee requests scalar spans, loads from
nonnull returned pointers and stores into context fields. This is a direction
and argument proof, not a claim about actual runtime bytes, player entitlements
or a historical identifier mapping.

The source PE fingerprint is
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`
at 53,573,840 bytes. Instruction evidence comes from the existing analyst-derived
statically transformed patch, inherited SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
It is not runtime capture or unaltered PE text. This selection read 216 bytes of
PE exception metadata and 1112 patch bytes, with matching source identity guards.
No game or target code was executed.

The successful native run used a fresh empty IDA database and a decoder that
stops at the first RET. Four earlier failed attempts remain preserved locally,
including a fixed-span attempt that tried to decode the post-RET table data.
The successful TSV and quality report total 29,345 bytes, below the 48 KiB cap.
Source fingerprints, precise table boundaries and limitations are retained in
the [observation](../observations/native-context-stream-reader-2026-10-25.json).

This milestone changes no codec, replay, player value or synchronization data.
The next concrete targets are `0x9D8970` and the upstream constructor or caller
supplying the stream. Full historical conversion and playback remain unproved.
