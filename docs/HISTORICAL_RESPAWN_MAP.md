# Ordinary hero respawn times on the original Dragon Shire layout

The Greymane map now has a derivative that restores 15 entries in the ordinary death-time table. Three independent build-41810 replays establish whole-second values through level 23. Levels 7–13, 15–21 and 23 differ from the installed build-98348 table. The stock defaults remain in levels 24–30, where historical observations are missing. The normal scaling, cap, mode overrides and special respawn paths still use their original target-library logic. [Historical timer evidence](../observations/historical-hero-timers.json) · [Blizzard's April 2026 balance change](https://news.blizzard.com/en-us/article/24261475/heroes-of-the-storm-live-patch-notes-april-20-2026)

The original map calls InitializeStormMod from its map-initialization event. HeroesLib starts InitializeData without waiting. That routine synchronously invokes the DataDeathTimes trigger. In the extracted dependency libraries the trigger has a declaration, a single creation and this sole invocation. Its own initializer registers no events. The map creates a wrapper immediately before calling InitializeStormMod. When the library invokes the wrapper, it calls the stock initializer function once with the original flags and return value, then changes the observed table entries if the actions ran successfully. The override therefore completes inside the table callback. Inserting writes after the outer map-initialization call would rely on the scheduling of its nested tasks.

This approach allocates one extra Galaxy trigger and changes the function associated with the library's trigger variable. The original initializer has no event registration or TriggerEnable call in the inspected source. The later map and dependency callback order is unchanged in the source. Native trigger scheduling and playback remain unverified.

Only MapScript.galaxy changes. Both MPQ readers agreed on the contents of all 70 members and a separate rebuild produced the same 2,134,122 bytes. An independent check extracts the generated wrapper from the finished archive, removes the two insertions and recovers the exact input script. Its standalone C harness exercised eight combinations of callback flags and stock return values over 31 slots. [Map integrity and changes](../observations/respawn-curve-map.json) · [Callback checks](../observations/map-callback-check.json)

```text
python build_respawn_curve_map.py --source GREYMANE_COCKTAIL.s2ma --library HeroesLib.galaxy --evidence historical-hero-timers.json --output RESPAWN.s2ma --stormlib PATH
python verify_respawn_curve_map.py --base GREYMANE_COCKTAIL.s2ma --candidate RESPAWN.s2ma --library HeroesLib.galaxy --evidence historical-hero-timers.json --cc cc
```
