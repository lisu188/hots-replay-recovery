# Unit clicks on the reconstructed Dragon Shire layout

The converter projects 1,702 of TEN_GREYMANE’s 2,756 recorded unit clicks into build 98348. The event ID is 39. Its only payload is a mandatory unsigned 32-bit unit tag. Every original click and all 41,988 clicks in the 24 pinned 98348 controls contain a nonzero value. Splitting that word at bit 18 in TEN and bit 22 in each control uniquely maximizes matches with physical tracker generations and accounts for every tag.

| Target identity evidence | TEN clicks |
| --- | ---: |
| Primary hero from the lobby, opening allocator and independently reconstructed life at click time | 1,356 |
| Opening map generation during its first recorded lifetime | 333 |
| Initial Dragon Knight before its first destruction | 13 |
| Post-opening allocation with unresolved destination identity | 1,019 |
| After the initial placement lifetime | 24 |
| On a transition loop or while inactive, among the remaining opening generations | 11 |

The GateOrder map, scripted placements and player roster supply the opening birth records. Their identity, loop, owner and position agree with the original tracker for all 182 units. A map placement qualifies before its first recorded death, type change or slot reuse. Primary heroes also require an exact match between the recorded life history and the original level, player-death and historical timer reconstruction. The first Dragon Knight starts in its authored slot. The activation statistic and same-loop transfer identify the pilot, and the subsequent neutral spawn independently dates the first destruction through the verified 1,920-loop respawn interval. Later Dragon Knight slots remain unresolved.

The 24 physical controls reproduce 293,916 bytes at the original frame boundaries, with the preceding full-stream loop delta and recorded user. They contain living-target click witnesses for 28 of 29 projected unit types. The exception accounts for 49 clicks on `TownCannonTowerL2Standalone`. GateOrder places those towers, TEN confirms each opening generation, and the 98348 catalog contains direct declarations including a Dragon Shire override. An independent 98348 click on that specific type remains unobserved. [Catalog evidence](COLLECTION_REFERENCE_CANDIDATES_2026-10-18.md)

`unit_click_inputs.generate(source, gate_map, mechanics, curve)` returns a dictionary keyed by zero-based ordinal in the **full source game member**, sparse target bytes and the aggregate evidence. Each dictionary value carries the original game loop and user plus its projected tag. An assembler must interleave these rows by source ordinal and regenerate deltas for the resulting stream. The standalone 11,985-byte fragment has SHA-256 `a10254710ebbab120fd4111d7024133c4341294d96e7834a6d6b121b9d5e98fb`. The reconstructed historical map’s target simulation and click effects remain untested.

```text
python unit_click_inputs.py SOURCE GATE_MAP MAP_MECHANICS_GALAXY HISTORICAL_TIMERS --control-manifest PRIVATE_PATHS_JSON --jobs 4
python verify_unit_click_inputs.py SOURCE GATE_MAP MAP_MECHANICS_GALAXY HISTORICAL_TIMERS RECEIPT observations/first-sync-game.json ORIGINAL_R8
```

The private manifest maps the 24 SHA-256 values in `observations/first-sync-game.json` to local control files. Optional `--private-output` and `--private-ledger` save the fragment and `[source ordinal, absolute loop, user, target tag]` rows. The aggregate receipt contains counts and digests.

The original partial build-98285 R8 already repacks all 2,756 click words at the same source ordinals. The independent GateOrder projection corroborates 1,702 of them for the 98348 layout. The other 1,054 still require an allocation or lifetime witness. [R8 comparison](../observations/unit-click-r8-check.json)
