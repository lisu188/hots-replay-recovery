# TEN Quick Match opening

The GateOrder candidate contains 235 tracker frames at loop 0. The setup prefix occupies 240 bytes and the map initialization occupies 13,602 bytes. The full 13,842-byte candidate decoded and re-encoded exactly. Its SHA-256 is `575dc05ef76fa4c878fc45074c64e0cf94d7c658d3fd20d9b98d07fcf6c3bfee`.

The original replay identifies a ten-player Dragon Shire match with global attributes 3009 = `Amm`, 4010 = `stan` and 4018 = `fcfs`. The historical parser identifies a standard matchmaking lobby in build 41810 as Quick Match. That schema predates the numeric matchmaking ID field. [Historical parser implementation](https://github.com/barrett777/Heroes.ReplayParser/blob/65d53c98714ea12ad51dec1afa48b32891438766/Heroes.ReplayParser/MPQFiles/ReplayAttributeEvents.cs)

| Physical recording | Queue and lobby | Next event after ten player setups |
| --- | --- | --- |
| TEN, 41810 Dragon Shire | Quick Match, standard | First of 165 unit births |
| 98285 Braxis Holdout | Quick Match, ID 50001, standard | First of 332 unit births |
| 98348 Lost Cavern | Private, standard | First of 82 unit births |
| Other 23 local 98348 recordings | Private, draft | First of four hero bans |

The raw first loop in the three standard lobbies contained zero hero pick or ban events. The exact-build and exact-queue observations come from different recordings. No genuine build 98348 Quick Match was present among the 24 distinct inspected 98348 recordings. The local search skipped 2,072 cloud placeholders. The 235-frame output is a candidate for this opening. The private artifact contains original player identifiers and belongs in local storage.

The generator requires the original source, the two standard-lobby witnesses, the reconstructed map and the installed MapMechanics and Support libraries. It prints aggregate hashes and counts. To write the private output, supply a new destination using `--private-output`.
