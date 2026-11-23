# Combined TEN game inputs for build 98348

The private projection contains **19,504 of 104,257** original game inputs in source order. It includes the two final departures at loop 19,732. The opening is continuous through loop 67. At loop 68 the first sound-offset event still requires a target sound instance. The 84,753 omissions and the assumptions for emitted inputs remain explicit. The output is a sparse game-event stream, and target simulation checks remain open. [Coverage by event type](../observations/ten-game-input-coverage.json)

| Input group | Included | Basis |
| --- | ---: | --- |
| Camera updates | 17,593 | Original fields, optional values and positions preserved on the historical terrain extent |
| Unit clicks | 1,702 | Authored placements, primary heroes and first Dragon vehicle during qualified lifetimes |
| Pings | 72 | 59 map or untargeted pings and 13 primary-hero pings |
| Issued commands, updates and closes | 77 | Nine point issues, ten updates, nine closes and 49 Symbiote cancels. Each cancel still requires the correct target selection. |
| Talent purchases | 19 | Same-tier, independently witnessed target index. All require the appropriate award state, and 16 follow an earlier unresolved award. |
| Other inputs | 41 | 15 selections, 10 user options, 10 sound-length descriptors, two loading events, two private trigger-chat records and two departures |

The original final departures use four bits for their reason. The target uses five. The two physical source frames occupy seven enclosing bytes and the two projected frames occupy nine. In 24 target recordings, 45 qualifying terminal departures and 191 trigger-chat inputs reproduced their enclosing bytes. The private projection preserves the original chat payloads. [Terminal-event checks](../observations/terminal-user-leaves.json)

The assembler merges on zero-based ordinal in the original game member. Eleven inputs are supported by two component projections. Their complete target payloads must agree. Both target writers reconstruct the same 155,772 bytes. The SHA-256 is `6fa047434ca7b2f25e16218e8bdb674d5d66ac0388deee0e7c4be13cc182f645`. The independent auditor checks every included event's ordinal, absolute loop, user and type against the source and reports every omission by type.

Run the following with the repository protocol dependencies on the Python path. The historical controls are the three recordings pinned by `predict_camp_captures.CONTROLS`. Supply the original map and its GateOrder derivative separately. The generated binary and ordinal ledger belong in local storage.

```text
python assemble_ten_game_inputs.py ORIGINAL GATEORDER_MAP MAP_MECHANICS HERO_CURVE SELECTION_CONTROLS LOOP64_GAME_PREFIX ABATHUR_CONTROL ABATHUR_XML --original-map ORIGINAL_MAP --historical-control CONTROL_A --historical-control CONTROL_B --historical-control CONTROL_C --private-dir NEW_DIRECTORY
python verify_assembled_inputs.py ORIGINAL NEW_DIRECTORY observations/ten-game-input-coverage.json
```
