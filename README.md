# HotS Replay Recovery

Source replay: build 41810 (Heroes of the Storm 1.17.0).

Git stores all binary replay artifacts as deterministic Base64 text under `artifacts/` because the GitHub connector only accepts text content. `decoded/<build>/` is a deterministic semantic projection used for review and diffs. Large event streams use JSON Lines where practical, while compact before/after semantic deltas under `migrations/` make protocol changes easy to inspect.

Workflow:

1. Restore the source `.StormReplay` from `artifacts/*.base64`.
2. Decode the replay into stable JSON/JSONL.
3. Apply a version migration to the semantic model.
4. Diff decoded states with Git.
5. Encode a new `.StormReplay` checkpoint.
6. Decode the generated replay again and compare it to the intended semantic state.
7. Store durable Git bundles and binary checkpoints on OneDrive.

Restore an artifact with `scripts/restore_artifact.py`. Repository layout is documented in `docs/REPOSITORY_FORMAT.md`.
