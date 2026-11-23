# Historical-layout building command catalog links

Of 2,179 original building-target commands, 1,589 across 17 unit types have a unique observed source link and a candidate destination link witnessed on a live building in the 12 stock Dragon Shire controls. All 2,179 source snapshots encode flags 111 and timer 0. Each admitted target witness has that same pair. The strongest subset has 1,484 commands with a witness in each of two additional recordings.

| Additional stock recordings with a witness for the building type | Source commands | Event 27 | Event 105, sequence absent | Event 105, sequence present |
| --- | ---: | ---: | ---: | ---: |
| Both | 1,484 | 89 | 831 | 564 |
| One | 22 | 3 | 0 | 19 |
| Neither | 83 | 2 | 51 | 30 |

The earlier 33-pair manifest starts from the 98285 R8 partial. The verifier takes the destination-side names and IDs as leads and calculates the original links independently from the authentic 41810 recording. For each ordinal it verifies the source map's numeric object ID, tracker identity, first lifetime, exact snapshot X/Y and loop. The reverse checks include known tracker names in command snapshots and selection subgroups. A known second name blocks the link. The verifier also checks the separately published 98348 reverse-alias exclusion.

Four types account for 590 excluded commands. The original L2 cannon tower link 531 is also used for a dead tower (407 commands). The current L3 cannon tower link 296 has a dead-tower alias (40). The L2 standalone cannon tower (140) and the L3 BLUR/BR vision-blocking gate (3) lack a stock target link in these controls.

All destination IDs depend on the stock build-98348 Dragon Shire catalog. The historical layout package has a different dependency chain and different map-local unit declarations. Its effective runtime catalog and the historical match's target lifetimes remain unverified. The receipt counts source sequence presence. A target enclosing event still needs independent verification of sequence semantics and all other fields.

## Historical map dependency

The original stock archive and the two-talent copy have identical `DocumentInfo` and `UnitData.xml`. Both depend directly on HeroesData and contain four map unit definitions. Stock 98348 instead depends on the Dragon Shire mod and contains seven map unit definitions. The Dragon Shire mod itself depends on HeroesData. Its unit catalog binds the core's petrification ability, specifies the core and tower AI, and defines a petrification missile. Consequently, copying the stock dependency to obtain stock numeric links would also add gameplay behavior. Blizzard documented the new Dragon Shire core mechanic in April 2020. [Catalog dependency comparison](../observations/dragonshire-unit-dependencies.json) · [Blizzard patch notes](https://news.blizzard.com/en-gb/article/23367312/heroes-of-the-storm-ptr-patch-notes-april-6-2020)

`compare_dragon_unit_dependencies.py` reproduces the comparison from the three hash-pinned maps plus the installed 98348 HeroesData and Dragon Shire mod unit XMLs and the Dragon Shire mod's `DocumentInfo`. All arguments and the required files are listed by `--help`. The observed XML layers establish why a build-specific effective catalog is still needed for the historical copy.

## Offline reproduction

Use Python 3.11 with the recovery repository and its pinned Blizzard heroprotocol checkout and dependencies on `PYTHONPATH`. Generate the private original-layout input using `historical_layout_xy.py --rows`. The verifier checks its compact ordinal/loop/object/X/Y digest and re-reads the original recording. It writes only an aggregate receipt by default.

```text
python -B audit_building_links.py --source SOURCE_REPLAY --source-map ORIGINAL_MAP --current-map STOCK_MAP --rows PRIVATE_ORIGINAL_LAYOUT_ROWS.json --roster observations/expanded-current-catalog-comparison-2026-10-18.json --runtime-anchors observations/runtime-catalog-reference-anchors-98348.json --control-root CONTROL_DIRECTORY --external-manifest observations/dragonshire-independent-control-tags.json --external-root TWO_NEW_CONTROLS_DIRECTORY --output-dir OUTPUT_DIRECTORY
```
