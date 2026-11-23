# TEN_GREYMANE building snapshot-point encoding

The binary contains build-98348 encodings of the `m_snapshotPoint` field for 2,179 building-target commands from TEN_GREYMANE on the historical-layout talent map. Their X/Y come from its authored placements and Z comes from its terrain. There are 146 `SCmdEvent` and 2,033 `SCmdUpdateTargetUnitEvent` ordinals. Each point occupies **72 bits** in an enclosing command, with 20-bit unsigned X, 20-bit unsigned Y and 32-bit signed-range Z. The encoder applies the native integer lower bounds.

The build-98348 schema graph was extracted from the pinned game binary and is published in the repository as `native_game_events_schema_98348.json` with SHA-256 `bbb2ca6a0c1511a6756cf0f5ab9d0309f4b8b6cdf397963d020390f549082895`. Event 27 takes the native path `291 → 294 → 164(choice 2) → 167 → 145 → 152 → 157`. Event 105 takes `555 → 557 → 145 → 152 → 157`. The shared native point type 157 maps to named type 90 in the pinned compatible Blizzard protocol. Field names come from that named schema.

## Reading the artifact

The TSV index identifies the source game ordinal, loop, editor object ID, event ID, three coordinates, binary offset and field bit length. The target-format cursor of a future enclosing command determines the alignment phase `p = cursor % 8`. For each row, read nine bytes starting at `binary_byte_offset + 9*p` in `historical-98348-snapshot-points.bin`. Copy those 72 physical bits into the destination beginning at its current bit position. Bit positions within a byte increase from least significant to most significant. Each row stores eight possible encodings and occupies 72 bytes in the artifact.

| Artifact | Bytes / entries | SHA-256 |
| --- | --- | --- |
| Binary | 156,888 bytes | `1caf663b5823c277735745a7fe528d6b989b0542e4689a4771c4afcf280c5b35` |
| TSV index | 2,179 data rows | `3e073059c7b2cba761860229f8ac78e12d8f4cf388fb76f9fcd197c8c25a5da2` |

## Independent checks

All 17,432 stored variants match a second named encoder and decode to the expected point with surrounding sentinel bits preserved. The two frozen genuine 98348 controls provide 2,562 comparisons at the actual start and end cursors of the native point field. Each frame was located with the independent Blizzard-derived decoder, then parsed again with the build-98348 native graph. All 2,562 physical spans matched and writing them back reproduced both complete game members. The measured phases were 1 (1,056 commands), 3 (1,474) and 7 (32). Using the phase-zero form would have given incorrect bytes on all 2,562.

These files cover one field within each command. A future enclosing target event must supply its other fields and actual bit cursor. Full target events, a converted replay and native playback remain unverified.

## Local reproduction

Run from the repository root with the pinned Blizzard protocol modules and the existing recovery codec available on `PYTHONPATH`. The output directory must be new. Its parent must exist.

```sh
python snapshot_wire.py generate --original-map "$ORIGINAL_41810_MAP" \
  --historical-map "$HISTORICAL_RULES_41810_LAYOUT_PACKAGE" --source-replay "$TEN_GREYMANE" \
  --output-dir "$NEW_PRIVATE_DIRECTORY"
python verify_phase_artifact.py "$NEW_PRIVATE_DIRECTORY"
python snapshot_wire.py verify-control --target-map "$STOCK_98348_MAP" \
  --target-replay "$CONTROL_REPLAY" --replay-sha256 "$CONTROL_SHA256"
python -m unittest -v test_snapshot_wire
```

The verification commands emit aggregate JSON receipts. Generation writes the binary, ordinal TSV and digest receipt into the specified local directory.
