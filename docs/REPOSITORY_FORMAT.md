# Repository format

The repository intentionally separates reproducible source artifacts from generated semantic projections.

## Binary artifacts

Raw `.StormReplay` files are not committed as binary objects. Each binary is represented by:

- `artifacts/<name>.base64`
- `artifacts/<name>.sha256`

Restore and verify with:

```bash
python scripts/restore_artifact.py artifacts/TEN_GREYMANE_source_41810.StormReplay.base64 source_41810.StormReplay --sha256 artifacts/TEN_GREYMANE_source_41810.StormReplay.sha256
```

## Semantic JSON

`replay_to_json.py` deterministically decodes a replay to JSON/JSONL. The very large `game.events.jsonl` and `tracker.events.jsonl` files are generated locally and ignored by Git because they are mostly identical across adjacent migration checkpoints.

For review, each migration commits a compact semantic delta under `migrations/<from>_to_<to>/`:

- `*.changes.jsonl` contains every changed event with before/after values.
- `report.json` records total counts and SHA-256 hashes of full generated streams.
- changed structured documents such as header/initData are stored as before/after JSON snapshots.

This keeps the Git history reviewable while preserving deterministic regeneration from the committed base64 replay artifact.
