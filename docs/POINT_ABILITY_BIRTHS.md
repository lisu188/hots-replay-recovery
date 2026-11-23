# Matching point abilities to tracker births

The original TEN recording contains 51 explicit point issues that can be associated with a specific ability and a matching unit birth in both builds. The target-format projection uses the original game-stream ordinal, user, sequence and full point. It changes the numeric ability link and uses the flags observed on the corresponding 98348 casts. Whether those flags reproduce the original player’s input mode remains open.

| Target unit | Explicit TEN issues | Ability link, 41810 → 98348 | Exclusive same-loop 98348 witnesses |
| --- | ---: | --- | ---: |
| Abathur Toxic Nest | 49 | 173 → 154 | 62 in one match |
| Nova Holo Clone | 2 | 244 → 523 | 124 in two matches |

Each admitted birth has one point input from its owner on that game loop in the same integer map cell. The current catalog links the named ability to a target-point create-unit effect and its spawned unit. All 186 exclusive target issue frames match the native writer. They carry flags `0x2100100`. All 51 TEN issues carry `0x100`. Other 41810 reference players also used `0x200100` for those abilities. A general mapping for these original flag words remains unresolved.

The 51 projected issues occupy 1,221 bytes, SHA-256 `cf0c61fb8b2df7bc15649576f51a806053633a6d06d258a08c38c9021ba0a488`. R8 records different ability links and flags on all 51. Eleven additional original casts produce the historical cloaked clone, whose target behavior remains unresolved. [Physical receipts](../observations/point-ability-births.json)

## Missing historical state-1 sessions

The TEN tracker records 125 Toxic Nest births. At 62 of them, a point update and the immediately following same-loop state-1 manager share the same wire user and sequence. No event 27 for that user ever records this sequence. The update is the sole same-loop point input from the nest owner in its spawn cell. There is no explicit same-cell nest cast in the preceding 32 loops for any of the 62 cases. Shifting the birth loop by −16, −1, +1 or +16 produces zero matches in TEN.

Ten additional 41810 recordings contain 566 exclusive matches under the same rule. In TEN, the first occurs at loop 730. The private ledger records the update and manager ordinals, user, sequence, loop, unit and integer birth cell. This recovers the associated gameplay effect. The original creation time, initial full XYZ, issue flags and sequence-object initialization remain unresolved. The emitter adds zero synthetic commands on these 62 sequences.

Build 66488 has no Abathur or Nova player in the sampled match. The same owner/loop/cell test independently found 38 Fenix Plasma Cutter and two Deckard Healing Potion casts with explicit issues. This intermediate recording contains no state-1 or state-2 managers and therefore cannot establish which original fields were omitted when the historical producer recorded a nest session. [Build comparison](PUBLIC_COMMAND_TRANSITION.md)

```text
python point_ability_births.py SOURCE ABATHUR_XML NOVA_XML --controls PRIVATE_PATHS --retained-r8 R8
python -m unittest test_point_ability_births
```

The manifest maps the 48 independent pinned replay digests to local paths and builds. `generate(source, abathur_catalog, nova_catalog)` returns named target issues keyed by zero-based original ordinal, sparse bytes and an aggregate receipt. `--private-output`, `--private-ordinals` and `--private-symbolic` save the fragment, its ordinal list and the separate state-1 evidence.
