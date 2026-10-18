# Native resource matrix representation

The 98348 native metadata names the observed 32-byte availability rows as
`ScopeResources`: a fixed array of 16 `ResourceState/u16` values. Its outer
`ResourceAccessMatrix` has a 32-bit count. The selected StartGameRequest graph
places `m_accessMatrix` between `m_resourceMap` and `m_disabledHeroList`.
The separate ResourceAccessList type contains individual u16 elements and is
not substituted for this matrix.

One hash-bound read of the installed 53,573,840-byte executable supplies the
selected metadata projection. The actual matrix audit then reads existing
public replay controls, without loading the executable or launching HotS.
All 21 controls pass current build/base/data 98348 and root checks, prior
profile hashes, complete mod/tail EOF, private identity/slot/seed checks and
unchanged original/R8 guards. All 5,418 ordered resource identifiers agree
across the cohort.

A separate byte-aligned reader/writer checks the resource-map, matrix and
disabled-list boundaries and preserves every numeric value and byte. Across
21 replays it verifies 113,778 rows and 1,820,448 u16 cells. The selected block
re-encodes exactly in every case. The producer accounts 61,324,571 explicit
input bytes, 29,002,257 distinct replay bytes including original/R8 guards,
and 3,640,896 decoded matrix-row bytes. Implicit import reads are excluded.

Twelve focused tests pass. Independent code review reruns those tests and the
static-shape validation, checks all frozen source/report pins and confirms the
saved cohort against the earlier independent ClientInfo reader. It does not
reopen all replays or claim a second actual-matrix corpus execution. The native
grammar itself was independently compared across all 8,330 metadata records
in the preceding checkpoint.

This establishes representation and exact preservation. It does not identify
ownership, entitlement rules, bit meanings, a scope-to-player assignment or a
rule for filling newly introduced resources. No 263-name historical registry
mapping or 174-bit player conversion is inferred. No raw matrix, values,
patterns, vector hashes or player identifiers are published.

The additional eight-attempt legacy-fixture search is scoped negative evidence:
two Firecrawl calls were blocked before execution, four GitHub metadata calls
and two web queries found no exact 41810 candidate. Three complete repository
trees expose an unversioned replay and a filename mentioning 39445; those names
and dates do not authenticate a build. No header or replay was downloaded in
that recorded search. Later bounded header checks, if performed, need separate
receipts. The search does not establish global absence.

The portable ClientInfo v3 code-only review is also preserved here. All 14 tests
pass, including the isolated post-recursion field-cap regression and same-width
token mutation rejection. It binds the final exact-local-source 21/222 proof to
the earlier independent decoder corpus. Original profiles and earlier receipts
remain unchanged. Root also ran the 14 new tests plus the 20 existing tail tests.

No replay was generated. R8 still declares 98285, full migration is unfinished,
and the user instruction to keep HotS unlaunched remains active. These matrix
research tests are local evidence, separate from the hosted root-test workflow.


The native-reader source checkpoint af8ef7c passed complete CI run 39173281503:
908 tests across 45 root modules on each of Linux, Windows PowerShell 7 and Windows
PowerShell 5.1. All 14 new tests executed, and each lane decoded ten actual EU
ClientInfo records with matching anchors, identities, ends and exact spans.
Declared skips remain 38 on Linux and 4 on each Windows lane. The actual NGS
range fixture and current EU core/lobby checks executed. These hosted checks
did not inspect the installed PE, private dumps or rerun the 21-case matrix audit.

A subsequent 4096-byte HTTP 206 prefix read of the formerly unversioned public
fixture reports 2.35.0.66488 with executable/base/data66488, excluding it as an
41810 candidate. Exact Content-Range and immutable commit URL are retained.
The prefix was decoded with the pinned official schema, then discarded; no
full replay/Gitblob hash or complete archive validation is claimed. This header
check is separate from the earlier eight-attempt zero-acquisition search.
