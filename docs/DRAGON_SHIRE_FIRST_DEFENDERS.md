# The first Dragon Shire mercenary wave

The original map supplies the types and positions of sixteen neutral defenders at five camps. Both layouts specify four siege giants, nine melee knights and three ranged mages. The verifier loads each map's spawn points, builds the expected multiset of types and positions, then finds the first complete wave in the physical tracker's unit births.

| Match cohort | Gate-opening loop | First defender loop | Game time after gates |
| --- | ---: | ---: | ---: |
| TEN_GREYMANE, 41810 | 610 | 2532 | 120.125 seconds |
| All 14 stock 98348 recordings | 610 | 1044 | 27.125 seconds |

The 98348 siege and knight registrations each use the 30-second initial timer. The birth trigger fires three seconds before expiry, and the creation routine waits 0.125 seconds before making the first units. The result is 434 loops at 16 loops per game second, matching every stock control. The original interval is measured directly from TEN_GREYMANE. Its internal timer settings remain unknown. [Per-replay results and script locations](../observations/dragonshire-first-defender-wave.json)

Preserving the original layout and enabling the current camp timers alone would make the defenders appear 1,488 loops early. A reconstruction must also preserve the historical flags and create the minimap icons at loop 2530, before the defenders appear at 2532. First attack, camp capturability, reward behavior and historical respawn timing require separate evidence. [Original capture sequence](ORIGINAL_CAMP_EVIDENCE.md)

```sh
python verify_first_defender_wave.py original.s2ma TEN_GREYMANE_source_41810.StormReplay --build 41810
python verify_first_defender_wave.py current.s2ma control1.StormReplay control2.StormReplay --build 98348
```
