# Point issues and their immediate updates

TEN contains 1,248 implicit point issues among 4,558 `SCmdEvent` records. All 1,248 carry an explicit per-user sequence and an X/Y/Z position. Ability, other unit and unit group are absent. The 98348 representation adds an optional vector, absent throughout the qualified projection. The converter preserves each original coordinate including Z, sequence, user, loop and full game-stream ordinal on the GateOrder historical layout. Six later occurrences reuse a per-user sequence already seen on a qualifying TEN issue.

| Original flag | Projected 98348 flag | TEN issues | Physical 98348 issues with that flag |
| --- | --- | ---: | ---: |
| `0x100108` | `0x80108` | 1,175 | 514,492 |
| `0x110108` | `0x88108` | 66 | 1,843 |
| `0x10a` | `0x10a` | 7 | 2,969 |

The 24 genuine 98348 recordings also contain 14 issues of this shape with flag `0x810a`. Under the earlier single-zero-bit deletion model, requiring the independently witnessed first-issue mapping and membership in the complete observed target set leaves seven possible deletion positions (9–15). All seven give the same three words on these original inputs. This evidence establishes a reproducible flag projection. The historical meanings of the individual bits and the selected gameplay order or ability still require independent reconstruction. [First-issue controls](FIRST_POINT_COMMANDS.md)

The native writer reproduced all 519,318 control issue frames across 10,386,360 bytes at their original boundaries. The original partial build-98285 R8 already contains the 1,248 projected issue records at the same source ordinals. At least one other same-user manager or target-update record echoes the sequence of each eligible issue in the 98348 recordings. Only 16 of the 1,248 TEN issues have such an explicit numeric echo. The distinction matters when assembling the intervening command stream. [Issue evidence](../observations/implicit-point-issues.json)

## Recovering an absent target-update sequence

For 311 TEN issues, the same player’s next command-family record changes the target point **in the same game loop**. Each preceding issue has ordinary flags `0x100108` and an explicit sequence. The historical target updates (event 104) omit their sequences. All 311 remain absent in R8.

The verifier saves the preceding ordinary issue separately for each user. A reset (25), new issue (27), manager record (103), point update (104) or unit update (105) consumes the previous candidate. It admits only a same-loop target-point update whose point differs from its immediately preceding ordinary implicit issue. On 98348 the corresponding flag is `0x80108`. The update’s own sequence is held out until after admission and prediction.

Across all 24 controls, all 13,081 eligible updates carried exactly the preceding issue’s sequence. Encoding each prediction at its physical game-stream boundary reproduced 209,296 bytes. In the TEN projection, the 311 supplied values produce a 5,077-byte sparse stream with SHA-256 `9a553909c1cb2af25f510552fb8dc1b8297d5533e91a63716d1696648906e358`. One same-loop update overlaps the earlier first-command interval. Other issuers, intervening commands, unchanged coordinates and later loops require separate evidence. [Update evidence](../observations/immediate-point-updates.json)

## Reproduction

```text
python implicit_point_issues.py SOURCE GATE_MAP --control-manifest PATHS --retained-r8 R8
python immediate_point_updates.py SOURCE --control-manifest PATHS --retained-r8 R8
python -m unittest test_implicit_point_issues
```

`PATHS` maps the 24 SHA-256 values in `observations/first-sync-game.json` to local replay files. Both emitters accept `--private-output` for sparse bytes and `--private-ordinals` for the original zero-based indices. Their respective `generate(source, gate_map)` and `generate(source)` functions return a dictionary of named target rows keyed by original game ordinal, standalone bytes and an aggregate receipt. Recalculate time deltas after interleaving rows and verify overlapping predictions agree. Simulation state and gameplay effects remain untested.
