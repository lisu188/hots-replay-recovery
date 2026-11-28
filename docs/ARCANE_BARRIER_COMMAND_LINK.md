# The 98348 Arcane Barrier command and TEN's five item uses

In build 41810, Kael'thas' Mana Addict reward is an inventory unit, `KaelthasArcaneBarrierItem`. TEN player 4 (user 3) receives the second such item (tag 217, recycle 5) at loop 1217. The original then contains five `SCmdEvent` records that use it:

| | Value |
| --- | --- |
| Game ordinals | 77929, 82528, 90313, 99691, 103345 |
| Loops | 14059, 15110, 16885, 18403, 19328 |
| Ability link and command | 365, command 3 |
| Target | none |
| Other unit | the item |
| Command flags | `0x100100` |

In build 98348, the third rank of `KaelthasManaAddict` grants `KaelthasArcaneBarrierAbility` instead. Its button issues `KaelthasArcaneBarrier,Execute` once the 20-globe quest completes, with a 45-second cooldown (720 loops). Both values are read from the pinned 98348 Kael'thas catalog.

## Witnessed target link

`arcane_barrier_command_link.py` scans a private manifest of the 52 genuine 98348 recordings in the workspace. A candidate link must meet four conditions:
- it is issued only as an untargeted command 0 without another unit;
- only by Kael'thas players;
- only after the recorded `RegenGlobePickedUp` count since their `KaelthasManaAddict` award reaches the quest threshold;
- with every activation burst (repeats within one second) separated by the cooldown.

**Link 385 meets all four.**

| Case | Result |
| --- | --- |
| Activating players | 2, both after quest completion (first uses at loops 16635 and 15947, completions at 12331 and 7659) |
| Activations | 10, in 6 bursts |
| Incomplete quest (19 globes) | never issues 385 |
| No Mana Addict (2 players) | never issue 385 |
| Completed but unused (1 player) | consistent |
| Other heroes, 46 recordings | never issue 385 |

The source item uses are separated by at least 925 loops, which is consistent with the same cooldown. Repeated runs produce identical receipts. The receipt is `observations/arcane-barrier-command-link.json`.

This is a witnessed, conditional identification. It is not a static proof of the catalog index.

## Translation rule

The rule replaces each source item use (link 365, command 3, other unit = the player's Arcane Barrier item) with link 385, command 0 and no other unit, for the same user and loop.

Three parts are deliberately not translated here:
- the command flags (`0x100100` in the source, `0x80100` in native uses);
- the per-user `m_sequence` numbering;
- the target simulation's own quest-completion time, which on the derived maps uses the restored 25-globe threshold.

The five commands therefore stay out of the sparse input stream. They depend on simulated globe pickups and remain withheld with the other state-dependent inputs.

```sh
python arcane_barrier_command_link.py ORIGINAL_TEN KAELTHAS_98348_XML PRIVATE_98348_MANIFEST
```
