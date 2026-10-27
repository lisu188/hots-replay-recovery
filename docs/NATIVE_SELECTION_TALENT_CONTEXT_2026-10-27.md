# Selection-delta state and the talent callback's unit context

The selected current-native selection-delta callback now connects to the same
user row read by the talent callback. For bank10, `B61970 -> A286A0 -> 202DBC0`
updates the row returned by `A28B60`. The talent callback then asks for the first
unit matching the row's **dynamic active subgroup index**, not a literal tag2
or an automatically identified hero. This establishes a conditional native
producer/consumer address relationship. It does not reconstruct the actual
unit or owner selected at a recorded talent purchase.

## Dispatch, payload and row identity

Pinned official event IDs are28 for `SSelectionDeltaEvent`,29 for
`SControlGroupUpdateEvent`, and30 for `SSelectionSyncCheckEvent`. The existing
native binding for event28 supplies root303, original vptr `26643A0`, and
original root slot `27BEB7C`. Its two43-byte typed methods were freshly checked
against their original pointer cells and pinned transformed code.

Within the previously qualified conditional observer-switch suffix, header
`3001C` gives index14 after subtracting `3000E`, selector byte7 and case
`B5F7B0`. The case calls `B61970` at `B5F7BB`. The whole opaque dispatcher,
its earlier field preservation and actual execution remain unproved.

Original root303 layout has declaration-order offsets0 and8, corresponding
to control-group ID and delta body, at event `+30` and `+38`. The inner native
delta root has offsets0,4,30,F8 for subgroup index, removal choice, additions
of subgroup descriptions and additions of unit tags. Native negative STRUCT
tags are not equated to upstream tags: the selected bit-packed binding uses
declaration order and the matching scalar/struct shapes. The first scalar
fields and consumer offsets agree; this is not a whole generic-reader or
bit-array-to-memory transformation proof.

`B61970` reads event byte29 as the user, byte30 as the bank, and passes event
`+38` as the delta pointer. After its user-context gate, it calls `A286A0`.
That function reconstructs the same encoded base used by `A28B60` and chooses:

```text
bank < 10: row = base + (192 + 10*uint8(user) + uint8(bank)) * 1A4
bank >=10: row = base + (176 + uint8(user)) * 1A4
A28B60:    row = base + (176 + uint8(user)) * 1A4
```

The updater itself aliases every low-byte bank>=10 to the active row. The
wire declaration bounds the bank value to0..15. The operand-derived address
model checks96 active-row and160 stored-row cases over valid users0..15 and
banks0..15. This is static arithmetic reasoning, not target execution.

`A286A0` passes the selected row and delta to `202DBC0`. Its snapshot hooks
`A283F0/A27B50` are not fully audited for later state effects. Stable encoded
base, normal helper returns and valid row state remain explicit conditions.

## Dynamic subgroup selection

`202DBC0` removes entries according to the delta choice, processes subgroup
descriptions and unit references, then writes row byte2 at `202DD3A`:

```text
row[2] = delta.m_subgroupIndex if it is below row[1], otherwise 0
```

The prior talent callback `B612D0` loads that byte at `B612F0` into its query
tag. It passes capacity1 to `202ED90`, which scans unit DWORDs at row `+4+4*i`
and compares their per-unit tag bytes at row `+84+i`. The first match supplies
the handle used by the previously qualified pool/owner lookup. A missing or
invalid match retains the earlier documented fallback using event byte2A;
that field's effective runtime value is not authenticated here.

Two complete native API contexts query this same row getter on their valid
user branch. Original error-context literals are `UnitIsSelected` and
`UnitGroupSelected`. These names and the selection-delta producer support the
selected-unit interpretation. Native API export registration is not audited,
and alternate player-row branches are not treated as the serialized-user row.

Consequently, do not replace this state with a fixed hero list, match units
by hero name/nearest time, assume row byte2 has value2, or silently ignore a
nonzero subgroup index. The current code needs a selected unit/owner context;
the relevant row is mutable selection state.

## Effective data still needed

