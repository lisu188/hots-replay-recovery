# Dragon Shire building target coordinates

In TEN_GREYMANE, 2,179 unit-target commands address a verified initial building during its first recorded lifetime. For all 2,179, the command’s X and Y fields equal the map editor’s placement multiplied by 4,096. This includes 570 commands on a fractional position. The same check passed for 9,801 commands across 12 genuine build-98348 replays, including 4,832 on fractional coordinates. Replacing both fields with the prediction and re-encoding reproduced all 13 complete game event streams byte for byte.

The check uses the recorded target tag as an input. It pairs map placements to tracker births with the existing startup-identity check, admits only the enumerated Dragon Shire structures, and stops at the initial death, type change, revival, reinitialization or slot replacement. Events on a boundary loop are excluded. Each axis must be exactly representable as a nonnegative multiple of 1/4096. The command snapshot and tracker birth coordinates are separate data. The tracker stores integer positions and loses fractional placement information.

| Source commands on a verified building | Count |
| --- | ---: |
| Same X/Y on the 98348 layout, with target witnesses | 1,272 |
| Different X/Y on the 98348 layout, with target witnesses | 675 |
| No matching target structure with that editor ID | 225 |
| Matching structure without a target-command witness | 7 |

The transfer matches editor object ID, exact unit type and startup control/upkeep player IDs. It also requires at least one command addressed to the same placement inside its initial lifetime in an independent target replay. On this corpus, each accepted object had witnesses in at least three target replays. All 15 moved objects had witnesses in at least five. Together the 1,947 accepted proposals address 57 objects. The source-schema projection and its inverse recover the 1,146,911-byte original game member. The intermediate SHA-256 is `2eb2774622b3d7fd46e7da104737e7410985ce8f2e2db794bdeca62f44746f64`.

At loop 1203, a source command addresses moonwell 1609 at `(153.5, 143.5)`. Its encoded coordinates are `(628736, 587776)`. The matching 98348 placement is `(150.5, 133.5)`, giving `(616448, 546816)`. A mobile counterexample occurs at loop 2544. VehicleDragon 275 was placed at `(507904, 454656)` in fixed-point units and was targeted at `(489146, 418716)`. Among commands on post-start hero births, 1,020 of 1,020 source snapshots and 14,781 of 14,784 target snapshots lie more than one tracker cell from the recorded birth on at least one axis.

## Run locally

Place the tools alongside the recovery repository’s `map_startup_identity.py` and its existing codec dependencies, with the Blizzard protocol modules importable. Supply the unmodified stock maps and genuine replay files.

```sh
python command_authored_xy.py "$SOURCE_MAP" "$SOURCE_REPLAY" --build 41810
python command_authored_xy.py "$TARGET_MAP" "$CONTROL_1" --build 98348
python project_layout_xy.py --source-map "$SOURCE_MAP" --source-replay "$SOURCE_REPLAY" \
  --target-map "$TARGET_MAP" --target-replay "$CONTROL_1" --target-replay "$CONTROL_2" --rows
python -m unittest -v test_command_authored_xy
```

Repeat `--target-replay` for all twelve controls to reproduce the table. The transfer CLI emits the original zero-based command ordinal, both coordinate pairs and the witness count when `--rows` is selected. Its two replay builds use their respective snapshot tag layouts. Proposals use the physical 41810 replay and authentic 98348 map. The source-schema projection tests only X and Y. Z, target tags, target lifetime in a converted match, target-format encoding and native playback remain unverified by this check.
