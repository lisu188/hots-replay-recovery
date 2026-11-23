# First Anub’arak award in the TEN tracker

The MercCapture opening contains 266 tracker frames. The separate ExtendedSpikesRange map restores selector zero for Anub’arak’s first talent at loop 102. Using this map’s projected catalog, the tracker generator adds the award at loop 103. The continuous private candidate is 15,965 bytes with 267 frames. The next physical source tracker record is a talent purchase at loop 134. [Tracker receipt](../observations/extended-spikes-prefix.json)

The builder checks both whole map packages. All 69 content members other than the affected catalogs match, including the map startup script and placements. It recovers the player and hero from the prior opening, reads original game input 491, independently resolves the target talent from the map and target GameLib, then compares the full added physical frame at source tracker ordinal 244. The standalone 114-byte award becomes 113 bytes when its delta is counted from the preceding loop 87. Re-encoding the entire new target prefix reproduces every byte.

The projected name is AnubarakMasteryExtendedSpikesImpale. Its ordinary retail slot selects AnubarakNerubianArmor. The historical Impale geometry, the assembled catalog at runtime and its effect on later simulation remain unverified. The 675-frame MercCapture fragment remains under its own map identity. The first game input gap is still the opening sound at loop 68.

```sh
python extended_spikes_opening.py TEN MERC_CAPTURE EXTENDED_SPIKES_RANGE MERC_TRACKER_PREFIX ANUBARAK_XML GAMELIB --private-output NEW_PREFIX
```
