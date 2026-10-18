# Current replay availability vectors: 21-case offline comparison

Twenty-one genuine current-build replays have the same ordered 5418-entry
registry. Comparing their per-participant availability vectors narrows the
possible cell arrangements; it does not yet establish a migration rule.

| Frozen audit | Presence-compatible arrangements | Repeated-account pairs with exact vectors | Different-account pairs with exact vectors |
|---|---:|---:|---:|
|13 current controls|2880 active x 2 never-participant = 5760|12 / 19|0 / 7781|
|21 current controls|240 active x 1 never-participant = 240|59 / 81|0 / 20919|

The extension uses eight other-map replays already acquired and verified for
the earlier catalog comparison. All eight pass; there are zero acquisition
attempts and zero source/decode failures. It requires pinned replay and prior
core-profile hashes, actual executable/base/data build 98348 and root
c3b3c8bc82e3a5a62e550fdde9a40c28, complete battlelobby mod/tail roundtrip and EOF,
private details/initData/tail identity, position and seed agreement, and exact
registry order. Core event decoding is bound to the earlier profiles rather
than repeated by this audit. Original and R8 are rehashed as preservation guards.

Every presence-compatible active arrangement is enumerated. For 13 controls,
two arrangements tie at the maximum 12 repeated-account exact pairs. For 21,
one arrangement attains the maximum 59 pairs, including the observed direct
working-set alignment. No arrangement makes all 81 repeated-account pairs equal.
The other 22 pairs differ in 1-12 registry rows, 74 mismatched rows in total.
Different-account vectors differ in 346-3845 rows across the 20919 comparisons.
These are statistical correlations. They prove neither ownership semantics nor
an authoritative participant-to-cell mapping, and no mapping is selected.

The extension reproduces the frozen 13-case comparison exactly. It reads
29002257 distinct replay bytes including original/R8 guards, 61018250 explicit
analysis-input bytes including repeated guard and MPQ reads, and 3640896 decoded
availability bytes. Its limits are 40 MiB distinct replay bytes, 180 MiB explicit
input reads, 8 MiB availability and 21 current cases. Runtime executable/import
filesystem activity is outside that explicit input accounting scope.

Sixteen focused tests cover the first audit and twelve cover the extension.
An independent reviewer ran all 28 tests with no skips and freshly recomputed
both complete JSON reports without overwriting the frozen results. Both match
exactly, and source/receipt digests remain unchanged. These are local research
checks; the existing 894-test hosted corpus does not execute these private-input
audits. Producer bytes, test sources, review source and sanitized receipts are
published under research/exact-header-98348/availability/vectors and the matching
observations directory, with byte-preserving publication bindings. Their input
paths still refer to the original private research workspace.

No raw cells, vectors, vector hashes, account identifiers, slots, presence
signatures or candidate permutations are published. No availability values are
generated, no replay is created, and HotS is not launched. R8 remains unchanged
and declares 98285. The old 263-string registry, current 5418-license registry,
opaque player fields, catalog/ability/unit-instance/rule changes and retained
synchronization data still require a justified semantic conversion.
