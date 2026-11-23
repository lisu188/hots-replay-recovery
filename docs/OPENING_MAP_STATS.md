# Dragon Shire map statistics at loop zero

The converter constructs 18 target tracker frames using the map alone. GameStart uses the two map dimensions. Twelve TownStructureInit frames use the town registration order, owning team, lane and the exact position of the only town hall within each region. Five JungleCampInit frames use the registered captain points. Galaxy fixed-point coordinates preserve fractional positions. The dimensions in MapInfo also agree with the terrain vertex grid.

The build-98348 SupportLib member (SHA-256 `b7578aac7284cbc6bed62b2b4fde267615f99bc0e3703fce31a32d5835a55a80`) emits these fields from the full map bounds, the registered town structure spawn points and the camp captain points. GameLib registers a structure's unit position as its spawn point. No replay statistic supplies a value to the generator.

Against 15 stock 98348 recordings, all 270 predicted frames matched their individual physical byte ranges. The KeepCatapults map produced the bytes of all 72 corresponding frames in four original 41810 recordings. Each 18-frame projection is 2,152 bytes. Their aggregate hashes differ between the two maps because the startup positions changed. The output is a sparse tracker stream. It omits the intervening player statistics. [Per-recording evidence](../observations/opening-map-stats.json)

Run `python dragon_opening_map_stats.py MAP REPLAY REPLAY_SHA256 BUILD --output NEW_FILE`. Use build 41810 for historical-layout comparisons and 98348 for the stock target. The output path must be new.
