# Recovering command target owners

`command_snapshot_owners.py` reconstructs the control and upkeep player fields in unit-target command snapshots from the same recording's tracker stream. A packed tag identifies the index and recycle generation. The original uses an 18-bit recycle field, the current build uses 22 bits.

```sh
python command_snapshot_owners.py TEN_GREYMANE_source_41810.StormReplay --build 41810
python command_snapshot_owners.py control.StormReplay --build 98348
```

The history records births, initialization, owner changes, type changes, deaths and revivals. During an active lifetime, each owner role remains eligible until its first recorded change. A revival can retain the earlier owner's value for the same generation. At a transition loop or after death the checker accepts a role only if every recorded assignment in that generation agrees. Index reuse starts a separate history, and contradictions involving retired generations are rejected. The checker erases the eligible fields in memory, restores them using the tracker, then re-encodes and compares the entire game member. Unresolved fields retain their recorded values.

| Recordings | Unit-target commands | Both owners recovered | Owner fields restored |
| --- | ---: | ---: | ---: |
| TEN_GREYMANE, 41810 | 12,465 | 11,746 | 23,492 |
| 12 Dragon Shire references, 98348 | 69,274 | 66,155 | 132,310 |
| 2 additional Dragon Shire references, 98348 | 13,107 | 12,613 | 25,226 |

All 15 complete game-event members reproduced byte for byte. Of the 719 unresolved source commands, 670 came after an ownership change and 41 used a sentinel tag. The remaining eight involved death, a transition loop or an unknown generation. [Per-recording results](../observations/command-snapshot-owners.json)

Using the most recent tracker owner unconditionally would give the wrong team for six commands on lane minions in the original 12-control set. In each case the snapshot still recorded the other team one or two loops after the tracker reported the transfer. The historical match still requires independently derived target player assignments, unit lifetimes and ownership transitions. [Six counterexamples](../observations/command-owner-transfer-counterexamples.json)
