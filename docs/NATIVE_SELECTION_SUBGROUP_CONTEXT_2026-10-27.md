# Selection initialization, subgroup comparison and recorded talent context

Every recorded talent purchase in each of the three pinned game streams has
an earlier SelectionDelta for the same wire user. The selected native allocator
also supplies an explicit initialization route for the active rows used by
the talent callback. The subgroup comparison order is now byte-qualified.
Together these results narrow the reconstruction problem; they do not prove
the actual row, selected unit, owner or catalog values at a purchase.

## Recorded user coverage

The original 41810, partial R8 and current 98348 control game members were
freshly read to exhaustion with their pinned grammars and whole-file hashes.
Each has ten wire users 0..9 with seven talent selections apiece. Every one of
the 70 talent records has an earlier same-user SelectionDelta. No talent-only
user or purchase without such a prior record was found in these finite inputs.

The first recorded selection of every user has bank 10, subgroup index 0,
removal variant None, one added subgroup of count 1, and one added unit.
The original/R8 first selections occur at loops 52..84; the control's at
647..687. **None does not clear an unknown earlier row.** These records alone
therefore do not prove that the resulting native row contains only one unit.

The latest recorded same-user selection before each talent has subgroup
index 0 in all three streams. Its other aggregate context is:

| Content | None, one added unit/group | ZeroIndices, one added unit/group | Mask, no additions |
| --- | ---: | ---: | ---: |
| Original 41810 | 53 | 11 | 6 |
| R8 partial | 53 | 11 | 6 |
| Current 98348 control | 64 | 0 | 6 |

This is a lookup of the latest preceding recorded delta, not a reconstruction
of the cumulative row. The earlier five nonzero subgroup-index events in the
original/R8 remain relevant to intermediate state and cannot be discarded.
No name-based unit association or assumed owner mapping is introduced.
R8 still declares 98285; decoding its contents with the native 98348 grammar
does not establish a valid 98348 replay or playback.

## Native allocation and row initialization

`A28C90` requests `24180` bytes from `1372530`. On its non-null branch it passes
the allocation, zero fill argument and that size to `1A2B6C0`, then initializes
rows with stride `1A4`:

| Row indices | Direct construction route |
| --- | --- |
| 0..15 | first 16-iteration loop calling `202D680` |
| 16..175 | `A28370(base+1A40)`, nested 16 by 10 iterations |
| 176..191 | second 16-iteration loop starting at `base+120C0` |
| 192..351 | `A28370(base+13B00)`, nested 16 by 10 iterations |

The latter two ranges match the previously qualified active-user and stored
bank address formulas. Sixteen address cases verify that the active loop's
row for user u is exactly `(176+u)*1A4`, also used by `A28B60`.

`202D680` directly writes WORD `[row]=0`, clearing both unit and subgroup
counts, and BYTE `[row+2]=0`, clearing the active subgroup index. These stores
precede calls to `202D3C0(row+A4)`, `1A2B6C0(row+4,0,80)` and
`1A2B6C0(row+A4,0,100)`. Their complete memory effects are not audited in this
checkpoint. Preserving the count/selector result through those calls requires
their intended bounded, disjoint memory contracts and normal returns.

The allocator publishes the pointer through the same encoded base globals
read by the active-row getter: low 32 bits XOR key `32C55D8`, high 32 bits
NOT plus key `32C2ED0`. Stable keys decode the published value back to the
allocation. The allocation-failure branch publishes encoded null.
`A29420` decodes that same base, calls `1A24B90` and publishes encoded null.
Thus an initialization route exists, but retained valid state must still be
established at the actual consumer. This audit does not show that either
initialization/reset function ran, or exclude later mutation and snapshot
effects before the first recorded selection.

## Subgroup comparison

The insertion path passes its row, descriptor and output-index slot directly
to `202E600` at `202DA17`. The helper scans descriptors at `row+A4+8*i`, using
the subgroup count at row byte 1. Its unsigned lexicographic order is:

| Descriptor field | Width | Order |
| --- | --- | --- |
| `+4`, selected subgroup priority | byte | descending |
| `+0`, first definition WORD `+40` | word | ascending |
| `+5`, selected intra-subgroup priority | byte | descending |
| `+2`, conditional unit index or `3FF` | word | descending |

The helper continues past negative comparisons and stops at the first
nonnegative comparison. It writes that index and returns AL=1 only for a
match of all four fields there; otherwise AL=0. If it reaches the end, the
output index is the current subgroup count. With subgroup count zero, it
writes index 0 and AL=0 without reading incoming descriptor fields.
`202D910` uses the returned match flag to choose the existing-group or new-group
branch. This does not by itself implement all insertion, removal and ordering
effects across a replay.

The exact comparison key preserves the prior definition-data dependency.
It uses the resolved definition's word, not an assumed equality to the wire
unit link. The predicate-derived component remains dependent on the second
resolved object's byte DD bit 5. Actual table entries, object values and
successful insertion are not captured here.

## Verification and remaining boundary

Seven qualified ranges total **1,610 bytes / 375 instructions**. Six complete
original RuntimeFunction/CHAININFO unions and one branch-closed no-call leaf
provide their extents. Five newly decoded complete functions account for
876 bytes / 201 instructions; the insertion and active-row lookup ranges were
already qualified. All 98 selected instruction/call/reference checks, seven
nonvolatile-register definition/use checks, two required edges and four
unsigned comparison flag-preservation paths pass. Original PE and transformed
text pins remain separate authorities.

A filename-only search including ignored/hidden files found zero matching
`.dmp`, `.mdmp`, `*memory*.bin` or `*catalog*.bin` files beneath the task's
`work` directory. This is only that workspace search, not a global absence
claim or a new examination of previously exhausted historical dump routes.

Python and GNU objdump under WSL supplied static evidence; no REA native
provider or native target execution occurred. Fresh game-event decoding and
replay/draft hash checks were completed. Production conversion code, tracker
decoding, unit tests, a full corpus, hosted CI and independent peer review
were not changed or rerun. Original/R8/control replay and sync bytes remain
unchanged. No raw whole replay, native image or runtime table dump is included
in the source checkpoint.

Next authenticate constructor/helper state preservation and the remaining
effective catalog/mask inputs before replaying cumulative selection state or
attributing a unit/owner to a talent. Historical 41810 rules and successful
native application/playback remain separate requirements. All work stays
offline: no game, Battle.net, Computer Use, network, remote refresh or
publication. Full upgrade/playback remains false.

Addresses, memory offsets and allocation/stride literals are hexadecimal.
Row/event/user counts, loop counts and subgroup values are decimal.
