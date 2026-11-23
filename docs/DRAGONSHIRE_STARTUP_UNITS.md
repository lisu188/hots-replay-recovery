# Dragon Shire startup unit identities

The map's `Objects` member predicts the initial tracker tag of every authored unit in the original 41810 match and fourteen independent 98348 matches on the stock current layout. The zero-based rank of the numeric `ObjectUnit.Id` among all authored units gives the index. The first recycle value is one throughout these recordings.

```sh
python map_startup_identity.py DragonShire.s2ma match.StormReplay --build 98348 --anchors
```

The verifier checks the physical build and verifies that both dependency lists in the replay identify the supplied map by SHA-256. Pass the matching stock map. The target uses the pinned compatible build-96477 event schema. The same command accepts build 41810 for the original.

The verifier hides both tag components of every loop-zero birth. It pairs map placements with births using only unit type and coordinates. A pair must be unique in both directions within the four possible integer corners around the authored X/Y. For all such pairs both coordinates equalled the authored values rounded down. The evidence covers nonnegative coordinates. A missing or ambiguous birth stays unassigned. Every predicted tag is compared with the revealed original, then the verifier compares the full re-encoded tracker stream byte for byte.

| Recordings | Births at loop zero per match | Tags recovered from map | Placements with fractional coordinates | Unassigned births retaining recorded tags |
| --- | ---: | ---: | ---: | ---: |
| Original 41810 | 172 | 165 | 43 | 7 |
| 12 stock 98348 references | 170 | 158 | 51 | 12 |
| 2 further stock 98348 references | 170 | 158 | 51 | 12 |

Independently, `verify_authored_owners.check_owners(xml, tracker_bytes, protocol)` masks both owner fields. Explicit map `Player` values supplied both tracker owners; an absent attribute supplied zero. TEN_GREYMANE had 63 absent entries, 50 per team (11 and 12), and two shrine targets belonging to player 10. The current stock map has 66 absent entries and 46 per team. Each reconstruction preserved the complete tracker bytes. Changing one original object's player from 12 to 11 was detected.

Later ownership changes occur in the same recordings. These rules apply at startup on the tested layouts. A converted match still needs command-time identity, lifetime and ownership checks, the historical map and rules, and independently verified synchronization.

The receipts give each source archive digest and explain the accounting for unmatched births. [Startup recovery](../observations/dragonshire-startup-identity.json) · [Ownership recovery](../observations/dragonshire-startup-owners.json) · [Two additional matches](../observations/dragonshire-startup-external.json)
