# Optional command sequences in 98348

The 98348 archive reader consumes a presence bit for the sequence on command-manager state (103), target point update (104) and target unit update (105). An absent value clears the presence byte and leaves the adjacent integer storage untouched. The writer emits the presence bit and skips the integer. An absent sequence therefore has no decoded numeric value. The consumer's choice of pending command still requires simulation evidence.

| Event | Object bytes | Presence byte offset | Value offset | Native optional and integer types |
| --- | ---: | ---: | ---: | --- |
| 103 | 64 | 0x34 | 0x38 | 549, 550 |
| 104 | 72 | 0x30 | 0x34 | 552, 554 |
| 105 | 88 | 0x30 | 0x34 | 556, 558 |

For static reproduction, verify the executable and transformed code sizes and SHA-256 in the [IDA receipt](../observations/sequence-native-ida-receipt.json). Use image base `0x140000000` and place the verified static transform at RVA `0xBA000`. Follow event entries 103–105 in the typed dispatch table at RVA `0x1353A78`. The per-type archive wrappers pass the payload at object offset `0x30`. Follow the native schema field types above into optional reader case `0x1A70F24` and writer case `0x1A6F142`. Compare the absent and present paths at `0x1A70F56` and `0x1A6F1EF`, including the callbacks listed in the receipt.

Two static IDA 9.0 passes covered 63 selected ranges. The 2,694 decoded bytes matched the pinned offline code transform. This evidence concerns archive storage and serialization. [Historical and current command observations](LEGACY_COMMAND_SEQUENCES.md)
