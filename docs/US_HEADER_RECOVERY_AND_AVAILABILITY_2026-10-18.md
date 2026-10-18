# Exact current US package recovery and availability representation

Two of the three previously missing exact US headers are recovered offline.
They match the FULL terminal SHA256 values read directly from the pinned public
Protectors Dragon Shire replay, SHA256882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c.
Its actual executable/base/data98348 and rootc3b3... were independently checked,
including fresh complete observed core roundtrips with canonical Blizzard96477.

| Target | Actual package/version | Bytes | Exact advertised SHA256/result |
|---|---|---:|---|
|HeroesData|243553/65665|222049|0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a — recovered|
|Dragon Shire map|243571/65624|4057|3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429 — recovered|
|Dragon support DataMod|280539/16|unknown target size|42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a — unresolved|

The three already-known Core/Teams/Heroes US headers were first reconstructed
from their exact EU counterparts using actual US identity/archive/visual/
locale/dependency fields. Each namespace-minus-package-ID hypothesis was
derived from the other two US modules, with the tested target excluded. All
three whole headers match their known hashes AND bytes; six wrong-module
controls reject. Root and separate reviewers repeated these controls.

The missing-header trials were explicitly bounded at one initial recipe per
target. HeroesData and Dragon map matched exactly and passed separate generic
EOF decoding, lossless wire roundtrip and actual replay package/terminal/payload
binding before exclusive private creation. Independent RAM reexecution without
the producer wrapper/save function reproduced all three hashes and both saved
files byte-for-byte. All raw headers remain outside Git.

The initial DataMod candidate bcbacce6174dac21f9c289f4dd6a7e6b40873c15cc96c3624a37204c4793aa67
was rejected. Its authenticated EU source itself falls outside the base-module
namespace relation. A separately reviewed single hypothesis preserving ONLY
that source namespace leaf, with every other prior candidate subtree byte-exact,
also failed:50d7f1580f339d55aed6a665a2b9bda9f8019f839fa2ac886a87013aab8e3aef.
Neither mismatching body was saved. These misses do not identify which target
fields differ. No more DataMod recipes are authorized by this report.

## Availability representation constraints

Fifteen source/R8/current cases contain2270720availability bytes. Each has
exactly two literal2-byte cell patterns: zero and one fixed nonzero pattern
with one set bit. The alphabet is identical across all15cases; the hypothesis
that the nonzero pattern has all16bits set fails. Literal patterns, bit
positions, column vectors, account IDs and per-position flags stay private.

All cases have10active and10varying cell positions. These flags exactly match
details-participant working-set presence across all16positions, yet5760joint
bijections remain compatible. Four current cases have1-2 extra occupied lobby
entries absent from details. The weaker activity-implies-occupied relationship
permits8709120bijections. Lobby-array ordinal coordinates admit zero global
compatible bijections. Presence correlation does not establish a unique slot
mapping, ownership semantics or a conversion/default for new or unmapped keys.

Twenty focused privacy/bounds/permutation tests pass. Root and another reviewer
independently recomputed every actual case and got identical complete v2JSON.
The total input was18284640replay bytes including the R8 duplicate; all inputs
remain unchanged. These local20tests are separate from the published894-test
three-lane CI atf97e57a, which does not reconstruct real static headers.

## Reproduction and remaining work

Executed source snapshots and their receipts are under research/exact-header-98348
and observations/exact-header-98348. Publication bindings preserve exact producer
bytes/hashes. Regional/availability producers retain original machine-bound
private-input paths; only the earlier root EU header CLI is portable.

Five of the six current US Dragon package headers are now exact and available
locally; DataMod remains missing. The shared EU four-base-header set is also
available, while a genuine current EU Dragon final tuple remains unbound.
R8 still declares98285 and is unchanged. Opaque174-to198-bit player conversion,
207legacy availability/alias cases and catalog/ability/unit-instance/rule/sync
equivalence remain unfinished. No client launch, replay output or deterministic
playback proof is claimed.
