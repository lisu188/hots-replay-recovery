# Dragon Shire ownership changes in the target tracker format

For TEN the DragonBeaconReset map and four recorded Dragon Knight activation loops yield 21 ownership changes. The output contains 16 shrine and beacon resets plus the five opening mercenary flag transfers. It is a 434-byte standalone build-98348 tracker stream with source timing. [Evidence and frame counts](../observations/dragon-reset-wire.json)

The map places the Sun and Moon shrines at distinct coordinates. Its startup rules create one beacon at each shrine. Those positions and the startup allocation order determine the four persistent unit tags. The map script visits Sun then Moon when neutralizing shrines. The delayed beacon transfers appear in the reverse order in all 67 recorded activations. Opposite callback wake order is a possible engine explanation. TEN’s first two delayed transfers share loop 2530 with the camp opening. Both precede the five camp flag transfers. The writer binds this ordering to that specific recording and clock.

The test fixes the event sequence from the map and activation clocks without using any recorded owner payload for prediction. It serializes the predicted rows with the target schema, using the actual preceding frame time to compare each physical byte range. Five build-41810 recordings verify 60 shrine/beacon resets and 25 flag transfers. Fifteen stock build-98348 recordings verify 208 shrine/beacon resets. All four persistent actors have team ownership immediately before their respective neutral transitions. The historical derivative uses a 16-loop delay and the control maps use 48. [Map logic](DRAGON_SHRINE_CLOCKS.md) · [Mercenary flags](HISTORICAL_CAMP_OPENING.md)

The original activation clocks remain inputs. Regenerating those clocks from the simulation, predicting the native dispatch order on the derivative and rebuilding the complete interleaved tracker remain open.

The SharedBeaconReset derivative uses the existing capture-point trigger. It produces the same 434 bytes under these conditions. [Shared trigger](SHARED_BEACON_RESET.md) · [Second map verification](../observations/dragon-reset-wire-shared.json)

The SignedAnnouncer map combines the signed capture-point argument with the modern Dragon Shire default announcer. Its opening layout yields the same four objective tags and five camp flags. The 293 physical comparisons and the 434-byte TEN output also agree on this map. [Combined-map verification](../observations/dragon-reset-wire-final.json)

```text
python dragon_reset_wire.py HISTORICAL_PATHS TARGET_PATHS DRAGON_BEACON_RESET_MAP STOCK_MAP MAPMECHANICS_LIBRARY observations/historical-shrine-start.json --write-to NEW_TRACKER_STREAM
```
