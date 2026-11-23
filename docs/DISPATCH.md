# First synchronization in build 98348

Static IDA analysis used the original 53,573,840-byte PE (SHA-256 `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`) and the separately pinned decoded text (36,581,376 bytes, SHA-256 `3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`). Addresses below are RVAs.

| RVA | Recovered operation |
| --- | --- |
| `0x13239dd`, `0x13239e4` | Initialize the user mask to zero and both adjacent 32-bit CRC/state fields at context offsets A13C0 and A13C4 to all ones. |
| `0x1326762`, `0x13267b9`, `0x13267c2` | Add the decoded loop delta to the running frame, then place the physical source user at event+29 and the accumulated loop at event+2C. |
| `0x13237f8`, `0x132e2d3`, `0x1327810` | The base context table at 27BC518 points from slot +110 to a getter. For user IDs below 16 it returns the byte at context+A13C8+user. Otherwise it returns sentinel 16. The dispatcher stores the result at event+2A. |
| `0x133bee0` | Populate the three lookup tables from 16 groups at stride BF0. Each group has a count and entries starting at +8 with stride B0. The first entry byte, when below 16, indexes A13C8 and maps to the group ordinal. Establish which groups actually populate TEN before computing any mapped-user result. |
| `0x132e2e4..0x132e350` | Three event types bypass the user-mask gate. A user-object check can still reject the event before the CRC update. |
| `0x132e350..0x132e415` | Update raw CRC32 at context+A13C0 with little-endian loop, one mapped-user byte and little-endian standalone payload CRC32, in order. The table starts at 2648210. A finished-loading event at context frame zero reaches its special return after the CRC update when admitted. |
| `0x13551d0`, `0x1352000` | Serialize the virtual event payload into a CRC stream starting at bit zero. The stream flush and finalization feed whole bytes, rounding up the final partial byte. |

The named protocol writer and the independent native-layout writer agreed on all 30 projected TEN payloads through loop 64 (593 standalone bytes). The ordered digest over event type, length and payload CRC was `3fbe83b84771036331379ea05a3dc228d3d57939297484fae7d5aaba2a1c9330`. Across 24 authentic target recordings, 1,507 in-profile opening payloads matched (19,243 bytes, maximum 106 per event). Eight type-58 payloads were outside the current native codec.

Run `python check_dispatch_inputs.py ORIGINAL_98348_EXE TEN.game-through-first-sync.private.bin` with the repository on the Python path. To reproduce the control cohort, add `--controls controls.json` with a local JSON object mapping each of the 24 hashes from `observations/first-sync-game.json` to its replay path. [Aggregate reference result](../observations/dispatch-input-controls.json)

## TEN dispatch contribution through loop 64

MapInfo and the TEN lobby assign users 0 through 9 to groups 1 through 10. The native importer reads the authored group number and binds it to the physical user. These assignments independently reproduce each physical player-setup block in 19 recordings. [Map and lobby derivation](DISPATCH_GROUP_SOURCE.md)

The six file event classes reach the game-input queue. The native setup copies the lobby observe field into the role byte used by the dispatcher. All ten TEN participants have class zero and their user bits are active. All 30 projected events therefore pass the admission tests with that roster committed. Run `python verify_dispatch_admission.py PE DECODED_TEXT ORIGINAL_TEN ORIGINAL_R8 GAME_PREFIX` to check the native instruction bindings and actual lobby values. [Admission evidence](../observations/native-dispatch-admission.json)

The first TEN input and the first input in all 24 controls are a loop-zero finished-loading event with user 16 and an empty payload. This type bypasses the participant mask and the sentinel has no player object. The mapped user remains 16. From the constructor seed the first update yields `0x79167cd3`. In the controls, all 240 human setup rows matched their physical lobby slots, including 42 where the user and slot numbers differed. All 7,501 physical sync records followed the 64-loop cadence. [Control counts](../observations/first-dispatch-witnesses.json)

On a clean start with the TEN roster committed and the 30 projected inputs dispatched in file order, the command accumulator at context+A13C0 reaches `0x176e9dc3` after the last loop-64 input. The user lookup, standalone payload and loop produce 270 bytes. The first and last loop-zero inputs both participate. This field is one input to the frame checksum. The previous frame's accumulator and the simulation vector are separate inputs. [Per-loop result](../observations/first-dispatch-trace.json)

`python dispatch_timeline.py ORIGINAL_TEN GAME_PREFIX TRACKER_PREFIX GATEORDER_MAP ORIGINAL_98348_EXE` reproduces the trace. `python first_dispatch_witnesses.py controls.json ORIGINAL_98348_EXE` checks the independent recordings. The native frame update at `0x132dda4` runs before the recording routine at `0x132ddae`, and the frame counter advances at `0x132ddd2`. The checksum state is updated between recorded checks, so the first type-2 record also depends on the intervening frame states.