The insertion path resolves each subgroup's uint16 unit-link input through
leaf `5E1B70`. It uses global context pointer `3388B18`, table slot `+2A0`,
count `+90` and entry array `+A0`. A null slot or out-of-range index produces
a zero output reference; a valid context itself is a prerequisite. The leaf
returns the output-slot pointer, not a raw definition pointer as its return.

`202D910` then calls reference helper `201A490`, checks a reference condition
and row capacity32, reads a word at definition `+40`, and uses predicate helper
`993DA0`. Its subgroup descriptor conditionally incorporates unit-handle index
`>>22` or sentinel `3FF`. Effective table entries, definition values and
predicate outputs have not been captured. These helpers and native mask-memory
details still prevent claiming an exact subgroup/actor reconstruction from
wire values alone. No XML flag name, native RTTI class or historical rule is
invented for those dependencies.

## Fresh recorded coverage

The original and current tracker contents were freshly checked for unit-key
domains and explicit `PlayerSpawned` fields:

| Content | Unit index range | Recycle range | PlayerSpawned events | Explicit unit identifier in PlayerSpawned |
| --- | --- | --- | ---: | --- |
| Original41810 | 0..254 | 1..235 | 10 | None |
| Current98348 control | 0..97 | 1..193 | 10 | None |

Both fit the selected native handle domains and allocator index range. Each
PlayerSpawned integer-key set is only `PlayerID`; hero metadata is present,
but no explicit unit/tag/handle integer key was found. These finite observations
do not identify a live runtime object, justify a name-based unit association,
or infer a new tag packing or conversion.

Fresh full game-event reads cover the original, R8 and current control:

| File | Frames | SelectionDelta | Bank | Subgroup index1 | Talent selections |
| --- | ---: | ---: | --- | ---: | ---: |
| Original41810 | 104,257 | 158 | All10 | 5 | 70 |
| R8 partial | 104,257 | 158 | All10 | 5 | 70 |
| Current98348 control | 144,708 | 37 | All10 | 0 | 70 |

All remaining subgroup indices in those events are0. All three have zero
ControlGroupUpdate29 and SelectionSyncCheck30 events, so the exploratory
control-group-recall branch was not promoted as observed fixture coverage.
The original/R8 selections contain92 added-unit references each; current has24.
Each case references11 distinct unit-link values. Aggregate agreement is not
proof that the whole source/R8 payloads or simulation states are equivalent.

Original game contents use the pinned41810 grammar; R8/current use the native
98348 observed22 value codec. R8 still declares98285, and this decoding does
not validate that container or playback. Every replay/member hash and whole
input identity was checked. The earlier R8 tracker equality to the original
is retained; it is not a third independent tracker reference.

## Static verification and remaining boundary

Thirteen qualified ranges total **3,326 bytes / 821 instructions**. Eleven
complete original RuntimeFunction/CHAININFO unions and two branch-closed
no-call leaves supply their extents. The23-byte observer case is a separate
conditional window. Its99-byte selector and116-byte RVA tables are pinned
transformed data, not unchanged original PE bytes or full dispatcher proof.

All54 selected byte/call/reference checks, eight nonvolatile-register
definition/use checks and three required edges pass. Original native payload
pointer cells, accessor records, metadata, PE/transformed-text and replay/draft
pins pass. The fresh decodes add bounded recorded-data evidence; no production
codec/conversion change, unit tests, full corpus, hosted CI, peer review, REA
native-provider analysis or native target execution occurred.

Valid initialized metadata and row/base/definition state, stable pointers and
identities, disjoint storage, ordinary x64 ABI/helpers and no uncontrolled
exception/reentry/concurrent/alias changes remain conditions. Same user/fields
must survive the opaque dispatch path. An actual first selected handle, owner,
effective hero/talent catalog and successful event application remain unproved.

All work stays offline: no game, Battle.net, Computer Use, network, remote
refresh or publication. Original/R8/current replays and sync bytes are
unchanged. Full upgrade/playback remains false. Next resolve the exact
effective link/definition/predicate inputs or existing captures that can
justify subgroup construction before attributing a unit/owner to a purchase.
Historical41810 rules and native playback remain separate requirements.

Addresses and offsets are hexadecimal; event/type IDs, counts, numeric domains
and bank/subgroup values are decimal unless shown in the code formulas as
native address literals.
