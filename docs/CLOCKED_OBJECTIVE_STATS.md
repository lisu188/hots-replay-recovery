# Camp captures, Dragon activations and team levels

In build 98348 the GameTime field on JungleCampCapture uses the clock of the team beacon transfer. The capture statistic appears one loop later. DragonKnightActivated uses the pilot transfer loop for both the clock and the statistic. Across 15 physical 98348 Dragon Shire archives, the reconstructed frames reproduce 260 camp captures and 52 Dragon activations, including their physical time deltas. The 41810 schema omits GameTime. Five old matches reproduce the remaining fields in 41 captures and 15 activations. TEN contributes 13 and four respectively. [Objective measurements](../observations/merc-clocked-objective-stats.json)

The target clock counts from the gate timer in units of 256 per game loop. The verifier derives the gate from the upgrades of all ten players and joins pilot player IDs through the physical setup records and lobby slots, including historical computer slots. It reads map placements to identify the camp and its defender type. Recovered target GameLib, UILib and MapMechanicsLib establish the timer and stat field. The recorded non-stat transitions supply timing. The generator does not simulate a capture or pilot action.

For team levels, the first lobby-mapped teammate supplies the level and its loop. The verifier repeats this using the last teammate and then compares every field and byte of all five notifications, in order. This covers all 210 post-start LevelUp records in TEN. Five old archives qualify with 945 total frames. Twelve of 15 current archives qualify with 2,430. Three current matches contain simultaneous level changes on opposing teams. Their order is outside the implemented model. The final Level score records the end-of-match value and does not establish the advancement times. [Team-level checks](../observations/team-level-frames.json)

```sh
python clocked_objective_stats.py LEGACY_PATHS TARGET_PATHS historical-shrine-start.json MERC_CAPTURE STOCK_DRAGON LIBRARY_DIRECTORY
python team_level_frames.py LEGACY_PATHS TARGET_PATHS historical-shrine-start.json LIBRARY_DIRECTORY
```
