# Native 98348 schema and current ClientInfo wire binding

Offline inspection of the installed 98348 executable recovered a complete BSN
metadata container and identified a concrete boundary error in the earlier
observed current-player profile. No game process or client DLL was loaded.
This checkpoint establishes current serialization facts; the original 41810
player layout and a complete replay migration remain unfinished.

The installed executable is 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Its embedded container occupies file offsets 43,169,040 through 43,560,672
(391,633 bytes), SHA-256
`ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741`.
The five big-endian header words are version 7, an uninterpreted zero word,
8,330 type IDs, 67,244 type-info bytes and 257,729 dump-info bytes. Independent
framing checks reproduce the section geometry and known string anchors.

Public community BSN source from a different Blizzard game suggested the
container grammar. It is a hypothesis source, not an authenticated HotS source
release. The pinned files and exact source lines are recorded in the separate
provenance receipt. Acceptance rests on validating the actual HotS container:
all type-record boundaries, child references, dump references and complete
static name starts. Native member-memory offsets and header bit 6 remain
uninterpreted.

The native `Battlenet::Client::S2GameDefines::ClientInfo` record has 18 ordered
fields. After its talker choice, the observed invalid-choice branch contains:

| Field | Observed encoded width |
|---|---:|
| `m_talkerNetworkId` | 8 bits |
| `m_voiceSessionId` | 64 bits |
| `m_profileAddress` | 96 bits |
| empty `m_relevantPermissions` count | 31 bits |
| Total for this observed branch | 199 bits |

The earlier `current-tail` profile consumes the first network-ID bit as
`secondary/present`, then calls the remaining 198 bits opaque. All 222 player
records in the 21 genuine current-build controls have this first bit zero and
an empty permissions list. A separate native decoder matches 13 surrounding
anchors, every player end boundary and exact consumed-bit re-encoding in all
222 records. Existing initData/details identity, slot and seed checks pass.
These controls cover 20 NGS replays and one EU reference; this run rechecks
their build/root and structure, without repeating their full game-event decode.

A single-bit RAM mutation demonstrates the practical difference: changing only
the first network-ID bit preserves the native record end and exact re-encoding,
while the earlier observed profile rejects the member. The mutated body is
synthetic, remains in RAM and is not published as a genuine replay.

`native_clientinfo.py` provides an explicit `clientinfo-98348` profile using
only the authenticated 104-type ClientInfo closure. It accepts replay-member
bytes and a starting bit, with no game installation or executable loading.
Private fields and tokens disable their representations; the summary and
existing-Tail adapter expose aggregate structural checks. The encoder refuses
changed consumed bits. Fourteen focused tests cover all talker branches,
nonempty permissions, optional fields, all network-bit alignments, invalid
schema/input bounds and read-only reconstruction.

The portable implementation freshly checks the same 21 controls and 222
players. A separate reviewer independently parses all 8,330 metadata records,
recovers the exact 104-type closure and reproduces every consumed player bit.
Thirty-one research tests pass, alongside nine additional independent malformed
metadata checks. The portable 14-test module is registered through the existing
root test discovery; CI additionally checks ten actual EU ClientInfo records.
The subsequent hosted result must be recorded separately from these local
checks and the earlier 894-test milestone.

The native metadata also proves that the `ClientLicenses` list uses 32-bit
`License::Id` values, while the resource-map type follows a separate 64-bit
BattlePay license identifier. Those types must remain distinct. Their names
alone do not establish ownership or the meaning of the observed 32-byte
availability rows. The map-header graph names `m_mapNamespace` and
`m_resourceList`; it does not recover the missing target DataMod namespace.

The original 174-bit region remains unbound to an authenticated 41810 native
schema. A shorter permission-count representation is a hypothesis only; no
zero extension, insertion, default or cross-version transformation is admitted.
The four-call search for an older typed ClientInfo found different structures
and host declarations, without a 41810 wire-width binding.

Metadata-only analysis of the five preserved old dumps finds two captured
ranges within the old executable image, 1,032 and 4 bytes at relative RVAs
`0x02036E40` and `0x020399E0`. No first PE-header page is covered. The pointed
memory contents and custom stream 4096 remain unparsed. Range coverage does
not identify a schema or establish recoverability of the complete old image.

The official EU manifest fetched at 2026-10-18 22:12:45 UTC still advertises
2.57.0.98348 with BuildConfig `a64c9b7ebf1c6a811ffefad97865ed80`.
The earlier native/crash milestone at `3e5ebb7` passed all three complete CI
lanes: 894 tests per lane, four declared Windows skips and 38 Linux skips.
Those hosted runs did not inspect the installed executable or private dumps.
Its source-only backup was uploaded and freshly checked against cloud size
and QuickXor metadata; no independent remote SHA-256 claim is made.

Raw executables, schema blobs, dumps, logs, donor replays and private player
values stay outside Git. Only our source, selected static schema projections
and sanitized checks are published. Original and R8 hashes are retained;
R8 still declares 98285. Full conversion and deterministic compatibility are
not established, and HotS remains unlaunched.
