# Combined TEN game inputs for build 98348

The private projection contains **21,585 of 104,257** original game inputs in source order. It includes the two final departures at loop 19,732. The opening is continuous through loop 67. At loop 68 the first sound-offset event still requires a target sound instance. There are 82,672 omissions. The output is a sparse game-event stream, and target simulation checks remain open. [Coverage by event type](../observations/ten-game-input-coverage.json)

| Input group | Included | Basis |
| --- | ---: | --- |
| Camera updates | 17,593 | Original fields, optional values and positions preserved on the historical terrain extent |
| Unit clicks | 1,702 | Authored placements, primary heroes and first Dragon vehicle during qualified lifetimes |
| Pings | 72 | 59 map or untargeted pings and 13 primary-hero pings |
| Issued commands, updates and closes | 2,112 | 39 building-target issues, 17 independently corroborated hero targets, 51 explicit point summons, 1,248 implicit point issues, 688 point updates, 20 closes and 49 Symbiote cancels. The flag mapping, sequence inference and selected abilities remain conditional. [Moving heroes](IMPLICIT_HERO_ISSUES.md) · [Point summons](POINT_ABILITY_BIRTHS.md) · [Building targets](IMPLICIT_BUILDING_ISSUES.md) [Point commands](IMPLICIT_POINT_ISSUES.md) · [Sequence evidence](COMMAND_INTERVAL_SEQUENCES.md) |
| Talent purchases | 19 | Same-tier, independently witnessed target index. All require the appropriate award state, and 16 follow an earlier unresolved award. |
| Map-intro soundtrack completions | 46 | The two non-Dragon map anchors agree on link 195. Projection preserves the original users and reporting loops and assumes GateOrder retains the stock soundtrack catalog link. [Catalog and witness checks](SOUNDTRACK_DONE.md) |
| Other inputs | 41 | 15 selections, 10 user options, 10 sound-length descriptors, two loading events, two private trigger-chat records and two departures |

The original final departures use four bits for their reason. The target uses five. The two physical source frames occupy seven enclosing bytes and the two projected frames occupy nine. In 24 target recordings, 45 qualifying terminal departures and 191 trigger-chat inputs reproduced their enclosing bytes. The private projection preserves the original chat payloads. [Terminal-event checks](../observations/terminal-user-leaves.json)

The assembler merges on zero-based ordinal in the original game member. Nineteen inputs have overlapping component projections. Their complete target payloads must agree. Both target writers reconstruct the same 194,652 bytes. The SHA-256 is `d5722b8a4e8e794d6321abe49a7d4cdf825b793fc259e3b9c94fbf2d9c814cfd`. The independent auditor checks every included event's ordinal, absolute loop, user and type against the source and reports every omission by type.

Comparison with the preceding stream preserved 21,532 of 21,539 original frames byte for byte. Inserting the soundtrack completions reduced the encoded loop delta on seven frames. All 21,539 retained their original source ordinal, absolute loop, provenance and bytes following the delta. [Frame comparison](../observations/soundtrack-assembly.json)

Run the following with the repository protocol dependencies on the Python path. The historical controls are the three recordings pinned by `predict_camp_captures.CONTROLS`. Supply the original map and its GateOrder derivative separately. The generated binary and ordinal ledger belong in local storage.

```text
python assemble_ten_game_inputs.py ORIGINAL GATEORDER_MAP MAP_MECHANICS HERO_CURVE SELECTION_CONTROLS LOOP64_GAME_PREFIX ABATHUR_CONTROL ABATHUR_XML --nova-xml NOVA_XML --soundtrack-evidence observations/soundtrack-done.json --original-map ORIGINAL_MAP --historical-control CONTROL_A --historical-control CONTROL_B --historical-control CONTROL_C --private-dir NEW_DIRECTORY
python verify_assembled_inputs.py ORIGINAL NEW_DIRECTORY observations/ten-game-input-coverage.json
```
