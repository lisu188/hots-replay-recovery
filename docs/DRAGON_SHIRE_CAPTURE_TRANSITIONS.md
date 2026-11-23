# Dragon Shire camp capture

TEN_GREYMANE records 13 mercenary camp captures. The winning team took ownership of the camp beacon 24 loops after the final tracked defender death in 11 cases. The other two intervals were 28 and 39 loops. Each team ownership change preceded the capture statistic by one loop. All 13 beacons returned to neutral exactly 16 loops after the statistic, or one game second.

Across 14 Dragon Shire replays from build 98348, all 246 team ownership changes also preceded the capture statistic by one loop. All 246 beacons returned to neutral **48 loops after the statistic**. The two-second difference in reset time is reproducible from tracker events. A reset is the beacon’s return to neutral after the reward has already been granted.

The timing rule derived from TEN_GREYMANE was then applied to three independent 41810 recordings identified by `predict_camp_captures.CONTROLS`. From team ownership alone it predicted all 26 capture statistics and all 26 neutral resets. Counts per recording were 16, 6 and 4. Across the four historical recordings, each of 39 team changes matched one capture and one reset. The comparison counted every transition of all five beacons in each recording, including unexpected events and predictions extending past the end. Both counts were zero in the historical and current cohorts.

## Rules recovered from build 98348

| Stage | Behavior and code locations |
| --- | --- |
| Last defender dies | The AI checks that its defender group has zero living members and that it has not already sent the death event. The camp handler resolves the AI group to its camp. A mercenary camp using the capture-point reward path enables the point. See `AILib.galaxy` 744–747 and `MapMechanicsLib.galaxy` 5218–5230, 1663–1667. |
| Who counts | The engine searches a radius of 3 around the beacon for heroic units. The initial filter excludes missiles, items, dead units and hidden units. The second filter excludes benign units unless they have `CapturePointAllowed`. A hallucination requires the allowance and one of the explicit Ultimate Evolution or Storm, Earth, Fire cases. Units count for the faction of their owner. See `HeroesLib.galaxy` 114 and `GameLib.galaxy` 13652–13676. |
| Progress | The point starts neutral at zero. A 1.5-second capture time corresponds to 24 increments, checked every 0.0625 game seconds. One uncontested side advances by one per tick regardless of the number of eligible units. A contest holds progress. On an empty neutral point, partial progress moves back toward zero. Disabled points and beacons with the checked disabling buff skip the tick. See `MapMechanicsLib_h.galaxy` 67–68, `MapMechanicsLib.galaxy` 4944 and `GameLib.galaxy` 1277–1280, 13621, 13652–13657, 13731–13752, 13801–13806, 13927, 13978, 14043. |
| Award and reset | Crossing the signed team threshold changes the beacon owner and emits the ownership event. The camp handler updates camp ownership, disables the point and awards the capture. The disable routine waits three game seconds before restoring the neutral owner. See `GameLib.galaxy` 1236–1237, 1346–1349, 14024–14028 and `MapMechanicsLib.galaxy` 1670–1681, 1721–1723, 5396–5410. |

The 41810 Galaxy implementation was unavailable. The original tracker establishes the event times and team transitions for these 13 captures. Per-tick hero positions and behavior states remain unresolved, including the cause of the two longer intervals. The verifier identifies defenders by authored type and position, follows births and deaths by full tag generation, and matches each camp beacon to its authored captain point.

Run the portable CLI from the recovery repository with the pinned Blizzard protocol package available.

```text
python -B check_capture_transitions.py ORIGINAL_MAP TEN_GREYMANE CONTROL_1 CONTROL_2 CONTROL_3 --build 41810 --historical-cohort
python -B check_capture_transitions.py CURRENT_MAP CURRENT_REPLAY ... --build 98348
python -B -m unittest test_capture_transitions
```

The CLI writes JSON to standard output. It reports map and replay digests, in-game camp numbers, counts and game loops. It does not emit input paths, player names or account IDs.
