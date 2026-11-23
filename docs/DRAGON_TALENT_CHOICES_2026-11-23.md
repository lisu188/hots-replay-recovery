# Talent choices in TEN_GREYMANE and 12 Dragon Shire controls

The original records 70 talent purchases across 61 distinct hero/index/name combinations. In the 12 build-98348 controls, **19 of the 70 purchases have a different recorded name for the same hero and numeric index**. The remaining 51 lack an observation at that hero/index. Nine original names, covering 11 purchases, were observed at different indices. This limits the use of R8, which preserves all 70 original indices.

The comparison joins a selection to the unique purchase by the same player one game loop later. The original has 70 such pairs and the controls have 809. The controls agree on map title and target map/mod checksums. The original has the same map title and different map/mod checksums. The JSON records the coverage of each original combination and the observed indices for its name. [Comparison data](../observations/dragon-talent-choices-2026-11-23.json)

| Greymane purchase | Recorded index in 41810 | Observed index for that name in 98348 | Tracker identifier at the old index in 98348 |
| --- | ---: | ---: | --- |
| Go for the Throat | 11 | 9 | `GreymaneDarkflightDisengageRunningWild` |
| Running Wild | 13 | 11 | `GreymaneInnerBeastOnTheProwl` |
| On the Prowl | 15 | 13 | `GreymaneLordofHisPack` |

## A removed talent selected in the original match

Both original Greymanes purchased Concentrated Blast at index 17. The tracker records the purchases at game loops **11490** and **11909**. The next recorded synchronization entries are at **11520** and **11968**, respectively, under the 98348 physical sync profile. These are candidate comparison points for an offline simulation. Which later commands used Gilnean Cocktail, their damage, and the first divergent frame remain open.

Blizzard documented the removal of Concentrated Blast in July 2016. The pinned 98348 Greymane XML has 21 direct talent choices. It contains no Concentrated Blast entry in that tree. The older build-labeled community data describes a bonus to Gilnean Cocktail while Inner Beast is active. Reproducing that effect requires its historical execution rules. [Historical data](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [Blizzard patch notes](https://news.blizzard.com/en-us/article/20164442/heroes-of-the-storm-patch-notes-july-12-2016)

Running Wild illustrates another issue with mapping by name. Its current direct definition modifies the cooldown of Darkflight and Disengage by `-1`, consistent with Blizzard's documented change. The 224970-byte XML member is `mods/heroesdata.stormmod/base.stormdata/gamedata/heroes/genndata/genndata.xml`, SHA-256 `78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff`. Individual declarations still require effective map and mod context. [Blizzard balance notes](https://news.blizzard.com/en-us/article/23761542/heroes-of-the-storm-balance-patch-notes-february-1-2022)

## Reproduce the comparison offline

Use Python 3.11 with `six==1.17.0`. Put this repository root and the pinned Blizzard heroprotocol checkout on `PYTHONPATH`. The script checks the hashes of the upstream decoder and both schemas, so preserve their original LF line endings. Pass the original 41810 replay and the 12 reference archives to the script and compare stdout with the committed JSON. Reference order is immaterial. [Pinned upstream source](https://github.com/Blizzard/heroprotocol/tree/9af3ea7150f1a8acb53464c92519a9bbcc7a3594) · [Comparison script](../research/dragon-talents/project_dragon_talent_comparison.py) · [Reference inventory](../observations/expanded-current-catalog-comparison-2026-10-18.json)

```text
python -B research/dragon-talents/project_dragon_talent_comparison.py --source <original> --references <12 replay paths>
```

The talent audit preserves the apostrophe in the recorded purchase name `Zul'jinAmaniRageAmaniHide`. The comparison reads existing files and writes its report to stdout. Full-match equivalence and native playback remain unverified.
