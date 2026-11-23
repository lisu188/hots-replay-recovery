# TEN_GREYMANE selections before the first sync

All four historical player selections at loops 52–60 can be encoded for build 98348. Each selects the player's own living hero. The opening model derives the hero's slot and generation from map, roster and allocation order. The source tracker independently confirms type, owner, generation and birth before selection.

| Loop | Unit | Source link | 98348 link | Matching 98348 replays |
| ---: | --- | ---: | ---: | ---: |
| 52 | HeroGreymane | 807 | 614 | 3 |
| 59 | HeroFaerieDragon | 64 | 470 | 8 |
| 60 | HeroAnubarak | 739 | 468 | 4 |
| 60 | HeroKaelthas | 827 | 632 | 2 |

The generator checked 24 distinct exact-build replays across multiple maps. A corroborating player selection through loop 256 had to match the tracked birth, packed tag, owner, subgroup priority 15, intra-subgroup priority 1 and count 1. Each eligible control frame re-encoded byte for byte with the native game codec and the named schema. All observed links agreed with the pinned existing catalog profile.

The four generated frames carry TEN's user IDs, loops, mask and control group. Their tags use a 22-bit generation field in place of the historical 18-bit field. The 60-byte fragment has SHA-256 `b1dc360f1539f5ac7800730f34f410f5d9f7bb4f3f61eafacf9d9b675f67d90b`. The deltas 52, 7, 1 and 0 agree with the original surrounding game-event stream. Other game-event kinds and the synchronization value remain outside this fragment.
