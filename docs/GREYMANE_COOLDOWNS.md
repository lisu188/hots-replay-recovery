# Greymane cooldowns on the original Dragon Shire layout

TEN_GREYMANE records two Go for the Throat selections at game loops 6426 and 7074, and one Running Wild selection at loop 9927. The original replay SHA-256 is `e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824`. Each selection has a corresponding named purchase one loop later.

| Rule | Build 98348 | Combined map | Evidence |
| --- | --- | --- | --- |
| Running Wild range | +35% | +35% | The build-41810 talent description and installed build-98348 range modifier agree. Absolute historical dash geometry is unverified. |
| Darkflight and Disengage cooldown modifier from Running Wild | −1 second on each ability | 0 on each ability | The 41810 catalog lists a 5-second base for each ability and describes only range for Running Wild. Blizzard introduced the 1-second reductions in 2022. |
| Disengage cooldown when using Go for the Throat from human form with Running Wild | Talent branch sets 4 seconds, current fallback sets 5 | Talent branch points to the same effect as the fallback | Both the initial and free heroic cast sets invoke this switch. Blizzard documented the heroic-specific cooldown reduction in 2023. The exact heroic-triggered time on build 41810 remains unverified. |
| Go for the Throat base cooldown | 80 seconds | 60 seconds | The 41810 catalog gives 60 and Blizzard recorded the increase to 80 in July 2016. |
| Go for the Throat cooldown restored after the free-cast state | Writes 80 | Writes 60 | On build 98348 the effect explicitly restores the base cooldown. Adjusting both fields preserves its relationship to the restored base. |

The historical JSON identifies both abilities and the level-13 talent by ID. Blizzard's 2022 notes date the talent-specific cooldown addition. Its 2023 live notes identify the later Go for the Throat interaction. [Build-41810 hero catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [July 2016 patch](https://news.blizzard.com/en-us/article/20164442/heroes-of-the-storm-patch-notes-july-12-2016) · [February 2022 balance change](https://news.blizzard.com/en-us/article/23761542/heroes-of-the-storm-balance-patch-notes-february-1-2022) · [November 2023 heroic interaction](https://news.blizzard.com/en-us/article/24031812/heroes-of-the-storm-patch-notes-november-16-2023)

## Rebuild and verification

Use the repository's existing MPQ tooling and StormLib. The builder accepts the previously produced original-layout Mana Addict and Bed of Barbs map with SHA-256 `662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800`. It verifies the pinned build-98348 Greymane XML, build-41810 hero JSON, and earlier map overrides before applying five edits to four records.

```sh
PYTHONPATH="$RECOVERY_REPO" python3 -B build_greymane_talent_map.py \
  --source-map "$TWO_TALENT_MAP" --stock-xml "$GENNDATA_98348" \
  --historical-json "$HEROES_41810" --stormlib "$STORMLIB" \
  --output "$NEW_MAP"
```

The resulting archive is 2,130,976 bytes, SHA-256 `e8d151e5d574babf187e3c0b06cd4b29d2280ac085773afda36a3ebb9c79ffa7`. Two MPQ readers agree on the contents of all 70 members. There are two new XML members, one extended talent member and 67 unchanged original members. Both earlier rules are preserved. Heroes.XmlData 1.1.1 independently opened the physical source and derived maps and compared all four affected records to independently prepared references. Direct and parent-expanded lookups agreed across all 16 comparisons.

A retained negative control used an explicit index on the heroic's `Cost` element. The released reader interpreted it as a nested record and kept the real base cooldown at 80. Both heroic record comparisons detected the mismatch. The corrected map overrides the existing unindexed `Cost/Cooldown` field, preserving the energy cost. The zero for the free-cast window and its separate refund and cooldown-holder paths are outside the five edits.

These results cover the packaged data on the selected 98348 baseline. Historical heroic damage, cast timing, movement geometry, talent selection dispatch, native catalog resolution, map sync checksum and full replay playback still require separate evidence.
