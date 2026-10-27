# Replay version helpers inspected with REA and IDA

The client-98348 loader's numeric comparison uses an authenticated literal
**98348**, but a mismatch at that comparison is not an unconditional rejection.
The caller can continue through a separate legacy classifier and data check.
This narrows the native acceptance rules; it does not establish that the old
TEN_GREYMANE replay passes them or that changing its version fields is valid.

The paired [observation](../observations/replay-version-helpers-rea-ida-2026-10-27.json)
records five actual REA/IDA dossiers and independent instruction checks. All
addresses below are RVAs relative to image base `0x140000000`.

## Selected rules

The earlier [CFA810 caller analysis](REPLAY_VERSION_VALIDATION_GATE_2026-10-25.md)
left four helper contracts unresolved. The new selected listings establish:

| Helper | Selected normal-path behavior | Caller consequence |
| --- | --- | --- |
| `271C60` | Return byte `[T]` masked with `1`. Its complete selected entry route is six bytes, three instructions, with no call or memory write. | A zero result makes `CFA810` return `0x15`. |
| `271B50` | At `271C2A`, compare DWORD `[T+8]` with the value saved in R8D from the call at `271BD0` to `1EEEAE0`. Also evaluate the supplied 16-byte value against a global value and a conditionally populated local value. | A true result skips the legacy classifier; a false result enters it. The boolean is also copied through caller argument 5. |
| `271CE0` | Call `262F90` with a local descriptor. If DWORD at its returned pointer is `0x7A68434E` and unsigned `DWORD[T+8]-1 <= 0x46AA`, return `1`. Otherwise return `3` when byte `[T+1]` is zero and byte `[T+2]` is below `12`; return `0` on the other selected normal route. | The caller maps `1` to `0x14`, `2` to `0x16`, and `3` to `0x18`. A zero result continues. The selected helper itself has normal returns `0`, `1` and `3`. |
| `2719B0` | Consult external functions/global state, compare the supplied numeric value, and inspect a supplied 16-byte value; the selected routes return `0`, `1` or `2`. | The caller rejects only zero here, returning `0x17`. Both nonzero values continue. |

The independent six-byte entry route at `1EEEAE0` returns EAX **98348** and
then returns, without calls or memory writes. Its bytes were checked directly
against the pinned transformed patch and decoded with ordinary GNU objdump.
It is an additional static check, not a sixth REA dossier.

After the helper gates, the retained caller still rejects numeric `[T+8]`
values **73016**, **79155** and **79515** with `0x18`; other values reach its
zero return. An observed false result from `271B50` alone would therefore be
insufficient to explain rejection. Runtime helper results and the actual
structure presented by the replay loader have not been observed.

These statements apply to the selected instructions and normal returns.
External helper effects, global values, object aliases, exceptions and later
playback paths remain outside the recovered contract. No error names, global
hash meanings or named header-field binding are inferred from numeric offsets.

## Analysis identity and verification

The original installed PE is 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
The analyst-derived transformed text is 36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
Both were hash-verified when building the small analysis input.

REA 6.8.0 with its IDA adapter analysed a new **9,216-byte PE carrier**, SHA-256
`ef334e3631913404f906d2640b1270c5c99475ce68ecda86877c56f1ea050d9e`.
Its PE headers are analyst-authored. Its only source payloads are two exact
4,096-byte transformed-code windows at `[271000,272000)` and
`[CFA000,CFB000)`, mapped at their original addresses. External code/data,
exception metadata, original loader context and unaltered original PE text
are not supplied. This carrier was never executed and must not be used as a
game client. No full client import or shared IDA session was used.

The five selected listings contain **733 bytes / 213 instructions**. Independent
GNU objdump decoding matched every IDA instruction address and every selected
byte. All selected direct noncall branch targets are included instruction
boundaries, and the selected ranges end at RET. Four ranges also match exact
original RuntimeFunction entries. The six-byte `271C60` route has no covering
record in the inventoried `.pdata`; it is not assigned an original function
extent. IDA's adapter does not expose complete body ranges or a typed CFG.

All focused identity, byte, boundary, relative-call and branch assertions passed.
This is structural verification by one agent, without independent peer review
or a new production-code test run. The five REA dossiers were exported before
graceful close returned `cleanup_incomplete`: the upstream registry did not
confirm worker release. The private workspace was retained. The owned Windows
Job subsequently had zero active processes, without forced termination. The
run took **10.063 seconds** and monitored workspace usage peaked at **196,703
bytes**; filesystem monitoring is not a hard quota or a measurement of every
external engine effect.

No Computer Use, HotS launch, target-code execution or replay modification
occurred. R8 remains `98285-resumable-r8`; synchronization data and both false
full-upgrade flags remain unchanged. Complete conversion and playback are still
unverified.
