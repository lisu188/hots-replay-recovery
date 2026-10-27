# Current ability callback route and original command contexts

The selected current98348 command validator's callback is now traced to a
runtime type lookup, a per-type command descriptor and a callback slot at+80.
Selected initialization code supplies both constant callbacks and a callback
that reads a data record at+190. This replaces an opaque callback dependency
with specific static reads and assignments. The actual records for historical
ability links126/351, their current identities and context bit2 remain unknown.
No flag conversion or replay changed; full historical conversion is incomplete.

The three dated `native-ability-callback-route`, `native-ability-source-context`
and `native-ability-callback-validation` observations contain the range hashes,
source pins, aggregate contexts and local validation results. All addresses
below are RVAs unless explicitly described as object offsets.

## Callback lookup and selected initialization

The existing qualified validator202AFB0 calls5E48D0, passes its result to
A51A70, uses command index object+38, checks A27180, and retrieves the callback
through A27340 before indirect call202B473. The returned AL enters the already
modeled post-callback gate at202B475.

- `5E48D0..5E4920` follows a runtime registry rooted at global slot3388B18.
  It obtains a16-bit key from link object+40, follows the registry's entry and
  returns DWORD[resolved record+24], orFFFFFFFF on lookup failure. This is a
  runtime data dependency, not a recovered table of historical link names.
- `A51A70..A51AAD` accepts type indices0..18 only when the corresponding bit
  in bitmap36350C0 is set. It returns3604290 + index*2A48, otherwise null.
  The stride does not establish the extent of every object in that storage.
- `A27340..A27364` returns the callback at descriptor + command_index*A8 +80
  only if the index is below DWORD[descriptor] and the slot's byte at+8 is
  nonzero; otherwise it returns null. `A27780..A27793` writes the supplied
  pointer to that exact slot. It does not check those bounds itself.
- The separate mask getter `A27180..A271C0` reads the bit at descriptor+150C
  for an active, in-range slot. Its inactive/out-of-range fallback returns
  **true**, so it must not be treated as a generic bounds-validity predicate.

Selected initializerA51FE0 and helperA50B20 connect local descriptor construction
to the storage used by the getter. Slot initializerA27530 installs callback
A93770, which returns AL=0, while initially marking the slots inactive. Builder
B91D80, used for numeric type5, passes nonzero active byte2 for three slots and
sets callback pointers yielding classes3/2/2 at indices0/1/2. BuilderC03A40,
used for numeric type6, sets one active slot and tail-calls A27780 with C02780
for index0. These are selected constructor assignments under normal helper/copy
behavior, not live table observations or proof that no later alias changes them.
Numeric type5/6 are not historical ability links126/351.

Four separately bounded leaf callbacks return AL=0/1/2/3 at
A93770/A93790/A93780/A93760. Their upper return-register bits are not relevant
to the validator's zero-extension of AL. C02780 instead resolves a data record;
on its selected normal nonnull path it reads DWORD[record+190] and maps:

| Data field value | Callback class |
| ---: | ---: |
| 0 | 1 |
| 1 | 2 |
| 2 | 3 |
| Any other32-bit value | 0 |

A null resolved record gives class0. The field's symbolic name and historical
value are not authenticated. Another inspected callback, C09D00, retrieves and
calls a nested callback or yields zero after lookup failure; callback behavior
therefore cannot generally be reduced to a constant per hero.

## Actual original replay contexts

A fresh read-only decode of104,257 original game events and6,614 tracker events
reproduces the private selection-context receipt. The source remains635,140
bytes with SHA-256
`e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824`.
Across the61 commands for the two numeric links, every command index is0:

| Source link | Flags | Target | Count | Selected-unit candidate |
| ---: | --- | --- | ---: | --- |
| 126 | 0x100 | Unit | 21 | HeroFaerieDragon |
| 126 | 0x80100 | None | 9 | HeroFaerieDragon |
| 351 | 0x100 | Unit | 24 | HeroTyrande |
| 351 | 0x80100 | None | 7 | HeroTyrande |

The candidate comes from the existing selection/tracker audit with both mask
orientations checked. It is not the authenticated executed caster, an ability
name, a current catalog identity or a self-cast diagnosis. The first of the16
targetless exceptions occurs at loop1682; loop64 is not a measured divergence.

The current selected gate has a useful **conditional** implication. Assuming
the same callback class and the same context bit2 for both shapes, the classes
that pass both Unit/0x100 and None/0x80100 are:

| Context bit2 | Classes passing both existing shapes |
| --- | --- |
| false | None of0..3 |
| true | 2 only |

This is a comparison of a current partial gate against historical command
shapes. Neither assumption has been measured for those historical commands.
It does not establish a rejection, the cause of a desync, or that changing the
16 commands to0x40100 would be correct. The latter remains an unapplied
hypothesis. Authentic link/type/data-field/context evidence is still required.

## Named enum boundary

The original PE contains a genuine named enum registration:5F59B3 supplies
`ECmdFlags` and5F5A0A calls1600E80 with table2BD5310. Forwarding through16001D0
binds a count of10 records and a24-byte source stride. The constructor consumes
a32-bit value, name pointer and name length from each row. The240-byte table
has Unknown=FFFFFFFF followed by values0..8 named Alternate, Queued, Preempt,
SmartClick, SmartRally, Subgroup, SetAutoCast, SetAutoCastOn and User.

The neighboring table beginning2BD5400 is excluded. These are authenticated
named enum values; their association with the full26-bit replay flag word is
not established here. They do not name bit18 or19. An unrelated `TargetSelf`
string in an ability-category table does not supply that missing association.

## Authority, checks and limits

Original PE authority:53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction authority is the existing analyst-transformed text patch,
36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
It is separate from unchanged signed PE text and is not a runtime capture.
Original data-table bytes and instruction bytes are accounted for separately.

Twenty-one nonoverlapping selected ranges cover12,067 code bytes and2,180
instructions. Every decoded byte matches the pinned transformed text. Selected
direct noncall branches land on internal instruction boundaries, except the
explicit C03ACD tail transfer to the qualified setterA27780. Slot initializer
A27530 and callbackC02780 each have three RuntimeFunction fragments, joined by
original CHAININFO. Leaf getter fallback blocks are included; stopping at their
first RET would omit real paths. Exploratory partial ranges and raw xrefs are
excluded from these counts.

A small byte-opcode interpreter checks260 values through the selected nonnull
C02806..C0282C field-mapping block, including unsigned boundary cases. All
agree with the table above; this finite check is not an exhaustive32-bit run or
native execution. Four constant callback byte patterns are checked separately.
Six existing target-gate tests pass. No production code changed, no broader
corpus or hosted CI ran, and no independent peer review is claimed.

Original/R8/current-control lengths and SHA-256 values remain unchanged. The
two unused launcher drafts remain untracked. The user's **Keep all work offline**
instruction remains active: no game, Computer Use, network or remote publication
occurred. Missing player/lobby/catalog state and deterministic playback remain
unproved; this checkpoint does not supersede the98285-resumable-R8 replay.
