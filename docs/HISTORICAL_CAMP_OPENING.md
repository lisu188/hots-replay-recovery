# First mercenary wave on the historical Dragon Shire layout

In TEN and three other build-41810 matches, gates open at loop 610. Exactly 120 game seconds later, each of the five camp icons appears and its own flag immediately changes to hostile owner 15. Camps initialize in map order. At loop 2532 the 16 defenders appear in reverse camp order and in ascending slot order inside each camp. All four recordings agree on types and integer positions. Fifteen stock build-98348 Dragon Shire recordings independently give the same defender ordering at their modern first-spawn time. [Replay comparison](../observations/first-camp-event-order.json)

The GateOrder map uses five historical CampOwnershipFlag objects. At startup the target library registers each camp birth timer and creates its capture beacon, then searches for a LootBannerSconce. The lookup fails on this layout and disables the camp. The separate HistoricalCamps map schedules the existing timers from the gates callback. Its first birth callback finds flags by their five authored object IDs, enables the camps, creates the ordinary neutral icons, transfers each flag after creating its icon and delegates to the original timer handler. The original handler's defender creation routine waits 0.125 game seconds. The five timers start in stock order. The exact expiry dispatch order on the derivative has only the independent stock recordings as evidence.

| Check | Result |
| --- | --- |
| Independent builds | Both produced 2,159,443 bytes, SHA-256 `5c241e8f9f316909ea237e5dd9f1c4d4ec2e7ea3224d383c596588c7eaf1b9ae`. |
| Archive comparison | Only MapScript.galaxy changed among the 70 content members. Its parent is the preserved GateOrder map. |
| Compiled callback harness | Exercises each of the five possible first timer IDs, duplicate expiry, unrelated timers, condition-only calls and 12 scheduling rejection cases. |
| Opening tracker | All 172 startup births per historical recording match the map projection. Five flag transfers per recording match the target writer byte for byte at the original frame offsets. The separate target-format flag stream is 103 bytes. |
| Resource identity | The map's SHA-256 changed. Its existing DocumentHeader declares `0x2d44411f`. Engine acceptance of that declaration on this derivative remains open. |

The tag projection uses the map's authored flag slots. Icon and defender tag allocations, subsequent captures, AI behavior, engine synchronization and native playback remain open. [Build receipt](../observations/historical-camp-map.json) · [Verification receipt](../observations/historical-camp-verification.json)

```text
python first_camp_event_order.py TEN ARCHIVED_MAP STOCK_MAP CONTROL_MANIFEST --historical OLD1 --historical OLD2 --historical OLD3
python build_historical_camp_map.py GATEORDER_MAP MAPMECHANICS_LIBRARY NEW_MAP --stormlib STORMLIB
python verify_historical_camp_map.py GATEORDER_MAP NEW_MAP LIBRARY_MANIFEST TEN OLD1 OLD2 OLD3 --cc cc --private-output NEW_FLAG_STREAM
```
