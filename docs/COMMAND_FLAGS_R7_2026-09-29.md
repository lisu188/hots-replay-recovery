# R7 command-flag experiment and current catalog investigation

Date: 2026-09-29.

This is a partial, explicitly experimental replay transformation. No successful HotS playback is claimed. The latest observed client outcome is still R5 rendering Dragon Shire and stopping at displayed replay time 0:04 with Replay Desync. No R6 or R7 client outcome was supplied in this continuation.

## Command flags

The preserved 2016 command flag values differ systematically from both original 98285 reference recordings. The first R6 commands at game loops 61 and 63 use `0x100108` with no explicit ability and a target point. The original current Braxis and Dragon references use `0x80108` for their corresponding command shape. Equal shapes are evidence for a hypothesis, not proof of equal flag semantics.

`repair_command_flags.py` tests deleting each individual bit position that is zero in all source command flags. Seven positions, 9 through 15, tie for the best observed support. Importantly, they produce the identical transformation on every supported flag value in this replay. Their shape-supported mapping covers 4542 of the 4558 source commands:

| Before | After | Source commands |
|---|---|---:|
| 0x100 | 0x100 | 1288 |
| 0x10a | 0x10a | 7 |
| 0x10100 | 0x8100 | 3 |
| 0x100100 | 0x80100 | 606 |
| 0x100108 | 0x80108 | 1915 |
| 0x110108 | 0x88108 | 66 |
| 0x200100 | 0x100100 | 657 |

The remaining 16 commands use source flags `0x80100`. Their model-predicted target value, `0x40100`, is not observed in the two current references. These 16 commands are deliberately left unchanged. The actual flag meanings and the historical location of an enum change have not been independently established.

R7 changes exactly 3247 `SCmdEvent.m_cmdFlags` values. It changes no ability links, unit-type catalog links, unit-instance tags, targets, event order or game-loop values. Its header, map dependencies, lobby, message and tracker streams and every other non-game replay member are byte-identical to R6, except regenerated MPQ integrity metadata. Synchronization payloads and checks are not removed, replaced or disabled.

## Artifact

- Name: `TEN_GREYMANE_client98285_FLAGS_R7_PARTIAL.StormReplay`
- Input R6 SHA-256: `0613acfcdcda173be31a7dbf4b31a985d62304a35547da18b235256738c22f0c`
- R7 SHA-256: `3cedf89c901c98e43201542dba901797c222e9ce36215f4d234bd43dfc66581e`
- Size: 2438170 bytes; 43 Base64 parts.
- Event counts: 104257 game, 155 message, 6614 tracker.
- Status: `partial-hypothesis-not-verified-in-client`.

The larger archive includes native replacement storage; size is not a measure of recovered gameplay. The complete per-event audit is `client-checkpoints/98285-flags-r7/command-flags.changes.jsonl`.

## Tests and independent verification

Locally, 85 focused tests passed: 21 new flag tests, 29 new catalog diagnostic tests and 35 existing unit-tag tests. Two native local generations produced the same R7 digest. An earlier broad local test attempt had three setup/import errors, including an incorrect test module name and unavailable restored fixtures/upstream schema. That invocation is retained in the delivery logs and is not counted as a passing full run.

The corrected complete CI workflow uses all required restored fixtures and the full pinned Blizzard protocol checkout. Run **36556354489**, code commit `5ac8aa268818c64654af21c4c14d74d59ff8557b`, completed successfully: **251 tests, zero failures and zero skips**. Native StormLib, available archive integrity checks, independent mpyq, full observed-payload decode/encode checks and two identical native generations passed. Both CI outputs match both local outputs. The downloaded CI archive's SHA-256 matches GitHub's digest, and all 43 Base64 parts reconstruct the same candidate. Publication commit: `10da5cead2291528932abb9c1e392701d9aa05bd`.

These tests prove the bounded transformation and container/serialization invariants, not flag semantics or game simulation compatibility. No HotS executable ran in these validation environments.

## Lifecycle-aware catalog audit

`catalog_diagnostics.py` joins selection/command snapshot links to tracker identities only when a known unit type is alive strictly before the command tick. It tracks morphs, deaths and recycled identities, rejects inconsistent selection subgroup counts, and excludes same-tick ambiguities. It does not infer live allocation from tracker data belonging to a different match.

The complete audit found 23 unambiguous observed source/current unit-type link pairs and 27 unresolved source types. This is not a complete catalog and does not prove that links are independent of map or dependency context. In particular, the current links for Greymane, Brightwing, Nova and Sonya are not established by the supplied reference recordings. No proposed catalog link is applied to R7.

The initial Dragon tracker snapshots contain 172 source objects and 170 reference objects at loop zero. Exactly 125 objects share unique descriptors comprising type, controlling player, upkeep player and coordinates. Their index offsets include 0, -1, -2, -3, -4, -5, -6, -7, -10 and -12. There is no universal observed offset. Source-only/reference-only descriptors can include moved objects and must not be presented as counts of deleted/added units.

The first affected selection at loop 52 refers to original index 173, recycle 1, type HeroGreymane, catalog link 807. R6's corrected packing does not prove that current live index 173 has the same identity. The first explicit source ability command is later, at loop 133. Neither fact locates the exact first divergent simulation tick.

Full audit digest: `3e201f36b63ab8b9476373219494638daf31b5362ca914bc78f10ae48f03da2d`. The full JSON is retained in the dated delivery package and OneDrive, not replaced by the abbreviated table in prior chat.

## Exact-build game-data acquisition

Three completed workflows used HeroesToolChest/HeroesDataParser 5.1.0, verified against release SHA-256 `d5db68a8659456c287df3ed65d64c4786a6501e8f1c638008c81032e90da9f9d`, to read online CASC data after requiring the reported version to be exactly 2.57.0.98285. The declaration extraction covered 5844 data/dependency files. Exported metadata includes names, declaration order, typed reference candidates, dependency/include ordering and content hashes, but not raw gameplay XML or private replay recordings.

Successful runs: 36553252987 (declarations), 36554302517 (reference identities), and 36554967299 (ancestry and unresolved forward-reference candidates). An initial ordering attempt, run 36553992968, failed because the requested Unit/Abil GUID tables were absent; this negative result was not treated as an empty valid mapping.

The metadata includes 1558 distinct declared unit names and 1323 declared ability names across extracted files. These are NOT verified runtime catalog sizes. Simple declaration ordering and several typed forward-reference models failed independently observed current replay anchors. Consequently no guessed Greymane link, ability number or catalog-wide offset has been used. The exploratory scripts and metadata archives are retained for further investigation.

Blizzard's heroprotocol issue 27 also describes ability links as build-specific data indices, rather than portable names. Data extraction alone does not supply a verified engine index assignment algorithm.

## Next evidence and preservation

A controlled test of `FLAGS_R7_PARTIAL` can establish whether the displayed stopping point changes. The outcome must record the exact file, first error and displayed replay clock; reaching a later time is not proof of original-match fidelity. Initial object allocation, numeric unit/ability catalogs, old synchronization records and changed simulation rules remain unresolved. Do not alter version numbers, infer an R6 client outcome, copy another match's synchronization values or suppress desync checks.

All new code and text checkpoints were published incrementally to main without force-pushes. The CI bundle preserves complete source history through R7 artifact publication. Later session and delivery metadata are retained separately in the dated package. Original and earlier replay files, private donor recordings and raw crash memory are not overwritten or published as new raw inputs.
