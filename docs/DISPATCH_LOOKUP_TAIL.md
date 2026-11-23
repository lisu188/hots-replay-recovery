# TEN dispatch mask and lookup tables

For a clean 98348 startup with GateOrder and the TEN lobby, the active-user mask is `0x03ff` (little-endian `ff03`). The context checksum consumes the 48 lookup bytes in the order shown below.

| Context offset | Meaning | Hex bytes |
| --- | --- | --- |
| +0xa13c8 | User ID to map group | `0102030405060708090a101010101010` |
| +0xa13d8 | Lobby slot to map group | `0102030405060708090a101010101010` |
| +0xa13e8 | User ID to lobby slot | `00010203040506070809101010101010` |

Their SHA-256 is `e27feb565f2dd60d91713776867aa1578342ef36c78dbc81010df14978cd83e9`. The native checksum routine at RVA 0x131ce10 feeds the mask before other fields and the queue. It then feeds these three 16-byte spans in order at 0x131cf35–0x131cf79.

The constructor zeros the mask at 0x13239db and writes twelve dwords of 0x10101010 to the tables at 0x1323ec4–0x1323f32. The group builder empties all 16 member lists before scanning MapInfo at 0x97c0dd–0x97c1e4. In both pinned maps, authored group 0 has control 3 and groups 11, 12 and 15 have control 4. The special branch at 0x97ce8d sets metadata, consuming no lobby slot and appending no member. Groups 13 and 14 have no authored record. The ten control-1 groups each get one human member. TEN’s six trailing control-1 lobby slots are observers with no user ID. They contribute neither a member nor an active-user bit. The tandem branch at 0x97d112 excludes every TEN playing slot.

The importer at 0x133bee0 overwrites indices 0–9 of each lookup. Indices 10–15 retain their constructor values. The separate setup pass at 0x133b9d0 sets bits for control-2 users, including occupied observers. In control `882f4895…`, human observers 5 and 6 each emitted a physical opening options event and counted toward mask 0x0fff. Both retained sentinel 16 in the two user-indexed tables. Across 15 native replays and four historical replays, every projected mask agreed with the user IDs in the physical opening options events. All ten group assignments per replay also matched the physical tracker setup block. Eight observer appearances across five native controls exercised the distinction between the active-user mask and the lookup membership.

The original TEN and the R8 lobby project the same mask and lookup bytes. No join or leave (event 102 or 101) occurs in the recorded TEN opening or the 30-frame reconstructed game stream through loop 64. Those event types can change the mask, and joins can also change user-to-group. The result describes the clean startup and recorded opening inputs. Later external events, restored state, and the full target simulation checksum require separate evidence.

Run `verify_dispatch_lookup_tail.py PE DECODED_TEXT ORIGINAL R8 GATE_MAP GAME_PREFIX` with the recovery repository on PYTHONPATH. Run `dispatch_lookup_tail.py REPLAY REPLAY_SHA256 BUILD MAP` for one control. The two JSON receipts contain the TEN verification and individual control results.
