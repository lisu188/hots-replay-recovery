# Selected command-context producers and the bit2 dependency

The extra context bit2 used by the current class2 target gate now has a bounded
producer route. The validator initializes its context flags to zero, retrieves
a separate callback from descriptor slot+40, and passes that context as the
third argument. Four selected registered providers either preserve/clear bit2
or delegate the same context. Under the stated family/alias conditions, a
returning invocation cannot change its initially zero bit2 to one.

This narrows the earlier hypothetical contextbit2=true escape in the selected
gate comparison. It does not authenticate a live descriptor, historical ability
identity or data value, prove command rejection/desync, or justify changing the
16 source exception flags. Production code, replay bytes and the generic gate
API remain unchanged. The instruction **Keep all work offline** remains active.

See the two dated `native-command-context-producer` observations for pins,
qualified ranges, fragment chains, finite checks and explicit limitations.
Addresses below are RVAs; +offsets describe object fields.

## Seed and callback selection

Within the previously qualified whole validator202AFB0, instruction202B2DD
zeros EDI. At202B390, DWORD[frame_RBP-11] is initialized from EDI. A local direct
control-flow check confirms that this zeroing dominates the store and that the
store dominates the later class2 read at202B49E. No explicit RDI/EDI/DI/DIL write
occurs between the zeroing and store; normal callee-preserved ABI behavior and
absence of alias writes are still required.

GetterA271F0 returns the pointer at descriptor + command_index*A8 +40 when the
index is in range and byte+8 is nonzero, otherwise null. At202B39D the caller
places the context base RBP-19 in R8; the flag word is context+8. Indirect call
202B3A9 is skipped for a null pointer. This is a separate slot from the target
class callback at+80, called later at202B473.

The already qualified slot initializerA27530 uses zeroed R9 atA27585 and stores
it to slot+40 atA27669. Selected builders for numeric types5/6 do not replace
that pointer. The current transformed-text scan finds exactly four direct
E8/E9 transfers to setterA27710, all decoded as actual E8 calls in these full
builder ranges:

| Numeric type | Builder | Command index | Context provider |
| ---: | --- | --- | --- |
| 9 | BA9A40 | 0 | BA59D0 |
| 11 | BC16C0 | 0 | BC2420 |
| 15 | C09790 | 0 | C09C10 |
| 16 | C0BB40 | 20..29 inclusive | C0C650 |

The scan covers the entire pinned transformed-text file. It is not a search
for every indirect transfer, direct memory alias write, later mutation or
instruction outside that artifact. The table describes selected constructor
assignments under normal initialization/copy behavior, not live memory.

## What the providers write

BA59D0 preserves the context on its early lookup-failure path. On its resolved
path it explicitly clears bit2, then sets/clears bit5 and later bit0. Its helper
201A490 receives the context address as RDX, but only reads its first QWORD.
Both key paths overwrite RDX before any call; the original context address is
not saved or forwarded. The output and other arguments must be disjoint from
the context. This is a bounded argument-flow result, not a proof against
arbitrary global/transitive aliases.

BC2420 preserves bit2 while setting bits0/1 and conditionally updating bit3.
C0C650 preserves it while ORing bit4 on a successful path; its other normal
paths leave the word unchanged. C09C10 has no local explicit flag-word write.
It uses A271F0 again, forwards the same context in R8 to a nested callback at
C09CAC, and leaves it unchanged on its local lookup failures.

Consequently, zero bit2 is invariant for a **finite returning delegation whose
nested callbacks all belong to this selected family or are null**, with valid
disjoint objects, normal ABI and no other alias writes to the context. This is
an inductive property of those operations. Unknown live descriptors, modified
callback slots, outside-family functions, nonreturning recursion and historical
applicability remain outside the claim. Other callbacks between this producer
and the gate are also subject to the no-alias-write condition.

## Consequence for the original command shapes

The prior pinned source-context observation contains61 commands for historical
links126/351:45 Unit/0x100 and16 None/0x80100, all command index0. Its receipt is
reused here; no new source stream decode is claimed. Lengths and SHA-256 pins
of the original, R8 and current control were freshly rechecked unchanged.

With a shared callback class0..3 and zero contextbit2, the existing selected
gate has no class that passes both shapes. The earlier class2/contextbit2=true
possibility is therefore not supplied by the selected producer family under
the conditions above. This remains conditional: the actual historical/current
type, callback, data-field values and stability of the class between commands
are unbound. The source links are not assigned to numeric types9/11/15/16 or
5/6 by this analysis. Do not replace their flags or label them self-casts.

## Static validation

Original PE authority is53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction authority is the separate analyst-transformed text,
36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
It is not unchanged signed PE text or a runtime capture. Local GNU objdump
and Python were used without native target execution or a new REA/IDA claim.

Fifteen selected ranges, including reused builder/initializer/setter code,
cover3,705 bytes and932 instructions. Every byte matches the pinned transformed
text. Direct noncall branches have internal decoded destinations except three
explicit builder tails to separately qualified settersA27780/A277A0/A27810.
BA59D0, BC2420, 201A490 and the reused slot initializer each have three original
RuntimeFunction fragments joined by CHAININFO. The prior whole validator is
separately rechecked at1,467 bytes/393 instructions with its original code hash.

A restricted interpreter checks four branchless flag-update fragments using
their actual opcode bytes: clear2/update5, update0, set0/1/update3, and set4.
All1,820 finite cases agree with the formulas and bit2 effect, including
high32-bit input flags and partial-register ZF behavior. Explicit byte-whitelisted
stack restores/address calculations are ignored only when irrelevant to that
fragment's flag-word result. This is not full callback execution, a general
emulator or an exhaustive32-bit run. Four gate-class comparisons use the
unchanged portable model.

No new unit tests were authored or rerun for this evidence-only change. No
broader corpus, hosted CI, peer review, client, Computer Use, network or remote
publication occurred. Original/R8/control/sync and unused launcher drafts remain
unchanged. Full upgrade and deterministic playback remain unproved; the next
dependency is authentic ability/type/data evidence for the two source links.
