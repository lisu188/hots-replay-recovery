# Native serialization clues and preserved 41810 executable metadata

This checkpoint preserves two newly authenticated sources for the remaining
offline migration investigation. It does not establish a replay conversion.

## Current executable: byte-only inspection

The installed Base98348 executable is53573840bytes, SHA256
efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9.
Its complete resource text says2.57.0.98348. Fixed version words are separately
[2,57,0,32812]; the16-bit low word is not substituted for the textual build.
The executable is read as a file; no game image, client DLL, debugger or game
process is loaded or executed.

Native ASCII labels include replay.server.battlelobby, m_licenseCatalog,
m_licenseInstance, m_clientLicensesList and four m_mapNamespace occurrences.
The latter occurs beside S2Map BnetHeader and familiar archive/definition/
variant/dependency fields. ClientLicensesList occurs in neighborhoods containing
S2Game EncodedGameDataHeader, resourceMap and resourceAccessList. BattlePay
licenseCatalog/licenseInstance neighborhoods are distinct. These are string
adjacencies, not formal field-container membership or bit-layout declarations.

The frozen initial/context reports total156753bytes. Two PE reads total
107147680bytes and selected context union33666bytes, below64KiB. An independent
one-pass reviewer reproduces all320 selected literal locations, selection/family
counts,11 context inventories, section/RVA maps and version fields. It confirms
29 RTTI data structures and zero candidates under the bounded protobuf grammar.
It does not claim universal absence of a schema. Separate selected-label
integer-address scans find zero absolute64-bitVA and32-bitRVA matches for nine
selected occurrences. Direct code crossreferences remain unproven; a shared
embedded string table or index/relative representation is a next investigation.
No174-to198-bit player layout,32-byte availability semantics, ownership or
missing DataMod namespace value is assigned.

## Five preserved old crash sets

Filename-only inspection found five B41810 crash folders from July/August2022.
Each dump's module list identifies HeroesOfTheStorm_x64.exe version
0.17.0.41810, image size89478144, checksum45759189 and PE timestamp
2016-03-25T19:47:30Z. All five CodeView records identify the same PDB:
HeroesOfTheStorm_x64.pdb, GUID7BF26548-FE37-4F3F-94F0-218512BDB807, age49
(hex31), symbol index7BF26548FE374F3F94F0218512BDB80731. These are module/debug
identities, not a full executable or PDB hash. The original local drive is
unavailable, and no complete executable/PDB was obtained.

The first45 Error-header lines independently agree on B41810/Heroes.17/x86_64
and the generic streaming category e_errorIdStreaming (NGDP:E_DATA_ERROR).
The message identifies neither a particular missing CDN object nor its cause.
Only minidump header/directory/module/name/CodeView metadata is decoded. Dump
memory/thread/exception/context streams and later Error memory sections remain
uninterpreted; full-file hashes treat all other bytes as opaque.

All ten dump/Error inputs remain unchanged:1388192 distinct bytes. The producer
separately accounts2776384 opaque hash bytes and72745 selected metadata bytes.
Root independently decodes documented first-module structures in all five dumps
and checks all first45-line static header claims, with12839 selected bytes plus
2776384 opaque hash bytes. No raw dump, log, source path or process/session data
is published. Primary structure references are retained in the root review.

Fifteen separate .build.info/NGDP/trace files total13364bytes, read twice.
All five manifests are byte-identical740-byte snapshots of EU2.55.3.88481,
BuildKey0534650161f366f2f048320d85b32893 andCDNKeyc53d29ee65044954474c758516b15ab4.
The literal original replay root83d43a8647bb5ca5caa6f2f09064da55 is absent in
those15texts. Weak timestamp-prefix label extraction does not establish that
other metadata is absent. A separate captured-read independent review exactly
reproduces the JSON and bytes without reading Variables, Error or dump files.
These saved manifests do not prove which content the old executable loaded.
The evidence supports old module metadata and newer preserved content metadata,
not an authenticated original41810 BuildConfig or a diagnosed streaming cause.

## Bounded additional primary research

The previous six-operation catalog route is now preserved: three pre2017
default-branch commit queries are empty, one nonrecursive HeroesToolChest list
has133 version directories/builds76003-97039 and no41810. An unsupported tags
endpoint is a connector limitation, not evidence of absent tags. A subsequent
ten-operation archive search finds22 indexed ChoGallPromo occurrences; first8
are localization metadata, not historical reward definitions. Seven exact
returned source bodies are hash-bound, totaling91299measured UTF8content bytes;
two web search envelopes have unmeasured bytes. Neither search obtains a
version-bound2016 or41810 catalog. Branch/index scope limitations remain explicit.

Eight new player-block source/history calls also fail to name the opaque
internals. An old bugfix names fields AFTER the unchanged198-bit block; Mac
platform options belong to a separate event, and a missing-tag fix changes
validation rather than wire reads. Generated Python patches are unavailable
for two commits, so complete historical-diff coverage is not claimed. Frozen
source/report replay is exact and no new correlations or replay inputs are read.

Sources and sanitized receipts are under research/exact-header-98348 and matching
observations subdirectories. Publication bindings preserve executed source bytes
and hashes. Machine-specific private-input paths remain research snapshots,
not portable supported CLIs. No new unit-test or hosted-CI claim is made for
these read-only static observations. Original/R8 and the offline-only constraint
remain unchanged; full migration and deterministic compatibility are unfinished.
