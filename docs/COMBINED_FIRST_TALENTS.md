# Combined Brightwing and Nova map

The independent PerfectAim derivatives for Brightwing's Unfurling Spray and Nova's intended historical Covert Ops slow compose into a 2,203,861-byte private map, SHA-256 `13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1`. Two builds produced identical bytes. The archive contains 73 content members and 75 live blocks. All 65 untouched parent members match their PerfectAim bytes.

The builder reopens the three SHA-pinned inputs, verifies their archive tables, and compares every affected catalog by entry ID. Both derivatives add their own entries after the same PerfectAim records. The builder rejects shared catalog IDs and localization keys, preserves each branch's contributed XML bytes, and rechecks all final values against both original branches. The source and validation receipts retain the exact branch hashes and per-member counts.

Brightwing's confirmed historical relative bonus and four-second passive support the model, while the absolute 6-to-8 radius depends on continuity to a later published baseline. Runtime recipient selection remains unverified. Nova's contribution reproduces the intended historical per-second slow ramp discussed in its separate component evidence. Native effective slow values, simulation checksums and playback are unverified.

```sh
python build_combined_first_talents.py PERFECT_AIM_MAP NOVA_INTENDED_RULE_MAP UNFURLING_SPRAY_MAP NEW_MAP --stormlib STORMLIB
```

On this map TEN's next four first-tier choices yield the following projected awards in original tracker order.

| Hero | Source input ordinal | Input loop | Award loop | Target selector |
| --- | ---: | ---: | ---: | ---: |
| Nova | 844 | 133 | 134 | 3 |
| Brightwing | 914 | 148 | 149 | 0 |
| Sonya | 1171 | 200 | 201 | 1 |
| Greymane | 1286 | 241 | 242 | 1 |

The projected tracker contains 271 frames and 16,394 bytes through loop 242, retaining the 267 prior frames. The sparse input stream contains 17,712 of 104,257 source inputs. Two independent builds reproduced both streams, and each of the eight selection/award fragments matched the separate translator for that talent.

This projection assumes the opening unit allocations, target identities, selection eligibility, and the earlier command and feedback conditions. Brightwing's initial healing amount and recipient tests and Nova's cloak handling can operate before the corresponding purchase. Whether these callbacks add, remove or reorder tracker events on the target remains open. The next original tracker record at loop 355 creates a Kael'thas inventory item. The complete simulation and all 308 synchronization records still require verification.

```text
python combined_first_purchases.py TEN HISTORICAL_HEROES_JSON COMBINED_MAP NOVA_XML BRIGHTWING_XML SONYA_XML GREYMANE_XML EXTENDED_TRACKER_PREFIX PERFECT_AIM_INPUT_DIR PERFECT_AIM_RECEIPT NEW_OUTPUT_DIR
```
