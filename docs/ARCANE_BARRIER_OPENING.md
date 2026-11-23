# The first Mana Addict purchase on the combined map

The original replay creates a `KaelthasArcaneBarrierItem` for player 7 at tracker ordinal 249, loop 355. The next record awards `KaelthasManaAddict` to the same player. The translated input already selects the third column at loop 354. The historical item is accounted for in the receipt with its owner and original tag (index 182, recycle 1).

The 98348 talent attaches three behaviors directly. The third supplies an Arcane Barrier ability button with an Execute command. The combined map also restores the historical quest threshold from 20 to 25 both in the quest display and the globe-count condition. Four independent 98348 recordings show the same first-tier purchase and award, with zero units of the historical item type anywhere in their tracker streams. The original rules gave 15 maximum mana per globe and a four-second shield with a 45-second cooldown. [Blizzard's March 2016 update](https://news.blizzard.com/en-us/article/20063493/heroes-of-the-storm-patch-notes-march-29-2016)

The projected tracker therefore records the award at loop 355 and represents the old item birth through the granted ability in the target catalog. Its receipt retains the source ordinal and records zero target unit births for this grant. The resulting 272-frame, 16,491-byte tracker preserves the full prior prefix. The next original event is Tyrande's talent purchase at loop 365.

The prefix assumes that the reconstructed opening produces the same interleaving of tracker events. Allocation after the historical item birth remains open. In particular, the other Kael'thas receives another item at loop 1217 and references it in five later original commands. Those commands still require a verified target translation. The projected prefix does not establish target simulation, activation outcomes, or checksums.

```text
python arcane_barrier_opening.py TEN COMBINED_MAP KAEL_XML TRACKER_PREFIX_THROUGH_242 COMBINED_GAME_DIR PRIVATE_TARGET_CASES NEW_TRACKER_PREFIX
```

PRIVATE_TARGET_CASES contains four pairs of the local path and SHA-256. The hashes and target award ordinals appear in the receipt. A new output file is required.
