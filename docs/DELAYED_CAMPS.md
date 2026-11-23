# Two late siege captures in TEN_GREYMANE

Both final deaths credit team 1's Kael’thas, primary tracker tag (179, 1). Both are Siege Giants, one at each team’s side of Dragon Shire. The replay supplies the defender's location when it dies. The two markers enclosing each delay are exact.

| Camp and authored center | Last defender death | Team ownership / capture stat | Direct Kael’thas body observation | Inputs around ownership |
|---|---:|---:|---|---|
| 1, (101, 76.5) | 18691 | 18730 / 18731 | (98, 75) at 18720, nominal distance 3.35 in integer tracker coordinates | At 18703, a point command targeted (101.38, 77.54), 1.10 units from the center. A no-target command with ability link 348 followed at 18708. |
| 3, (147, 76.5) | 18983 | 19011 / 19012 | (142, 72) at 18960, nominal distance 6.73, 23 loops before the last death. The next position packet came at 19200. | Unit-targeted the final defender at 18964. Point updates at 18985–18991 approached the center. At 18988 the target lay 0.22 units away. Ability link 348 followed at 19000. |

At camp 1 the last nearby Kael’thas command against a defender preceded its death. No target snapshot placed any live primary hero within twelve units of either center in a window from 64 loops before the final death to 32 loops after the capture stat. Kael’thas's camera had no update during either death-to-stat window. The team-1 globe spawned at the camp location on each capture loop. A pickup statistic for Kael’thas followed six and five loops later, respectively. These stats contain a player ID and omit both globe tag and coordinates.

The first three camp-3 awards in this match were on time and credited Sonya. Before the first, Sonya was sampled at (147, 77), 0.5 units from camp 3, 38 loops before the final defender died. Team 1's two earlier on-time camp-1 kills credit Greymane and Nova. Thus both late cases share a ranged credited killer; directly sampled pre-death proximity differs in the same-site Sonya example. The same no-target command 348 occurred 17 loops after the last death in both late cases. Seven players issued this link across the match. The event supplies no named ability or cast result, and the two ownership intervals differ by eleven loops.

The pinned 98348 Galaxy script searches within radius three and takes 24 uncontested increments from zero. Under the additional assumption of 24 consecutive positive ticks ending at ownership, the first tick would be 18707 or 18988. Neither loop has independent body-position or eligibility evidence. The camp-1 integer sample is near the radius boundary and cannot establish the exact crossing tick. A point-target update near the camp-3 center at 18988 measures the target. Contests, partial progress decay, interruptions and individual participants remain unresolved on 41810.

The original smartcam member has zero candidate timestamp records in either death-to-stat window. The three bracketing records occur at loops 18555, 18888 and 19413; their associated values all match packed unit identities. The first record links Kael’thas with a Siege Giant before the first death. These records carry no XY coordinate.

The source replay SHA-256 is `e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824`. The original map SHA-256 is `e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250`. The two decoded members are `replay.tracker.events` (SHA-256 `1a9a556f9f1fde466d17c4a3a3fbb31cbec8d8086bef97efeb796f1f5175245f`) and `replay.game.events` (SHA-256 `ea69dd77edd02f3ed2c42a2def1faab6dc4d0eb46da291c44f76bfb49a65eed6`).
