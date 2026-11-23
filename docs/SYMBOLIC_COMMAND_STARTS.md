# Command sequences with no recorded issue

TEN has 16,394 distinct `(wire user, explicit sequence)` pairs referenced by command managers or target updates for which there is no event 27 anywhere in the game member. For **10,495 point targets and 3,489 unit targets**, first use is an update immediately followed in the same player’s command stream and the same game loop by a state-2 manager record carrying the identical sequence. The two physical frames establish a player, sequence, loop and update target. The exporter can save their full-stream ordinals and observed target in a private ledger. It emits zero new commands.

Another 39 point/unit and state-2 pairs do have an event 27 on the same sequence, between zero and five loops later. All 39 later issues are implicit with source flag `0x100108`. Every one of the 13 point updates differs from the later issue’s coordinates. Of the 26 unit updates, 21 match the later unit tag, three name another unit and two precede a point-targeted issue. This prevents promoting the observed update target into an assumed issue target. All 28,046 physical frames in TEN’s numeric state-2 pairs re-encoded exactly. [Aggregate evidence](../observations/symbolic-command-starts.json)

| Header build | Distinct recordings | Point first uses with no issue | Unit first uses with no issue |
| --- | ---: | ---: | ---: |
| 39445, 39951 | 1 each | Sequence field unavailable on update | Sequence field unavailable on update |
| 41150 | 1 | 11,750 | 3,844 |
| 41810, excluding TEN | 23 | 247,133 | 91,667 |
| 42178 | 6 | 75,609 | 28,580 |
| 42273 | 1 | 4,716 | 730 |
| 97605, 98285, 98304, 98348 | 1, 3, 1, 24 | 0 | 0 |

The six genuine 42178 recordings and the 42273 recording use the same normalized upstream game protocol file as 41810. All 63 archive digests and complete game-member digests differ. Six additional public fixtures locate three distinct cases in builds 65006, 66488 and 68509. [Public transition controls](PUBLIC_COMMAND_TRANSITION.md) The partial TEN build-44256 conversion supplies no independent control. The data builds of the 39951 and 41150 recordings are 40322 and 41393 respectively.

In the inspected 98348 manager producer, state 2 requires bit 19 of the command descriptor flags when the owner-side condition succeeds. All 621,686 manager records in the 24 physical 98348 controls are state 0. The recordings establish nine issued-command flag words with bit 19 set. Among first target updates for a uniquely identified earlier issue with that bit, 361,670 point updates changed its coordinates, 11,911 point updates followed a unit-targeted issue and 4,138 point updates followed an explicit ability. Two 98348 manager keys without a recorded issue occur in one replay. Neither is a historical-style explicit point/unit and state-2 pair. The replay evidence therefore leaves the creator’s full flags, ability, initial target, creation loop and insertion order open.

```text
python symbolic_command_starts.py SOURCE --manifest PRIVATE_REFERENCE_PATHS --private-ledger NEW_PRIVATE_LEDGER
python -m unittest test_symbolic_command_starts
```

The manifest maps the 62 independent reference digests to objects with `build` and `path`. The source is supplied separately. The tool loads hash-pinned named grammars from the upstream heroprotocol versions checkout, and scores only command-related events 25, 27, 103, 104 and 105. Full-game ordinals count all event kinds. In the ledger each row contains the update ordinal, manager ordinal, loop, wire user, explicit sequence, update kind and its recorded target. The global SHA-256 check distinguishes the original TEN from derivatives.
