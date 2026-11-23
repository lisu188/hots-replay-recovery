# Hero revival records on the historical Dragon Shire layout

The converter emits all 45 TEN primary-hero revival records as a standalone build-98348 tracker stream. The source-unit death or revival records supply none of the four output fields. Opening unit index and recycle come from the lobby model, timing from player death and level statistics plus independently reconstructed historical timers, and the end-of-match cutoff from the destruction of the core. Original revival records then check the result. Every projected event has a different game loop. [Per-replay results](../observations/hero-revive-wire.json)

The original and stock Dragon Shire MapInfo files both link the ten active player slots to authored StartLoc object IDs 3–12. GameLib lines 10279–10291 assign the start location by the player's rank within the appropriate team, with an offset of five for Chaos. The ordinary timer passes that point to the respawn function at line 17323. The tracker stores its integer map coordinates. Object ID 12 and the unrelated ordinary point 794 have the same display name. Reading the actual MapInfo start-point field resolves that ambiguity. [MapInfo player structure](https://github.com/ggtracker/sc2reader/blob/master/sc2reader/objects.py#L567-L577)

Across fifteen genuine 98348 Dragon Shire controls, physical re-encoding reproduced all 270 native revival frames in place, spanning 6,084 bytes. The ordinary model independently predicted all 28 applicable control revivals including the unit tag, time and both coordinates. These frames span 636 bytes. Heroes outside the eight TEN types were included in wire-format validation only. The TEN stream occupies 1,051 bytes and its target decoder recovers all 45 ordered records. Merging the records with other tracker events still requires reconstruction of cross-event ordering and deltas. Native playback and simulation checksums remain unverified.

```text
python hero_revive_wire.py --case TEN.StormReplay SOURCE_SHA256 41810 --map RESPAWN.s2ma --historical-timers historical-hero-timers.json --output historical-hero-revives.bin
python hero_revive_wire.py --case CONTROL.StormReplay CONTROL_SHA256 98348 --map STOCK.s2ma --heroes-lib HeroesLib.galaxy --game-lib GameLib.galaxy
```
