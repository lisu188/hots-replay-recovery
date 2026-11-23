# Building coordinates for the historical-layout conversion

For the Dragon Shire package `662a90d5…79b800`, use the source X and Y for the 2,179 verified building-target snapshots. This covers 68 buildings and 570 fractional positions. Applying the coordinates derived from this package reproduces the complete 1,146,911-byte source game stream. The result applies to the initial source lifetime, including the observed target tag and recycle. It leaves 10,286 other source unit-target commands outside its scope.

The package and the original map have the same 540,292-byte `Objects` member, SHA-256 `5b1f268a147bc854a1d0321826f9e055f45aa690cb970f0e703c5e8cf01476a9`. Relative to stock 98348, 15 moved buildings account for 675 source commands. All 675 match the historical profile at the same event ordinal, loop and editor object ID. Another 225 source commands lack a compatible stock target structure. The historical layout supplies the original placements for those commands too.

At loop 2544, the Dragon Knight vehicle’s command snapshot differs from its authored spawn by several map units. The profile excludes vehicles and other mobile units. Converted-match target lifetimes, simulator state, Z and native playback remain open.

With the command-coordinate and startup-identity modules and the replay codec on `PYTHONPATH`, run

```sh
python historical_layout_xy.py --original-map "$ORIGINAL_41810_MAP" \
  --historical-map "$HISTORICAL_RULES_41810_LAYOUT_PACKAGE" --source-replay "$TEN_GREYMANE" \
  --stock-map "$STOCK_98348_MAP" --rows
```

The stock comparison and per-ordinal rows are optional. Each row gives the zero-based game-event ordinal, loop, editor object ID, X and Y. The compact JSON encoding of the rows has SHA-256 `9cfa8a1dbe50fed97167485590661060982a5aed5d2db586563910492050eccd`.

Two additional genuine 98348 replays independently verified the same coordinate rule on the stock layout. Among 13,107 unit-target commands, 2,562 eligible building snapshots matched exactly, including 1,301 fractional coordinates. Both complete game members reproduced byte for byte. Their replay hashes are disjoint from the original 12-control roster. The full 14-replay current sample now covers 12,363 eligible commands, including 6,133 fractional positions.
