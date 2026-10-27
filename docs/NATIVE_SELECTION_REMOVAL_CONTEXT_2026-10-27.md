# Removal masks and conditional talent-unit context

The selected native short-mask path now resolves the bit-order ambiguity for
the masks present in the pinned recordings. A conditional item-array model
then leaves exactly one unit before every one of the 70 talent purchases in
each file. Exact tag-key joins find a prior tracker birth/owner record for all
of those candidates, with recorded control owner matching explicit PlayerSetup.
The key condition remains unproved: each added unit must pass the client's
effective catalog/reference gates. These results do not capture actual client
rows, unit objects, successful insertion or playback.

## Selected short-mask representation

The selection reader's typed wrapper `1A713D0` calls generic reader `1A70A00`.
Its original function extent contains complete code through `1A7137E`, two
alignment bytes, and a separate 64-byte / 16-entry kind switch table at
`1A71380`. All table targets are checked instruction boundaries. Kind 3,
BIT_ARRAY, enters `1A70B7B` and reaches `1A704C0`, then `1A71400`.
The table is pinned transformed data, not unchanged original PE data or a
new proof of the earlier opaque game-event dispatcher.

The original type-321 accessor's slot `+10` points to `1359C10`, and the
choice type-313 slot `+18` points to `135BFF0`. The choice callback selects
tag 1, clears its count/data, and returns choice payload `+4`. The bit-array
callback stores the count and returns payload `+8`. Thus the selected delta
uses discriminator at `+4`, count at `+8` and bit data at `+10`.
The metadata allows counts 0..32; the observed masks have only 1..3 bits.
On selected old-count 0 / new-count 1..3 callback paths, the byte-fill call
is not reached.

For those short counts, the bit-copy routine follows its sub-eight-bit path,
accumulates input chunks in the same order as the pinned Python bit-buffer,
and writes the result into the low bits of one output byte. The consumer
at `202DC8A` tests `data[i>>3] & (1 << (i&7))`. For the observed lengths,
the native removal mask therefore tests bit i of the decoded integer.
It is not necessary to retain both low-bit and high-bit interpretations
for this selected current-client path.

An operand-derived calculation covers widths 0..3, all eight starting bit
offsets and all patterns: **120 cases**, compared with the unchanged official
Python BitPackedBuffer class. This is not CPU emulation. The result requires
a coherent buffered success path; arbitrary longer bit arrays, native refill
providers, allocation/error paths and complete generic-reader acceptance are
not proved by the selected comparison.

## Removal and numeric item order

`202DBC0` distinguishes the native variants as follows:

| Variant | Selected consumer behavior |
| --- | --- |
| None, 0 | remove nothing |
| Mask, 1 | walk indices backwards below min(unit count, bit count), removing set bits |
| OneIndices, 2 | consume supplied indices in reverse list order; no silent sorting or deduplication |
| ZeroIndices, 3 | walk row backwards, retaining matches against the tail of the supplied keep list |

The finite data has no OneIndices and only empty ZeroIndices lists. Those
empty keep lists remove all prior items. The original/R8 mask distribution
is length 1/value 1:45, length 2/value 2:23, length 2/value 3:1,
length 3/value 5:1 and length 3/value 6:1. Each also has 79 None and eight
empty ZeroIndices events. The control has 24 None and 13 length-1/value-1
masks. Each stream is freshly decoded to exhaustion and remains hash-identical.

`202EAA0` decrements group membership, compacts an emptied group, adjusts
active/group tags, shifts the item/tag arrays and decrements unit count.
Its copy calls retain an explicit ordinary overlapping-copy contract for
`1A2B250`; this audit does not close that helper's whole CPU-dispatch CFG.
Valid index/group invariants and stable state remain prerequisites.

After its reference and capacity gates, `202D910` inserts unique uint32
handles in ascending numeric order. That numeric item order is independent
of the unknown descriptor key and predicate values. The conditional model
uses the qualified empty initialization, these removal rules and this item
insertion order, assuming each nonduplicate in-capacity addition passes
the native catalog/reference gates and no other mutator changes the row.
No definition key, predicate, hero identity or owner value is invented.

