# Dragon Shire catapult births

In TEN, Order destroyed the enemy middle keep at loop 17547. Four catapults then spawned at loops 18016, 18497, 18978 and 19459. Applying build 98348's fort rule to the same town deaths and historical wave clock would add 34 catapults. Those extra allocation requests would change the pool of unit indices available to the simulation.

The verifier locates each of the two halls for every lane and side through the map's town initialization and Regions member, then predicts catapult waves from their tracker deaths. Across four build-41810 games, the keep rule predicts all 42 births with the exact tick and owning team. The current rule would add 91. Across 15 native build-98348 games, the current rule instead predicts all 426 births and the keep rule misses 271. The nominal spawn coordinates match 40 of the 42 historical births and 129 of the 426 stock births. Physical placement can move a spawn away from its requested point. [Case results](../observations/catapult-waves.json)

No recording in the 19-game set supplied a wave where the enemy keep was dead but its outer fort remained alive. Blizzard described the pre-change keep reward as one catapult per wave when it announced periodic rewards for forts. Its account and the observed normal-order cases support a map rule that checks the keep directly. [Blizzard's gameplay update](https://news.blizzard.com/en-gb/article/22556628/heroes-of-the-storm-2019-gameplay-updates)

The derivative uses the historical wave-clock map as its parent. It installs a callback just before ordinary minion spawning starts. The installer uses the stock lazy trigger slot; this moves creation of that trigger earlier within the start callback. At build time the generator extracts the unmodified formation and per-unit functions from the pinned local GameLib. In the formation it redirects one per-unit call. In that callee it replaces the town-count and every-third-wave condition with an explicit check of the enemy keep for that lane. Map mode, unit types, alive-catapult cap, unit creation, wait order and post-spawn logic retain their original expressions. The altered path never calls the original per-unit helper. The separate stock fort notification, experience, unit scaling and other combat behavior remain outside this change.

The map contains six towns marked as making the core vulnerable when killed. Each contains exactly one level-three hall. The build verifies 69 unchanged content members. A second build produced identical bytes. A standalone C harness exercises the emitted keep lookup and per-unit condition in all 1,152 combinations, including a destroyed keep behind an intact fort. Native Galaxy scheduling and replay playback remain unverified. [Build and harness checks](../observations/keep-catapult-map.json)

~~~text
python dragon_catapult_waves.py --map MAP --build BUILD --case REPLAY SHA256
python build_historical_catapult_map.py --source WaveClock.s2ma --game GameLib.galaxy --evidence catapult-waves.json --output KeepCatapults.s2ma --stormlib PATH
python verify_historical_catapult_map.py --base WaveClock.s2ma --candidate KeepCatapults.s2ma --game GameLib.galaxy --cc cc
~~~
