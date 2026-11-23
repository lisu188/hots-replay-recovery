# Which tier would award the recorded talent?

In the ordinary 98348 selection handler, the player’s active tier and the column reported by the engine select a cell in the player’s talent table. The script writes that cell’s talent link to `TalentChosen.PurchaseName` and passes the same link to `PlayerAddTalent`. The panel sets the active tier by scanning for the first empty, enabled tier for which the current hero unit meets the configured level. On the talents-enabled level-up path the native talent-level setter and the tracker receive the same custom level value. The panel separately calls `UnitLevel`. The two expressions need not agree on every path. [Installed script and catalog bindings](../observations/galaxy-talent-award-path-98348.json) · [Level-up handler in the tagged GameLib](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/v2.57.0.98348/mods/heroesdata.stormmod/base.stormdata/triggerlibs/gamelib.galaxy#L10474-L10502)

For an offline test, the model uses the prior recorded level, all default tiers enabled, no respec, and the column of the direct hero row at the observed command index. It erases the scoped purchase names before prediction. Each recorded index must point to the active tier before its column can select a talent. Applying this to twelve 98348 Dragon Shire controls restored 66 purchase names in eight controls. The other four contain no purchases by the eight scoped heroes. Re-encoding all tracker events reproduced 5,445,244 bytes in total. All other tracker fields were copied. In a negative control one real Brightwing input at loop 115 was changed from index 1 to index 0. Both are in tier 1. The model predicted Greater Polymorph, which disagreed with the recorded Hyper Shift and failed validation. Engine delivery of the selected column remains unverified. [Study results](../observations/active-tier-awards-98348.json)

For TEN_GREYMANE, assume every preceding historical purchase can be represented successfully. The normal seven-tier sequence then gives a required tier for each of the ten players’ seven choices. Of the 70 purchases, 35 already have a direct target row on that tier, 30 lack a row and five require a different tier. Those five concern four distinct talents.

| Talent | Required tier in this match | Direct 98348 tier | Source loop |
| --- | ---: | ---: | --- |
| Anub’arak, Bed of Barbs | 3 | 2 | 4582 |
| Nova, Explosive Shot | 5 | 6 | 9535 |
| Kael’thas, Sun King’s Fury | 6 | 3 | 11539, 11930 |
| Brightwing, Greater Polymorph | 6 | 1 | 11594 |

Retaining these historical purchases through that path would require at least 28 distinct missing hero/talent entries and four distinct tier changes at the level of the effective table. The remaining 29 distinct existing hero/talent entries satisfy the tier requirement alone. The study uses the pinned direct XML and global defaults. It supplies no inferred column for absent entries and performs no catalog or replay edits. Historical effects, resolved per-player catalog values and synchronization still require separate evidence.

Run the following with Python 3.11, the repository root and pinned Blizzard protocol checkout on `PYTHONPATH`. The eight XML files and the global tier file are identified by hash in the report. The control roster gives paths relative to its replay directory. A single 98348 replay can be checked with `--sha256 DIGEST --witnesses` in place of the roster and reference root. [Code](../research/dragon-talents/project_active_tiers.py) · [Earlier index and catalog checks](SOURCE_TALENT_PATH_41810.md)

```text
python -B research/dragon-talents/project_active_tiers.py --replay TEN_GREYMANE_source_41810.StormReplay --reference-root CONTROL_DIRECTORY --roster observations/expanded-current-catalog-comparison-2026-10-18.json --tier-defaults HeroData.xml --xml abathurdata.xml anubarakdata.xml barbariandata.xml brightwingdata.xml genndata.xml kaelthasdata.xml novadata.xml tyrandedata.xml
```
