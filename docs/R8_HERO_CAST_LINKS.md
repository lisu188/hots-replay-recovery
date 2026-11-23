# Build-98285 hero and ability links

The complete R8 archive carries forward the 708 command-sequence repairs and corrects 60 of 68 additional candidate issues. Its SHA-256 is `2ee895d18bf0395de81bef5138fe471bcb427ba7dcd7184e273dc1262c77c413`. The archived game member contains 104,257 events and differs from its parent at 77 byte positions. The archive retains all 308 historical sync records.

| TEN action | Admitted | Build-98285 observation |
| --- | ---: | --- |
| Abathur Toxic Nest | 49 | 41 explicit commands in an original replay have ability link 154, index 0 and flag `0x100`. Each is the owner’s sole point input in the new nest’s grid cell and birth loop. |
| Target Anub’arak | 6 | 274 live, owner-verified implicit target records and a separate selection witness identify unit link 468. |
| Target Kael’thas | 3 | 58 target records and a selection witness identify unit link 632. |
| Target Tyrande | 2 | 50 target records and a selection witness identify unit link 850. |

The observed build-98285 spawn flag agrees with TEN and its R8 parent. Build 98348’s matched casts carried `0x2100100`. Only the ability link changes for these 49 casts. Each hero-target patch changes only the numeric snapshot unit link. Both original 98285 controls were examined. All 423 qualifying frames came from the ten-player match. The other recording supplies no corresponding hero or spawn. Five Sonya targets, one Greymane target and two Nova Holo Clone issues lacked exact-build support and are withheld.

Two archive readers verified all active members and the available MPQ checksums. The only changed members are `replay.game.events` and the regenerated archive attributes. The source and parent remained pinned through output creation. The archive remains a partial conversion. Replay playback and the target engine’s simulation state remain unverified.
