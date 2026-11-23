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
