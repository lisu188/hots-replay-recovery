# Sequences after a recorded point issue

Three event patterns recover 382 additional sequence values for TEN on the GateOrder layout. There are 371 point updates (event 104) and 11 command-manager transitions to state 0 (event 103). The original build-41810 recording omits each value, as does the earlier build-98285 R8. The projection preserves the original ordinal, game loop, player, point or manager state.

| Observed pattern for one player | TEN | First 8 controls | Remaining 16 controls |
| --- | ---: | ---: | ---: |
| Later update in an uninterrupted run of point updates whose first changed point was on the issue loop | 364 | 5,530 / 5,530 | 15,372 / 15,372 |
| First update on a later loop; only point updates between this issue and the next consecutively numbered issue | 7 | 2,212 / 2,212 | 4,857 / 4,857 |
| State 0 after the first pattern’s same-loop anchor; final update and manager share a loop, then the next issue has the next sequence | 11 | 730 / 730 | 1,535 / 1,535 |

Every row predicts the preceding ordinary point issue’s sequence. The rule for the manager also admits a manager directly following the initial same-loop anchor. Only the original’s implicit point issue with flag `0x100108` and its observed 98348 counterpart `0x80108` qualify. Reset, manager, unit update and new issue events interrupt a point-update run. Checks for consecutive numbering read the original player’s next issued command. Candidate construction ignores optional values on every manager and target update. The encoded data passed individual physical-frame comparisons for all 30,236 admitted current records, covering 463,391 bytes. [Per-recording evidence](../observations/command-interval-sequences.json)

The discovery and comparison groups comprise the first eight and remaining sixteen replay hashes in sorted order. One comparison-group point update contradicted the broader uninterrupted-run rule, even though the enclosing issues were numbered consecutively. Checking only the immediately previous issue for the first later update also fails on five current records. The broader consecutive-issue rule for managers failed 187 times. These counterexamples are retained in the receipt. The selected patterns passed both groups; deterministic replay execution remains unverified.

A second candidate tracked one outstanding issued sequence per player from a reset or the start of the match. It cleared a sole entry at a state-0 manager record, and retained ambiguity when multiple issues accumulated. All 32,222 qualifying modern point updates and 9,867 state-0 manager rows agreed. In TEN, two explicit point updates contradicted that same model. Its 20 missing point-update and 22 missing manager values therefore require separate evidence.

The 382 source ordinals are disjoint from the previously recovered 311 immediate same-loop updates. The combined stream already contains ordinals 29 and 31 at loops 64 and 65. The other 380 extend match coverage. The standalone fragment occupies 6,108 bytes and has SHA-256 `ce52fff7532982463b4211617a7c4fb7a1fbea7081a58b298fa8684af1ab9431`. [Immediate same-loop rule](IMPLICIT_POINT_ISSUES.md)

```text
python command_interval_sequences.py SOURCE --control-manifest PATHS --retained-r8 R8
python -m unittest test_command_interval_sequences
```

The manifest maps the 24 published reference digests to private local paths. `generate(source)` returns a dictionary of named target rows keyed by zero-based full-source game ordinal, sparse bytes and an aggregate receipt. The CLI can save those bytes with `--private-output` and the indices with `--private-ordinals`.
