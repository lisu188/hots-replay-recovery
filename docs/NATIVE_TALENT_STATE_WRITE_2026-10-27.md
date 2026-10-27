# Native talent state write and a conditional event110 consumer

The selected native path writes the incoming uint32 talent index to
`3677A30 + (firstSelector * 32 + entry.Tier) * 4`. Its selected admission
predicate requires the tier cell to be empty (`FFFFFFFF`), along with other
conditions. A separate path clears an occupied cell and reassesses later
choices. These are static code findings under the record/storage conditions
below; native execution and simulation effects remain unproved.

The transformed code also contains a conditional route from header `3006E`
through callback `B612D0` to this writer. The switch tables differ from the
original PE, and the dispatcher has an unqualified obfuscated prefix. This
is a conditional suffix binding, not an end-to-end parser/dispatcher proof.

The two dated `native-talent-state-write` observations contain exact selected
range, instruction, table and replay pins. All addresses below are RVAs;
numeric code addresses and offsets are hexadecimal unless stated otherwise.

## Selected state mutation and its gate

`B10720` preserves the incoming first low-byte selector and uint32 index. It
forms a 128-byte row at table `3677A30`, obtains a handle via `9D5080`, and
calls `B0E870(handle, row, adjacentValue, index)` at `B1077A`. A false result
branches to failure. The adjacent value is read from table+800+selector*4
only when the selector is below16; its semantic meaning is not established.
This writer alone does not prove a universal selector bound or a player/user
namespace.

`B0E870` resolves and checks the index against record+500, copies the64-byte
entry from record+510+index*64, checks other data and `B10220`, then passes
the copied entry+8 to `B0E6E0` as its fourth argument. The previous named
`CHero`/`SHeroTalentTree` layout bridge binds that field to `Tier` under normal
record and initialization conditions.

`B0E6E0` checks a bitmap, a tier below32, earlier selections associated with
record tier entries, the target tier cell and a threshold. At `B0E850` it
compares row[Tier] with `FFFFFFFF`. A nonempty cell takes the false path;
the empty path reaches the unsigned threshold comparison at `B0E857` and
`setae bl` at `B0E85B`. Effective bitmap/threshold values and the names of
the further record fields are not authenticated here.

After admission, `B10720` resolves/copies the entry again. `B108EF` loads its
Tier, `B10902` forms firstSelector*32+Tier, and `B10934` stores the incoming
index in that DWORD cell. It then calls notification constructor `94AF40`,
which puts the selector and index in a stack record and sends it to `2DDC10`.
No effect or authoritative simulation application is inferred from that sink.

The writer checks later choices with `B10220`; a failed check reaches
`B0EC80`. That function writes `FFFFFFFF` to a nonempty cell at `B0ECD6`,
calls `94AF00`, and recursively clears later choices whose checks fail.
This documents selected scalar state changes, not a generic purchase engine.

## Conditional observer route

The original object at `2F73050` points to table `26EC238`; its slot+8 points
to `B58E70`. Prior registration code supplies this observer with header
`3006E`. A bounded raw-reference scan found the direct call `B5F9B4` to
`B612D0` inside that dispatch method.

Its selected suffix loads the saved header, subtracts `3000E`, bounds the
unsigned result to98, and uses two tables to select an arm. For `3006E`:

| Step | Selected value |
| --- | --- |
| Header minus3000E | 96 decimal |
| Byte at transformed B5FA60+96 | 26 decimal |
| DWORD RVA at transformed B5F9EC+26*4 | B5F9A9 |
| Direct call in that arm | B5F9B4 to B612D0 |
| Callback index load | B61394 from event+30 |
| Callback writer call | B6139A to B10720 |

`B612D0` derives its first selector using event bytes and an optional resolved
object, tests a selector bitmask, and only then calls the writer. A normal
return is followed by `BFA9D0` regardless of the writer's returned AL. The
selector namespace, bitmask meaning and that further call's effects remain
unbound.

The99-byte switch selector table and116-byte RVA table are in the pinned
transformed text. Respectively98 and116 bytes differ from the original PE.
Their transformed hashes and separate original hashes are recorded. An
initial original-byte-equality assertion failed and was replaced by explicit
difference accounting; the tables are not presented as original PE values.

The entire27731-byte dispatcher union was decoded only as a private search
aid. Its obfuscated prefix and embedded tables make that linear sweep
unsuitable for whole-function instruction/CFG claims. Only two clean suffix
windows, totaling73 bytes/15 instructions, are qualified separately, with
explicit image-base, saved-input and transformed-table conditions. The
factory/dispatcher-to-callback route and entry-to-suffix control flow remain
unproved. There was no execution or new process-memory capture.

The additional wrapper `20B9A50` calls the same writer and references the
original error-context literals `TalentTreeSetSelectedHeroTalentTree` and
`inTalentTreeIndex`. This is further local naming context, not proof of a
particular replay or actual call at runtime.

## Implication and validation limits

The earlier literal current Kaelthas tree places both BurnedFlesh and
SunKingsFury at Tier3, whereas one source player recorded both purchases.
If a by-name migration used those effective current entries, a stable shared
row and this selected admission path, the second choice would encounter a
nonempty cell unless intervening work cleared it. This strengthens the
conditional collision finding. It does not authenticate those effective
entries, prove a universal purchase rule, determine a desync cause or justify
a15-to7 replacement or deletion of either historical choice.

Eight complete original RuntimeFunction/CHAININFO unions total3145 bytes and
807 instructions. Every selected byte, boundary and direct non-call branch
was checked against the pinned transformed text. Four graph checks show that
the selected success edge is necessary to reach the writer, threshold result,
index-gate success or callback write call. Helpers are modeled as normally
returning and conforming to Windows x64 ABI. Valid disjoint storage, stable
resolved records/rows, valid selector/Tier cells, and no exception, reentry,
concurrent write or alias mutation are required.

Source/R8/current replay and unused-launcher hashes are rechecked. This is
ordinary offline Python/GNU objdump analysis under WSL. No new REA/IDA/Ghidra
session, native Evidence, unit tests, broad corpus, hosted CI or independent
peer review is claimed. Production/conversion/replay/sync data are unchanged.
Full upgrade/playback remain false; all work stays offline.

The next useful boundary is the unqualified dispatcher entry-to-suffix route
and the effective target-context data/selector identity. Historical41810
talent definitions and rule equivalence remain required before a safe mapping.
