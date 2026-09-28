# HotS Replay Recovery

Recover and experimentally transcode the preserved TEN_GREYMANE replay from protocol 41810.

**Protocol validation is not proof of in-game playback.** No checkpoint is currently certified to reproduce the match in a HotS client. Original game-data identifiers, opaque synchronization streams, catalog semantics and target compatibility hashes still need client-level validation. The target protocol number is not a claim about the newest live HotS release.

## Current workflow

The `Replay recovery checkpoints` GitHub Actions workflow tests the original replay, compares local schemas with a pinned Blizzard checkout, and attempts targets **44256, 57547 and 96477**. Each successful checkpoint is independently read by Blizzard's decoder, mpyq and StormLib before it is committed and pushed to `main`. Read `progress.json` and `checkpoints/<build>/report.json` for actual results; the target list alone does not establish success.

Git stores generated replay bytes only as fixed-width ASCII `*.base64.partNNN` files with `.sha256` sidecars. JSON snapshots and `*.changes.jsonl` / `semantic-audit.jsonl` show the changed fields, including explicit defaults and experimental assumptions. Native bit-vector values are preserved as length plus hexadecimal packed value; they must not be confused with raw physical LSB-first bit streams.

Restore a published checkpoint from the repository root:

```sh
python scripts/restore_artifact.py checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay.base64 TEN_GREYMANE_protocol44256.StormReplay --sha256 checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay.sha256
```

For another successfully published build, replace all occurrences of `44256` with that build number.

## Reproduce a migration

Use **Python 3.11** for the unmodified upstream package: its package initializer imports the removed `imp` module on newer Python versions.

```sh
python -m pip install six==1.17.0 mpyq==0.2.5
git clone https://github.com/Blizzard/heroprotocol _upstream
git -C _upstream checkout 9af3ea7150f1a8acb53464c92519a9bbcc7a3594
mkdir -p work
python scripts/restore_artifact.py artifacts/TEN_GREYMANE_source_41810.StormReplay.base64 work/TEN_GREYMANE_source_41810.StormReplay --sha256 artifacts/TEN_GREYMANE_source_41810.StormReplay.sha256
PYTHONPATH=_upstream:. python -m unittest -v test_recovery
PYTHONPATH=_upstream:. python migrate_replay.py work/TEN_GREYMANE_source_41810.StormReplay --target 96477
PYTHONPATH=_upstream:. python verify_checkpoint.py checkpoints/96477 --require-stormlib
```

The final validation command requires the native StormLib library (`libstorm-dev` on the CI image).

## Archive integrity

New checkpoints use `mpq_rebuild.py`: MPQ v4 header/table MD5, 32/64-bit sizes and per-member CRC32/MD5 are rebuilt. Stale HET/BET tables and raw-chunk digests are replaced with a valid classic hash/block-table layout. Untouched member contents remain byte-identical.

Historical build-43905 artifacts under `artifacts/` were produced by an older writer that did not refresh all MPQ v4 integrity metadata. Retain them for history, not as proof of client compatibility.

## Durable progress

The user requested frequent small pushes, deterministic JSON diffs, preserved intermediate checkpoints and OneDrive backups. `AGENTS.md` records these rules. The OneDrive folder is `HotS Replay Upgrade - TEN_GREYMANE`; GitHub Actions also produces a downloadable recovery archive with generated checkpoints, logs and a Git bundle. A OneDrive copy is only considered synchronized after its upload succeeds.

See `docs/CHAT_CONTEXT.md`, `docs/PROTOCOL_ROADMAP.md` and `docs/REPOSITORY_FORMAT.md` for the earlier investigation.
