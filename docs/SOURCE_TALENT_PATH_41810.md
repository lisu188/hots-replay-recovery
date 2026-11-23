# Recovering the original talent selections

The source decoder rebuilt all 70 talent indices in TEN_GREYMANE after erasing every `SHeroTalentTreeSelectedEvent.m_index`. Encoding the complete 104,257-event game stream then reproduced all **1,146,911 bytes** of the original member. Its SHA-256 is `ea69dd77edd02f3ed2c42a2def1faab6dc4d0eb46da291c44f76bfb49a65eed6`. Other event fields and the tracker come from the original recording. [Recovered selections](../observations/source-talent-path-41810.json)

For each selection, the decoder uses the explicit user/player setup and recorded hero to find the same player's unique named purchase one loop later. It looks up that name in the pinned 41810 community export. The exporter sorted the tree by tier and column and stored the options grouped by unlock level. Concatenating those lists in numeric level order recovers the observed indices for this match. The whole-member comparison checks that interpretation against the original encoding. [Historical catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json)

As a negative control, exchanging only the first two entries of Anub'arak's level-one list in memory changed the recovered selection on loop 102 from 0 to 1. Exactly one byte in the rebuilt member then differed from the original.

Three purchases declare prerequisites in the export. Each player had already purchased the required talent. A prior recorded level can exceed the unlock level. Brightwing selected Continuous Winds on loop 16,696 at level 21, one level after it unlocked. The report preserves both levels. The source-only command requires every game selection and tracker purchase to pair. A separate six-replay check found matching indices for 401 paired selections across 30 heroes. One control also had four tracker-only purchases after a user left, for which no selection index could be checked.

## Reproduce

Run with Python 3.11, the original replay and the exact `heroes.json` from the linked revision. The CLI checks both SHA-256 hashes and writes the report to stdout. It reads the replay through the repository's offline MPQ reader. The reusable `restore_talent_indices` function accepts selection events whose payloads have already been erased and returns the recovered event stream in its original order. [Source decoder](../source_talent_path_41810.py)

```text
python -B source_talent_path_41810.py --source TEN_GREYMANE_source_41810.StormReplay --catalog heroes.json
```

## Why index zero needs different handling in 98348

Anub'arak selected index zero on loop 102. The source tracker recorded Extended Spikes on 103. A 98348 control instead recorded Nerubian Armor at that index. The installed target XML retains an Extended Spikes declaration outside the 21 direct tree entries. It adds two periods to each of the two Impale effects and declares seven damage modifiers of `+0.25`. Blizzard documented the added damage in May 2016, after build 41810, and removed the talent from the tree in March 2017. Copying the old index or enabling the complete retained declaration would therefore introduce documented differences. [May 2016 change](https://news.blizzard.com/en-us/article/20120032/heroes-of-the-storm-patch-notes-may-17-2016) · [March 2017 change](https://news.blizzard.com/en-us/article/20581822/heroes-of-the-storm-patch-notes-march-14-2017)

The early source description specifies 25% more Impale range. Its underlying 41810 effect arithmetic and a valid 98348 selection path remain open. Loop 128 is the next recorded synchronization checkpoint. The reconstruction supplies historical inputs for a future comparison there. Full-match simulation and native playback remain unverified. [Designer description](https://news.blizzard.com/en-us/article/16152248/developer-insights-burrowing-deep-with-anub-arak)

## Encoding recorded names for 98348

The eight target hero files contain 171 direct talent-tree entries. Fourteen source purchases have the same name at the old position, 26 have that name at another position, and 30 have no row for the historical name. Seven of those 30 purchases still have a separate talent declaration in the same hero file. Both the document position and the observed wire indices appear for each source purchase. [Per-selection tree comparison](../observations/target-talent-tree-98348.json)

An independent check erased the indices of 66 selections by the original match's heroes in 12 current Dragon Shire controls. The tracker names and XML positions restored all 66. Eight controls contained selections by Anub'arak, Brightwing, Greymane or Sonya. The other four served as encoder controls. After preserving the other 743 indices and the rest of each event, the 12 reconstructed game members matched all 25,375,850 original bytes. This corpus supplies no wire-index witnesses for Abathur, Kael'thas, Nova or Tyrande.

Eleven historical purchases match both a direct target tree entry and a name/index pair recorded in those controls. Their indices all change. Using the original event's numeric user slot and immediate delta, the native-profile and schema-based encoders produced the same seven-byte frame for each. The remaining 59 purchases lack this evidence. A candidate's slot still needs a target player binding and its talent still needs historical effect equivalence. The Python API returns individual frames keyed by original event ordinal. The CLI emits the public result for each selection. [Frame encoder](../research/dragon-talents/project_target_frames.py) · [Results for all 70 selections](../observations/target-talent-frames-98348.json)

For example, Nova selected Explosive Shot at level 13 on loop 9535. Its name and literal position 14 survive in the target tree, where it occupies tier 6 with a global default unlock level of 16. The target ledger records both levels. It does not predict the actual playback decision.

Static analysis of the pinned 98348 executable identifies `CHero.TalentTierArray` at body offset `0x488`. The registered 12-byte entry has `Tier` at offset 0 and `Level` at 4. On the selected admission path, a tier match and a vacant selection cell lead to an unsigned comparison of the function's third argument with this `Level` (RVAs `B0E850` through `B0E85B`). IDA and objdump agreed on all 35 instructions of the 122-byte window in the statically transformed text. Which value the simulated player would supply on loop 9535 remains unresolved. [Earlier state-write analysis](NATIVE_TALENT_STATE_WRITE_2026-10-27.md)

To reproduce the tree comparison, pass the eight XML members named by their SHA-256 in the JSON. Include the pinned global `HeroData.xml` to reproduce the default-level fields. The 12-control observations and recovered source path are already in the repository. [Tree projector](../research/dragon-talents/project_target_tree.py) · [Control observations](../observations/dragon-talent-choices-2026-11-23.json)

For the frame encoder, use Python 3.11 with `six==1.17.0` and put both this repository root and the pinned Blizzard checkout on `PYTHONPATH`. Keep the upstream protocol files in their original LF form. [Pinned upstream](https://github.com/Blizzard/heroprotocol/tree/9af3ea7150f1a8acb53464c92519a9bbcc7a3594)

```text
python -B research/dragon-talents/project_target_frames.py --source TEN_GREYMANE_source_41810.StormReplay --tree-report observations/target-talent-tree-98348.json
```
