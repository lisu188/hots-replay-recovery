# Replay recovery working rules

- Continue the TEN_GREYMANE replay migration; preserve the original replay and earlier checkpoints.
- Commit and publish each small, coherent, verified milestone immediately. Do not accumulate an entire session before publishing.
- Use main unless an existing repository rule requires a pull request. Never force-push or discard concurrent changes.
- Store replay artifacts as ASCII Base64 parts with SHA-256 checksums. Do not commit raw StormReplay files or Git bundles.
- Retain deterministic JSON/JSONL projections and explicit semantic migration deltas for review.
- Save a Git bundle, progress manifest and generated checkpoints in the existing OneDrive project folder when its connector permits writes. Report failed synchronization honestly.
- Record user-visible decisions, tests, uncertainties and next steps in docs/CHAT_CONTEXT.md or dated checkpoint reports. Do not include credentials or unrelated personal information.
- A successful protocol decode/encode round-trip is NOT proof of in-game playback or deterministic simulation compatibility.
- Do not guess current game builds, content hashes, catalog mappings or version tuples. Keep unverified metadata explicitly marked experimental.
- Validate integer bounds and refuse silent truncation. Record every added, removed or defaulted semantic field.
- Compare target schemas against Blizzard's pinned upstream definitions, not only against our own decoder.
- Test reconstructed Base64 artifacts against their SHA-256 before replacing any existing output.

## Continuation state

Read `progress.json` together with the latest supplement `observations/catalog-capture-2026-09-29.json` and `docs/CATALOG_CAPTURE_VALIDATION_2026-09-29.md`. The old 43905 bootstrap state is historical, not the current checkpoint.

R5 loaded Dragon Shire but desynced at displayed 0:04. R6 repairs packed unit tags; R7 applies a bounded command-flag hypothesis. Neither R6 nor R7 has a confirmed successful client result. The standalone `TEN_GREYMANE_CATALOG_PROBE_98285.StormMap` is diagnostic, not a recovered replay.

The capture importer was tested at `db77fea54f1d1b7ad52a610590cbf8bf9ef173e9`, CI run `36570998775`: 107 tests separately passed on Linux and Windows. It requires collector digests, complete same-session banks, consistent reported version evidence and 48 independent unit anchors. Even passing these checks is only eligibility for unit-catalog review, not authenticated runtime state or verified ability/simulation compatibility.

The next concrete input is the user's `catalog-output-*.zip` produced by the diagnostic launcher. Search the OneDrive project and inspect that capture before generating another numerical mapping. Preserve and report any Galaxy/map error. Do not infer a successful export from the mere presence of the diagnostic package, a bank filename or an old log. Never suppress synchronization checks or substitute another match's sync values.
