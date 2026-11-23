# Dragon Shire shrine and beacon timing

The DragonBeaconReset map restores the one-second delay between a Dragon Knight activation and its two beacon owner resets. Every one of 15 activations in five build-41810 Dragon Shire recordings has this delay. Every one of 52 activations in 15 build-98348 controls has a three-second delay. All 67 activations also produce two immediate shrine owner resets. Each physical replay supplied its own header, matching map handles in details and initialization data, opening unit identities and tracker events.

| TEN_GREYMANE event | Loops |
| --- | --- |
| Gates open | 610 |
| First team ownership of the moon and sun beacons | 2011 and 2277 |
| Dragon Knight activations and immediate neutral ownership of both shrine units | 2514, 7734, 11318, 17151 |
| Neutral ownership of both corresponding beacon units | 2530, 7750, 11334, 17167 |

## First objective

The first team capture occurs 1284, 1302, 1319, 1362 and 1401 loops after gates in the five archived matches. The earliest observation bounds shrine availability at **80.25 seconds after gates**. The modern library starts the warning after 60 seconds and enables capture after another 30. Its 15 control matches record the first capture between 1509 and 1883 loops after gates. Blizzard published the 90-second opening in December 2017. [Blizzard patch notes](https://news.blizzard.com/en-us/article/21307436/heroes-of-the-storm-patch-notes-december-12-2017)

Two 2015 guides put first availability at 75 seconds. An earlier guide gives a 45-second start and a 30-second warning. Another observer in June 2015 gives a 40-second start and a 30-second warning. Both historical proposals fit the physical upper bound. [March 2015 timing observations](https://www.heroesfire.com/hots/guide/map-timings-2508) · [December 2015 timing guide](https://www.stormkings.de/im-late-im-late-for-a-very-important-date-map-timings-and-rules/) · [December 2014 Dragon Shire guide](https://gamek.vn/esport/tim-hieu-ban-do-heroes-of-the-storm-dragon-shire-20141213220807173.chn) · [June 2015 Dragon Knight guide](https://www.gameskinny.com/tips/robs-dragon-knight-guide-how-to-wreck-forts-and-crush-enemy-heroes-on-dragon-shire/)

The first two multi-user transmission completion groups in the five historical recordings span gates +804 to +866 and +1275 to +1290 loops. Their respective transmission IDs differ by recording. In the earliest-capture control the IDs are 2 and 14. Its ID 1 completes for a single player at gates +307. The equivalent first two multi-user groups in the modern controls span +1063 to +1090 and +1547 to +1555. Completion events record player acknowledgments. The payload alone supplies neither the dialogue identity nor the callback start loop.

Both the archived map and GateOrder call the external map-mechanics tower initializer and contain the same editor trigger file with 177 references to the external MapM library. The sole direct document dependency names HeroesData. The verifier checks the script, archive list and expected library member paths. Recovering the 41810 HeroesData timer implementation or a build-specific recording of the opening countdown would distinguish the remaining candidates. The derivative keeps its parent’s existing first-objective behavior.

## Offline map

| Item | Value |
| --- | --- |
| Parent | HistoricalCamps, SHA-256 `5c241e8f9f316909ea237e5dd9f1c4d4ec2e7ea3224d383c596588c7eaf1b9ae` |
| Output | DragonBeaconReset, 2,170,700 bytes, SHA-256 `4fc0c3bf21a2b96eda9d8d03f3a309256bf6aacf4715c1a1fc71700ae8edb2c8` |
| Output MapScript.galaxy | SHA-256 `6a59cfb960fa2ac4fc8fe2ab0e55f35d54f327c53c24a68783eff1f42cfde8a6` |

The builder replaces the Dragon Knight channel-finish callback at its existing MapMechanics trigger registration. The callback retains its original global, event, condition, registration position and actions. Only the capture-point disable call in its obelisk loop changes. Its map-local worker preserves the enabled guard, hide signal, asynchronous per-index argument capture and owner update. The worker uses a one-second game-time wait. The stock capture-point helper continues to handle all other callers. The first Dragon Knight completion allocates one dedicated helper trigger. Its effect on subsequent engine handle allocation and synchronization remains unmeasured.

Two archive builds were byte-identical. Two readers agreed on the map script. All 69 other content members matched HistoricalCamps. The builder requires the canonical SHA-256 of the full historical observation report, distinct replay identities, and increasing activation loops after gates in each replay. Four negative cases replace a replay identity, duplicate an identity, duplicate an activation loop, or substitute repeated loop zero. All four are rejected.

The verifier reconstructs the parental script and compares the emitted callback, registration, worker and wrapper with the target Galaxy sources. A C harness dispatches two copies of the emitted worker on independent POSIX user-context stacks and suspends both at their actual wait calls. Two intervening calls exercise the disabled and out-of-range guards and overwrite the shared argument. Both original owners persist through loop +15. At loop +16, the harness resumes Moon before Sun, matching the observed beacon write order after the Sun and Moon shrine resets. Each worker changes the owner of its own beacon. A later dispatch reuses the same helper trigger with the same delay. The harness supplies the wake order explicitly. Native Galaxy compilation, relative order against the historical camp timers, and complete replay playback remain unverified.

## Reproduction

Run `verify_historical_shrine_start.py` with the original 41810 map, GateOrder map, extracted 98348 script directory and two private JSON dictionaries mapping archive SHA-256 to replay paths. It emits the sanitized historical and target observations. Run `build_dragon_beacon_reset.py` with the HistoricalCamps map, extracted GameLib and MapMechanicsLib files, the resulting observations JSON and a fresh output path. Run `verify_dragon_beacon_reset.py` on that output with the same physical inputs and a C compiler supporting POSIX `ucontext`. The command-line tools accept `--help`. They use the project's MPQ helpers and StormLib.
