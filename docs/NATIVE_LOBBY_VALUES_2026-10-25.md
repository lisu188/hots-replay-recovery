# Current native battlelobby value codec

`native_lobby_values.py` adds a strict typed-value reader and writer for the
current native OnlineStartGameRequest, rooted at type5917 with serializer
context zero. Supplied values can now be edited and serialized independently
of a retained source token stream. Exact reproduction of unchanged source
bytes remains a separate operation.

The existing frozen `native_startgame.py` continues to decode the named graph
and reproduce its unchanged source tokens. It supplies an independent reader
for this milestone's actual-value checks. The new codec is a separate module;
it does not change that reader or its source-only reencoder.

This provides a current-format writer. It does not supply missing historical
values or produce a working TEN_GREYMANE conversion. `full_upgrade_complete`
remains `false`.

## Scope and API

```python
from native_lobby_values import (
    decode_lobby_values,
    encode_lobby_values,
    reencode_lobby_source,
)

lobby = decode_lobby_values(member_bytes, profile='online-values-98348')
canonical = encode_lobby_values(lobby.value, profile='online-values-98348')
original = reencode_lobby_source(lobby, profile='online-values-98348')
```

The public API accepts only profile `online-values-98348`, root5917, a complete
member starting at bit zero, and the exact pinned current schema. It does not
accept caller-selected roots, arbitrary schemas or nonzero serializer contexts.

The retained schema contains 513 selected types, including declarations for
online root5917 and offline root5962. The public codec supports root5917 only.
Its schema SHA-256 is
`0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640`.
The graph belongs to the named Battlenet registry. It is distinct from the
anonymous native775 setup graph and its registry.

All16 schema kinds have explicit representations and strict checks. STRUCT and
ARRAY values are tuples in declaration order; USER aliases expose the child
value; OPTIONAL is `None` or its child; BOOL requires an exact boolean; INT and
ENUM require exact integers within the selected bounds and domain. FOURCC is
four bytes; BLOB and string values are bytes; BIT_ARRAY is `(length, pattern)`;
CHOICE is `(tag, child)` with a declared tag; NULL is `None`.

ASCII_STRING permits only bytes `0x01..0x7E`, within the declared count bounds.
Python's ASCII decoder alone is insufficient because it also accepts NUL and
DEL, which the native validator rejects. STRING uses the recovered native
sequence counter and encoded byte-count bounds rather than substituting a
Python text-codec policy. REAL32 and REAL64 are unsigned raw32/64bit patterns;
they are not Python floating-point values. This preserves signed zero and NaN
payload bits. NULL writes no bits. CHOICE writes its tag and the corresponding
declared child, rejecting tags with no matching field.

The decoded object is frozen and suppresses value representation. Public
summaries contain only source fingerprints, byte/bit extents and aggregate
counters. Input/output size, nodes, arrays, strings and recursion are bounded.
Diagnostics omit supplied values and private field paths.

## Native writer context and source identity

A fresh, targeted Ghidra job confirmed the battlelobby writer and both reader
branches using registry `0x143B7F140` with serializer context zero. The server
branch selects type5917 and the local branch selects type5962. The writer
passes zero as its fifth argument at callsite `0x1350CAA`; the reader does the
same at `0x134C8B9` and `0x134C98E`. Archive stream context is a different
argument in a different call and does not imply a nonzero serializer context.

The selected descriptor and CHOICE helpers confirm count bounds, continuous
versus explicit tag lookup, and child-type selection. Together with the
retained generic writer, ASCII validator and scalar evidence, these close the
kind-specific contract for a successful, bounded current5917 value writer.
The job processed the project read-only and discarded changes. The public
receipt retains source fingerprints, RVAs, assertions and limits in
`observations/native-lobby-zero-context-static-proof-2026-10-25.json`.
Native exports and client binaries remain outside the publication.

`encode_lobby_values` writes supplied values using canonical zero alignment
padding. Accepted nonzero internal source padding can therefore make its output
differ from the source despite equal values. `reencode_lobby_source` revalidates
the retained source, hash, payload boundary, statistics and unchanged values,
then reproduces the exact source bytes including accepted internal padding.
Whole-member decoding validates zero final padding and records the payload
boundary before consuming that padding.

## Validation

All22 new synthetic tests passed locally. The tests cover the selected types
and all16 kinds, strict scalar/ENUM/CHOICE domains, ASCII and native STRING
validation, raw REAL patterns, optional presence, arrays, nulls, bounds and
budget rejection, source preservation and tampering, and an independent
per-destination-bit oracle with negative controls. The source-bound local test
receipt is `observations/native-lobby-values-local-tests-2026-10-25.json`.

The selected local regression run also passed all132 tests: these22 new tests
and110 existing codec tests. This selected result is separate from the whole
repository corpus assigned to hosted CI. From the repository root, the new
synthetic module can be reproduced with:

```text
python -m unittest test_native_lobby_values
```

The retained21 current build98348 controls also passed a fresh bounded
integration. Every whole `replay.server.battlelobby` member was reproduced
exactly by both canonical value serialization and source-preserving
reproduction. The current inputs happened to contain no discarded nonzero
internal padding. The new payload end matched the frozen reader for each
member, and **8,897,304 logical nodes** agreed after representation-aware
projection into the independent reader's values. The actual controls observed
400 types and13 kinds; full513-type/16-kind coverage is a separate synthetic
test claim.

The integration additionally changed one bit of the existing four-byte
`m_randomSeed` BLOB in a public current EU control, entirely in RAM. The frozen
reader decoded the edited value, the member length and payload end stayed
unchanged, and an independent XOR mask established that the single changed bit
was confined to the original32bit span `[2246024, 2246056)`. No seed value or
member bytes were emitted. This demonstrates writing an edited supplied value
without constructing a historical default.

All21 source replay hashes and file identities remained unchanged before and
after the checks. The integration used 25,928,547 unique input replay bytes,
below its32MiB cap, and read only the selected battlelobby member plus archive
headers/tables. It did not read original41810 or R8. The intentionally edited
control buffer was never saved, and no archive was written. The safe receipt
is `observations/native-lobby-values-21-current-2026-10-25.json`.

CI for this milestone is pending at documentation preparation time. Local
tests, retained-member equality, the controlled RAM edit and static native
review are separate evidence from the eventual hosted run against its exact
published commit. None of these checks launched the game or used Computer Use.

## Target and remaining recovery work

The existing official EU manifest observation from2026-10-25 reports
`2.57.0.98348`. Its source is [Blizzard's EU versions endpoint](https://eu.patch.battle.net/hero/versions),
with retained body `references/hero-versions-2026-10-25.txt` and receipt
`observations/native-setup-live-target-2026-10-25.json`.

The historical recovery still needs resource identities and ownership,
historical/current field semantics, compatible catalog state and deterministic
sync/playback evidence. Current serialization does not authenticate the
missing ClientInfo or SharedPlayerInfo meanings, reconstruct old catalog
rules, retarget R8 metadata or establish cached CRC/native object state.
No upgraded replay or full conversion is claimed by this milestone.
