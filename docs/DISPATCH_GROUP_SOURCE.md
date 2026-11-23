# Build 98348 input-dispatch groups

For the TEN_GREYMANE lobby and GateOrder Dragon Shire map, users 0 through 9 map to dispatch groups 1 through 10 in order. The group number comes from the player ID in MapInfo. The group member holds the lobby user ID and zero-based physical lobby slot in separate bytes.

| 98348 RVA | Data flow |
| --- | --- |
| `0x6aa935`, `0x6aa97a`, `0x6d0646` | The map reader receives the object at +0x9f0 and checks the IpaM header. |
| `0x6d090d`–`0x6d091b`, `0x6cf3c1`–`0x6cf424` | Reads each file player into the array at +0x858 using stride 0x1b0. The first u8 and following u32 become player ID at +0 and control at +4. Both pinned maps contain ten control-1 rows with IDs 1 through 10. The remaining rows have control 3 or 4. |
| `0x97bd95`, `0x97c1f5`, `0x97c289`–`0x97c2bc`, `0x97cee9` | The builder visits the map records in order. It selects the output group at base plus the record's u8 ID times 0xbf0. Control 3/4 bypasses lobby-slot consumption. |
| `0x97c2c2`–`0x97c2fd`, `0x97c3a5`–`0x97c3fd` | The next lobby slot comes from the array at +0xe1a8, stride 0xf28. Native slot field offsets +0xc and +0x6c8 hold observe mode and an optional tandem leader. Observers and bound tandem followers skip this ordinary assignment. |
| `0x97c58c`–`0x97c5da`, `0x97d112`–`0x97d149` | Appends one member to the selected group. Member byte 1 gets the slot index before increment. For control 2, byte 0 gets the slot's user ID at +2. The later pass needs a playing human with a present tandem leader other than 16. The ten TEN players have no leader. |
| `0xd00f87`–`0xd00f9a`, `0xd0121d`–`0xd01265` | The startup caller copies the setup object into its stack frame. Argument five to `0x97bca0` is the group output buffer at owner+0x2a6e0. On success it passes the same pointer in RDX to virtual slot +0x360. The physical base table at RVA 0x27bc518 points to 0x133bee0 in this slot. |
| `0x133bee0`–`0x133bf4a`, `0x1327818` | The importer visits 16 groups in order. Each member at stride 0xb0 supplies slot→group, user→group (user below 16), and user→slot. The three context offsets are +0xa13d8, +0xa13c8, and +0xa13e8 respectively. The lookup reads +0xa13c8 indexed by user. |

The pinned PE table at 0x27c4748 associates the native slot's declarations 0, 1, 8, and 16 with offsets 0, 1, 12, and 1736. Pinned Blizzard protocol 96477 identifies the corresponding declarations as control, optional user ID, observe mode, and optional tandem leader. The native slot copier reads optional values from the byte following their presence flag.

The replay verifier produces all ten triples from map and lobby before decoding the physical tracker. Every complete 240-byte setup block matched in 15 authentic build-98348 replays and four build-41810 replays, including TEN. Five target controls distinguished user ID from slot in a total of 23 rows. For example, user 7 was physical slot 5 and received group 6 in replay `882f4895…`. A total of 24 rows distinguished working-set ID from physical slot. Physical tracker agreement corroborates the mapping across both builds. The analysis covers the ordinary ten-human import and establishes one input to dispatch. Runtime delivery, later group changes, and the loop-64 checksum require separate evidence.

Run `verify_dispatch_group_native.py PE decoded_text` with the pinned local files to check whole-file identities, 28 instruction sites, ten direct-call destinations, the import vtable slot, and the native slot table. Run `dispatch_group_source.py MAP REPLAY BUILD REPLAY_SHA256` with the recovery repository on PYTHONPATH to verify one physical setup block. The cohort results are in `dispatch-group-controls.json`.
