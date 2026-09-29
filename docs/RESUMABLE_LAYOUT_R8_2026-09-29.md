# TEN_GREYMANE — resumable layout R8

Date: 2026-09-29.

## Result

Generated `TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay` from the immutable published R7 checkpoint. This is a partial format repair, not a confirmed playable replay. The last observed client result remains R5 rendering Dragon Shire and stopping at displayed 0:04 with Replay Desync.

Artifact SHA-256: `4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19`.

Size: 2438570 bytes; 43 Base64 parts. Artifact publication commit: `18e12d356370ed0d8c633a7f02b807451c4eb096`.

## Observed difference

The original replay.resumable.events survived earlier conversions unchanged. Its records contain a four-byte BGRA player-color field between the user byte and the name length. The field is absent from four complete inspected modern streams: two from build 93054 and two from build 98285. Each stream re-encodes exactly under its observed layout and rejects the opposite layout.

All 63 player records match the original replay.details names and color components; the two system records contain white color. CI independently repeats this cross-check using Blizzard's pinned source decoder. Record kinds 1, 2, 3 and 5 are preserved without assigning unproven engine meanings. Existing nonchronological physical record ordering is also preserved.

The first original record is at loop 61. Under the observed modern layout, two color bytes would be interpreted as a name length of 23807 rather than eight. This is a format mismatch, not proof of the native desync cause or first divergent simulation tick.

## Exact change

R8 changes only replay.resumable.events plus regenerated archive integrity metadata. It retains all 65 records and moves their color values into resumable.changes.jsonl. The old payload is 1195 bytes; the new payload is 935 bytes. Adding the audited colors back reconstructs the complete original stream byte-for-byte.

Header, map/lobby data, all commands, flags, unit references, message/tracker streams, load data, camera data and synchronization payloads are byte-identical to R7. Game/message/tracker event counts remain 104257 / 155 / 6614. No synchronization check is removed or disabled.

## Validation

178 tests passed in one local run with no failures or skips: 42 new resumable tests, 29 recovered planner tests and 107 existing diagnostic tests. Native generation was not run locally.

CI run 36578555002 at d961c6f9cfb68cb0ab09945acd846ebbcbb7e234 passed 429 distinct tests with no failures or skips. Native StormLib generated two identical files, verified available archive checksums and preserved HET/BET and 16384-byte raw chunks. Independent mpyq extraction and pinned Blizzard decoding/re-encoding checks passed. The migrated payload matches the local full-stream observation.

The downloaded CI archive matched GitHub's reported digest. All 43 Base64 parts reconstructed the identical replay. A further local independent-reader check compared all 14 archive members and reconstructed the original resumable stream from the audit.

A transcription error in the initial reference summary was corrected to the pinned local observation before CI. No failed test was suppressed.

## Recovered work and persistence

Recovered the unpublished planner from Library backup commit d823ea8 and published its code and 29 tests. CI regenerated its original-only report twice with identical output: 49 unit links, 12557 unit-link fields and 54 original ability links. Without an eligible runtime capture, no target index is guessed or applied. The original standalone planner workflow remains in its backup; the new R8 workflow runs those checks instead.

The new replay was uploaded under a separate filename to both the OneDrive project folder and Multiplayer. Earlier files remain unchanged. Public Git contains code, allowlisted observations, reports and Base64 artifacts, not private donor binaries or crash memory.

## Remaining limitations

No actual HotS execution was performed here. The observed resumable layout is not an official complete protocol schema. R7 command flags remain a hypothesis; unit catalogs, ability identities, object allocation and original simulation behavior remain unresolved. R8 can therefore still desynchronize.

The current searches found existing diagnostic packages but no catalog-output ZIP or HRC98285 export banks. This is not a complete enumeration of all local or OneDrive files.

Test the exact RESUMABLE_R8_PARTIAL file and retain its first error and displayed replay time. Continue validating a genuine runtime catalog capture when available. Parser and archive checks do not establish successful match recovery.
