# Hero presence at historical Dragon Shire camp captures

TEN_GREYMANE and three independent matches on the same build-41810 map record 39 captures. Every final defender death credits a player on the eventual capturing team and names that player’s active primary hero body as the killer. The capture stat follows 25–40 loops later, including 27 captures after exactly 25 loops. The death event supplies the defender’s position. An attacker can deal damage from range.

Only one of the 39 capture loops contains a tracker position sample of a winning hero within four map units of the beacon. It occurs in an independent control at loop 19,680, where Greymane is recorded at (146, 75) for camp 3. Four units is a diagnostic radius around the authored beacon center. The historical eligibility radius has yet to be recovered.

| Camp | Source captures | Four-match captures | Winning hero sampled from final death through beacon ownership | Winning hero sampled on capture loop | Winning hero sampled within preceding 240 loops |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1, siege | 3 | 10 | 3 | 0 | 5 |
| 2, knights | 0 | 3 | 1 | 0 | 2 |
| 3, siege | 4 | 12 | 0 | 1 | 8 |
| 4, knights | 3 | 7 | 2 | 0 | 6 |
| 5, knights | 3 | 7 | 0 | 0 | 6 |
| Total | 13 | 39 | 6 | 1 | 27 |

At the final defender death and at the beacon ownership transition there are zero exact-loop winning hero position samples within four units. In the six intervals with a nearby sample, the credited killer is present in all six and a second winning hero is present in one. TEN_GREYMANE supplies two examples. Sonya (`HeroBarbarian`) appears at (148, 109) on loop 16,080 before camp 4 is captured on 16,096. Kael’thas appears at (98, 75) on 18,720 before camp 1 is captured on 18,731.

Tracker position packets occur every 240 loops in all four games, and list only some units. Matching the main hero body and loop against an independently recorded unit-target snapshot yields 81 comparisons. In all 81, the unscaled tracker coordinates lie within two map units of the target snapshot. Multiplying the packet coordinates by four gives zero matches. Each of the 40 primary hero tags was identified by a matching `PlayerSpawned` stat, birth loop, unit type and player.

A winning player issued a point-target command within four units of the beacon during the preceding 240 loops for all 39 captures. The coordinate belongs to the command destination. During the shorter final-death-to-beacon interval the corresponding coverage is 27/39. A command that targets a confirmed active hero carries a snapshot for that target; this separate signal places a winning hero within four units in 1/39 such intervals. Hero births, revivals and deaths supplied no winning-hero location within four units at either exact milestone. The sparse observations leave contesting players, continuous presence and the individual who triggered ownership unresolved.

The team-bearing tracker marker is the beacon’s control/upkeep owner change to 11 or 12 one loop before the capture stat. The historical camp-specific stat names present are `JungleCampInit` and `JungleCampCapture`; the latter records camp and team. A hostile `MercCoweringDefenderOrientDummy` is born nearby on the final defender-death loop in all 22 siege captures and zero of the 17 knight captures. Its hostile ownership marks the siege defender state. No game event name contains camp, capture, occupancy or channel in these four streams.

```sh
python check_occupancy.py --map original-41810-dragonshire.s2ma \
  --replays TEN_GREYMANE.StormReplay control1.StormReplay control2.StormReplay control3.StormReplay
```

The CLI verifies the four replay hashes and the map hash. Its default JSON reports source, held-out and pooled results at diagnostic radii two, four and eight. Add `--details` for individual capture windows and the directly observed hero samples.
