# Lane and camp targets in TEN_GREYMANE

Three source ping targets have unambiguous producer slots. Ping ordinals are zero-based, and slots and waves are one-based.

| Ping | Loop | Birth | Producer | Slot | Tracker X/Y |
| ---: | ---: | ---: | --- | ---: | --- |
| 15 | 7128 | 6950 | Order, middle lane (3), wave 14, footmen | 3 | 60, 93 |
| 22 | 8319 | 7908 | Order, top lane (1), wave 16, ranged | 1 | 54, 97 |
| 62 | 17230 | 16096 | Chaos, camp 4 capture, melee knights | 1 | 149, 108 |

Predict an ordinary wave from GatesOpen, the build-specific delay and stride, the three lane batches, and each group's unit types and owners. In each lane the two teams spawn three footmen, a wizard and three ranged minions in parallel over three game loops. In the tracker, Chaos precedes Order at every ordinary group tick. The first 41810 wave starts 81 loops after GatesOpen and the stride is 481. Build 98348 uses 2 and 480. Through the recorded core deaths this predicts the loop, type, owners and within-loop order of 6,804 historical and 24,150 current-build births. [Per-replay wave timings](../observations/lane-wave-timing.json)

The first wave of a separate recording supplies exact integer placement templates. The map waypoint direction and a group step of 1.875 give all 18 group leaders on both reference maps. Historical timings and templates recover 1,672 of TEN's 1,680 complete ordinary birth placements, including both pinged lane minions. Other spawns can shift when the placement is occupied. The camp prediction reads the capture statistic, the four authored spawn points and the libMapM mercenary type array. All 38 TEN camp births match their type, team, position and loop. The reference uses the matching spatial slot regardless of iteration order. [Case results](../observations/dragon-lane-roles.json)

Both builds' capture-unit placements and normal-wave coordinates vary in some matches. Once supplied with a generated target history, `rebind_role` verifies an exact producer, slot, owner, coordinates and lifetime before returning a numeric generation. The three historical roles alone do not establish the target indices or recycle values.

Run `python dragon_lane_roles.py --build BUILD --map MAP --template-replay TEMPLATE --case REPLAY SHA256`. Use the template digest listed for that build under `basis` in the case results. Repeated `--case` arguments check additional matches.