## Conditional singleton result and exact recorded-key joins

Under those explicit conditions, the model yields:

| File | Talent purchases | Purchases with exactly one item | Skipped duplicates/capacity additions |
| --- | ---: | ---: | ---: |
| Original 41810, target-style projection | 70 | 70 | 0 / 0 |
| R8 partial, native-content projection | 70 | 70 | 0 / 0 |
| Current 98348 control | 70 | 70 | 0 / 0 |

The earlier wire audit established that the latest recorded subgroup index
before each purchase is 0. With valid nonempty group invariants and exactly
one item, there is only one active group and its first matching item is that
handle. Specific descriptor key/bit-5 predicate values are then unnecessary
to distinguish multiple units. This reduces the conditional actor-context
problem; it does not authenticate the insertion gates or actual simulation.

Each candidate handle is split with the existing repository packing lanes:
source shift 18, R8/current shift 22. This reuses `repair_unit_tags.py`'s
recorded migration, and performs no new tag conversion or replay write.
The resulting index/recycle pair is joined to the exact tracker key.
Owner selection uses a strictly prior record plus all same-loop owner
alternatives; it does not assume cross-stream ordering within one loop.
Player identity comes from explicit PlayerSetup user/player fields.

All three cases have zero missing prior birth/owner records, zero ambiguous
recorded owner contexts and zero recorded-control-versus-setup mismatches.
The normalized original/R8 purchase contexts are identical. R8's tracker
is byte-identical to the source, so this is only two independent tracker
contents, not three. Fresh tracker reads cover 6,614 / 6,614 / 6,181 events.

Two source/R8 candidate purchases join to **VehicleDragon** birth records.
The recorded control owner still matches the setup player. Unit type labels
are read only after exact key matching; neither hero name nor nearest time
is used to identify a unit. A fixed hero-unit shortcut would miss these
conditional contexts.

There are also 47 source/R8 and 36 control purchases after some prior tracker
death record for that key. This is not an assertion that a native pool slot
was absent, destroyed or still dead. The join keeps recorded ownership and
runtime existence separate; it does not discard handles based on that
unsupported interpretation of tracker deaths.

## Verification and remaining boundary

Twelve qualified ranges total **5,185 bytes / 1,453 instructions**. Nine are
complete original RuntimeFunction/CHAININFO unions; another is complete
generic-reader code with its two-byte alignment and 64-byte switch table
separated; two are branch-closed no-call leaves. All 94 selected instruction/
call checks and three original callback-pointer checks pass. All 16 switch
targets and 120 short-mask model cases pass. PE/transformed-text authorities,
schemas, replay files and unused launcher drafts remain pinned separately.

The private item and tracker join reports retain handle keys. The source
checkpoint exposes finite aggregates and their hashes rather than those
per-purchase keys or raw replay/native-image files. Source projection follows
the selected target behavior; historical 41810 native semantics remain
unauthenticated. R8 still declares 98285 and is not a new 98348 artifact.

The catalog/reference acceptance condition, actual runtime pool/owner
identity, other snapshot/mutator effects and historical 41810 rules remain
unproved. No safe talent-index migration follows from the singleton result.
Next prioritize the effective insertion gates and relevant unit identity,
using the now-explicit expected contexts without guessed definition values.
Successful native playback remains a separate requirement.

Python and GNU objdump under WSL supplied static and recorded-data evidence.
No production conversion code, replay, sync data, unit tests, full corpus,
hosted CI or independent peer review was changed or run. No native target or
CPU emulation, REA native provider, game, Battle.net, Computer Use, network,
remote refresh or publication occurred. Full upgrade/playback remains false.

Addresses and offsets are hexadecimal; event/type IDs, bit widths, counts,
packing shifts and numeric mask values in prose are decimal.
