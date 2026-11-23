# Reconstructing Dragon Shire command target height

The terrain grid and the building's authored X/Y determine all three snapshot coordinates for 2,179 commands in TEN_GREYMANE. This includes 570 commands to buildings at fractional map coordinates. The same reconstruction reproduced 12,363 command snapshots in fourteen genuine 98348 replays, including 6,133 with fractional X/Y. All fifteen entire game-event members re-encoded byte for byte.

```sh
python terrain_snapshot_height.py DragonShire.stock.s2ma match.StormReplay --build 41810 \
  --overlay DragonShire.41810-layout-HistoricalTalentRules.s2ma
```

Use a matching stock map and physical replay. The optional copy must contain the same decoded `Objects` and `t3SyncHeightMap` as that stock map. Both talent packages passed this check against their respective layouts. The CLI derives X/Y from the placement and first verified building lifetime, hides all three recorded coordinates, restores them, and checks the full game stream. [Per-recording results](../observations/dragonshire-command-xyz.json)

The two maps have version-102 `SMAP` members with a 64-byte header and 249 by 209 four-byte vertices. In the observed cells, multiplying the low 16 bits of each vertex by 16 gives the corner height in the command's fixed-point units. Bilinear interpolation at the authored X/Y gives the command Z. Every admitted building has zero authored vertical offset. Every tested corner is nonnegative and every interpolated value is an exact integer. The verifier rejects unsupported metadata, out-of-grid locations, high-bit heights and inexact building results.

Independent checks on the original and two additional target recordings distinguished the interpolation from other terrain rules. Using the lower vertex alone produced 106 errors in the original and 270 across the two target replays. Each triangular interpolation produced 23 and 12 errors, respectively. Using the other stock layout's terrain at the same X/Y gave an incorrect Z for all 4,741 of these commands. This result establishes why the terrain data matters even where a building's horizontal position agrees. [Independent comparison](../observations/dragonshire-height-comparison.json)
