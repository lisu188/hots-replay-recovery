# Unit-owner assignment and the talent selector

The callback's selected field44 now has a static unit-owner binding: wrappers
whose original error-context names are `UnitSetOwner` and
`UnitSetOwnerPreserveUpkeep` resolve an object from the same pool and forward
their new-owner argument to a routine that writes that byte. The talent
callback reads the same offset from a pool-resolved object and passes it as
the first selector to the talent writer.

The initial assignment is also located. A successful pool-creation path calls
an initializer that writes the low five bits of creation-input byte10 to
object+44. Actual creation inputs and effective owners were not captured.
This does not bind the replay's user ID or tracker player ID to the native
owner index, or authenticate a historical/current talent-index mapping.

The two dated `native-talent-owner-assignment` observations contain the pins
and validation. Addresses and structure offsets below are hexadecimal unless
explicitly described as decimal counts.

## Initial assignment after pool allocation

Creation routine996D90 preserves its incoming RCX in RDI. On its successful
allocation path,996FB8 calls990AF0,996FBD saves the returned object in RBX,
and997054/997057 pass the creation-input pointer and object to9BAEF0 at99705A.
This connects the earlier default16 initializer with a later selected setup
path. It does not prove the creation path actually runs for a recorded event.

9BAEF0 preserves its object in RBX and its second argument in R13. At9BB030,
RDI becomes creation_input+10.9BB052 loads its byte,9BB057 masks CL with1F,
and9BB05A writes CL to object+44. The value is read at that point after earlier
helpers; an immutable entry-time snapshot of the creation data is not claimed.
The wire/source field that produced those creation-input bits remains unknown.

The code interval9BAEF0..9BBDB8 is3784 bytes/939 instructions. Two embedded
64-byte RVA tables follow, ending at the original RuntimeFunction end9BBE38.
Their32 targets are instruction boundaries and are expanded separately in
the static graph. The tables are not counted as instructions.

## Named owner setters and the shared object pool

| Original error-context name | Literal RVA | Wrapper entry | Tail call |
| --- | --- | --- | --- |
| UnitSetOwner | 29ABCB0 | 2055CE0 | 2055D23 to9BC080 |
| UnitSetOwnerPreserveUpkeep | 29ABCC0 | 2055E00 | 2055E43 to9BC080 |

Each wrapper saves the second argument, resolves the first through64BAD0,
requires a nonnull result, and checks the second argument as an unsigned
integer0..15. It forwards that low byte in EDX, the resolved object in RCX,
and additional flags to9BC080. The precise effects of those flags are not
inferred from the names. The error-context name/argument/tail path is checked;
the API registration/export lookup was not audited.

64BAD0 is a98-byte no-call leaf with both early-failure and success RETs. It
loads a handle from the first argument, rejects invalid forms/out-of-range
slots, decodes a block pointer using slots34F02C8 and keys32C38B4/32C55D0,
uses stride2F0 and checks the full handle against object+10. These are the
same pool/identity operations as callbackB612D0. This is a static object-pool
binding, not a captured live object or native class RTTI name.

9BC080 retains its object in RDI. Its first instruction saves incoming DL at
entryRSP+10. The frame relation RBP=entryRSP-238 makes RBP+248 the same byte.
At9BC526 it loads that byte, and9BC530 writes it to object+44. Earlier paths
and callbacks have conditions; no claim is made that every invocation reaches
this store. The two checked wrapper paths restrict their owner argument to
0..15; other internal callers are not assigned a universal bound here.

## Owner-slot address escapes

The owner byte's address is passed to helper201A590 at three sites before the
selected store. Treating the absence of explicit local stores as sufficient
would leave an alias gap. The complete12-byte helper reads BYTE[RDX] and sets
only the low five bits of QWORD[RCX], preserving its other bits. It writes no
input byte, makes no call and does not let the input pointer escape. With
disjoint targets and owner storage, those three calls preserve the saved byte.

There is another pointer escape at9BC8E6 to201CE30 after the selected store.
Its input-readonly behavior is unproved. The normal graph from that site
cannot revisit9BC530, so it does not invalidate the value-flow proof at that
store. Final persistent object state, reentry, later alias writes and every
helper's gameplay effects remain outside this proof.

## Consequence for talent selection and validation limits

B612D0 reads resolved object+44 atB61370, copies that byte to ECX atB61397 and
calls B10720 atB6139A. In the checked naming/pool context, the first selector
is therefore drawn from the resolved unit-owner field. Its fallback still
uses event+2A. The preceding stages already proved the selected writer admits
only a first low-byte selector0..15 and requires an empty tier cell along with
other conditions.

This strengthens the native owner/selector interpretation. It does not prove
that the serialized user, native owner and tracker player identifier share
values or a constant offset. Do not introduce user+1, owner+1, a talent-index
replacement or a current effective catalog from this finding. The native
dispatcher path and intermediate event-field preservation remain incomplete.

Eight code ranges total8089 bytes/1933 instructions, plus128 bytes of switch
data.54 selected instruction/call/reference checks, eight definition/use
dominance checks with no conflicting explicit nonvolatile-register writes on
relevant paths, and four required wrapper-edge checks pass. Complete original
RuntimeFunction/CHAININFO unions, the split code/table region and two bounded
no-call leaves are recorded separately. Every selected byte matches the
pinned analyst-transformed text; original PE metadata/names are separate.

Helpers must return normally and follow Windows x64 ABI. Valid disjoint
input/object/stack storage, stable handles/keys, and no exception, reentry,
concurrent or alias mutation are required. These checks do not execute native
code, prove the bootstrap transform parameters at runtime or observe gameplay.

Original/R8/current replay and unused-launcher hashes remain exact. No fresh
event-stream decode, conversion/production/replay/sync change, new unit tests,
broad corpus, hosted CI, independent peer review or REA native analysis was
performed. All work stays offline; full upgrade/playback remain false. Next
bind the native owner to recorded player/setup/ownership data through an
authenticated producer, then obtain the effective/historical talent rules
needed for a safe migration.
