# Historical command recording changed in two observable steps

Six public matches contain three distinct ways of recording command references. Builds 65006, 66488 and 68509 all have identical Blizzard field definitions for SCmdEvent, SCommandManagerStateEvent and the two target-update events. The nearest sampled builds span two changes in what the recorder writes. The exact first patch of either change is open. [Original Blizzard definitions](https://github.com/Blizzard/heroprotocol/tree/9af3ea7150f1a8acb53464c92519a9bbcc7a3594/heroprotocol/versions)

| Physical build | Recorded manager states (0 / 1 / 2) | Same-user SCmdEvent evidence |
| --- | ---: | --- |
| 47479 | 27,557 / 1,137 / 25,123 | All state-0 sequences omitted. All 1,137 state-1 values absent from this user's issues. |
| 59799 | 28,553 / 1,838 / 24,824 | All state-0 sequences omitted. 19,282 state-2 values absent from this user's issues. |
| 65006 | 30,779 / 1,583 / 26,041 | All state-0 sequences omitted. No manager or target update has a matching earlier issue from the same user. |
| 66488 | 20,568 / 0 / 0 | All manager sequences omitted. All 36,982 target updates have an earlier issue with the same user and sequence. There is one unique issuing record for 31,528. The other 5,454 sequences occur on multiple issues. |
| 68509 | 35,619 / 0 / 0 | Every manager and all 38,471 target updates point to a unique earlier issue. |
| 75589 | 1,103 / 0 / 0 | Every manager and all 2,044 target updates point to a unique earlier issue. |

In the build-65006 Battlefield of Eternity replay, manager ordinal 362 at loop 66 records state 2 and sequence 4 for user index 1. The complete issue inventory includes sequences 3 and 5 for this user. It contains no issue with sequence 4. At loop 106, state 1 names sequence 7 for user index 3, whose adjacent issued values are 6 and 12. Preserving such references in a format that expects an earlier creator requires recovering the missing issue, including its command and target. [Build-65006 fixture](https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Tests/Heroes.StormReplayParser.Tests/Replays/CustomBattlefieldofEternity1_65006.StormR)

In the next sampled match, build 66488 already records command creators for target updates while its manager events continue to omit sequences. Build 68509 supplies matching sequences on the manager events as well. The samples therefore place these observed changes between 65006 and 66488, then between 66488 and 68509. Replay-specific mode and inputs vary. [Build-66488 fixture](https://github.com/nydus/heroprotocol/blob/08d8f6b68cfa1258dea5da2a8d9e258d98ccba3d/test/replays/towers-of-doom.StormReplay) · [Build-68509 fixture](https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Tests/Heroes.StormReplayParser.Tests/Replays/CustomHGC2018BattlefieldofEternity1_68509.StormR)

## Reproduce

Run the following with the recovery repository on the Python import path and Blizzard’s heroprotocol decoder available. Each command takes an explicit private destination directory. The scorer verifies the public Git blob for each replay, its physical header, its build-specific Blizzard grammar and byte equality after re-encoding the complete game event member. The JSON contains the immutable source URLs, physical hashes and anonymous examples. The six raw inputs total about 10.5 MB.

```text
python fetch_transition_fixtures.py PRIVATE_DIRECTORY
python score_public_command_transition.py HEROPROTOCOL/heroprotocol/versions PRIVATE_DIRECTORY
```
