# J2 capture import and catalog planning — 2026-09-30

## Actual result

Added `import_catalog_journal.py` and 27 tests, connecting the delivered J2 collector ZIP to the existing conservative catalog migration planner. No replay or new diagnostic map was generated. R8 remains the latest replay candidate; no new user playback result was observed. R5 rendering Dragon Shire and reporting Replay Desync at displayed 0:04 remains the last explicit playback outcome.

The current OneDrive searches for journal-output in the project and drive, HRC98285 in the game documents, and 2026-09-30 in GameLogs returned existing documentation/progress or no matches, not a real runtime capture or a new gameplay outcome. These are bounded search results, not an exhaustive filesystem inventory. The refreshed project progress.json includes the previous J2 checkpoint. The GitHub starting head was 0370a2cb8c8e2a27356e37635c467295e57168c1.

## Implemented pipeline

Input is the unmodified `journal-output-*.zip` from `START_CATALOG_JOURNAL.cmd`. The reader handles ZIP contents in memory with explicit per-file, total-size and member-count bounds. It accepts only the context and consecutively numbered journal files, rejects unexpected or unsafe paths, nonregular entries, duplicate names, unsupported compression and inconsistent inventory digests. It does not extract input members onto the filesystem.

Context validation checks the exact J2 schema, explicit booleans, map digest, reported launch/map/graphics status, independently parsed version/data-build/executable-build text, warning list and inventoried modification times. A file timestamp older than launch minus the collector's five-second tolerance blocks eligibility even if the freshness boolean claims success. Collect-only input cannot pass the launch requirement. Collector assertions of playback or export validation are rejected.

The existing J2 sequence parser verifies a complete same-session journal, declared counts, preserved indices and the 48 pinned unit anchors. Zero journals produce a blocked diagnostic report rather than a successful export. Multiple journals are not arbitrarily merged or reduced to the newest file. Incomplete or mixed records also block review. Parsing a plausible log is not cryptographic authentication of a running game.

With `--source`, the importer re-reads the SHA-256-bound original TEN_GREYMANE through `plan_catalog_migration.read_source` and passes the capture to its existing `propose` function. The new output directory contains `capture.json`, `summary.json` and, when a source was supplied, `plan.json`. Output is staged; existing results are not replaced. No binary writer, map generator, synchronization removal or guessed-identity fallback is invoked.

The source plan still contains 49 unit links across 12557 fields and 54 original numeric ability links. These are previously established source requirements, not newly resolved current identities. A blocked capture produces zero proposed target links. Even a reviewable capture cannot resolve old ability names, unit-instance allocation or historical simulation equivalence by itself.

## Usage

From the repository with its existing Python dependencies:

```text
python import_catalog_journal.py journal-output-EXAMPLE.zip --source work/original.StormReplay --output work/journal-review
```

Omit `--source` to inspect only the capture. Exit code 0 means eligible for unit-catalog review, NOT playable. Exit code 2 means a well-formed package was inspected and blocked; read the emitted report. Exit code 1 means malformed input, I/O failure or an existing destination; no new result is published. The command requires the immutable source replay when source planning is requested.

The user's existing J2 map and launcher remain unchanged. Collecting the export does not require installing Python; the importer is for the recovery workspace once the synchronized ZIP is available. Do not repeatedly replace maps to compensate for missing observations.

## Tests and evidence

Local validation passed 175 distinct tests, including the 27 new importer tests, without test failures or skips. CI run 36675547724 at 6ab371d98e6ef4681ea554613e8997b279912973 passed the same 175-test suite separately on Linux and Windows. These are not 350 new tests. Platform-inapplicable workflow steps were conditionally skipped; no unit tests were skipped.

On each CI platform, the complete pipeline inspected the genuine immutable original plus two explicitly SYNTHETIC input packages: an anchor-only positive fixture and a no-journal negative fixture. It generated each set of reports twice byte-for-byte identically. The positive fixture proposes 23 name matches only because the test injected existing anchor entries; those proposals are NOT a real user export or new authoritative mappings and must never be copied into a replay. The negative fixture proposes zero target links. Both plans retain unresolved simulation, object-allocation and ability-identity blockers, and neither is playback-ready.

Windows additionally executed the actual unmodified PowerShell collector in Collect mode under Windows PowerShell and pwsh, once with a synthetic journal and once without a journal. All four resulting ZIPs were read by the importer and correctly blocked because no fresh probe launch occurred. This exercises producer-to-consumer format compatibility, not the game engine or an actual OneDrive provider.

Both CI artifact ZIP digests were verified after download:

- Linux: 53db65fd8df8cfb554faff687d37e0273d9179378808d1b644440baa278bd036.
- Windows: 6958d6a1b6a667229b02fd570a805425e44d8ae92888129aa8e57d3b07a64bb3.

The downloaded source bundle records complete Git history through tested commit 6ab371d98e6ef4681ea554613e8997b279912973. Its SHA-256 is 29009fbbc3c4b42f9ec8732d825efba6c42347e82abc339d62fc2a0e07e78718. Code recovered from that bundle matches the locally tested new source files byte-for-byte. Later session notes and checkpoint metadata are preserved separately in the delivery backup.

No HotS process, StormLib writer or fresh upstream decoder was run in this continuation. The existing source decoder and planner are reused unchanged. The original replay's SHA-256 remains e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824.

## Remaining boundaries and next action

The context contains collector-supplied records and selected log text. The importer does not inspect the live process, authenticate the binary, independently convert the graphics log's local timestamp to UTC or prove catalogue context equivalence. `actual_build_verified`, `evidence_is_authenticated`, `ability_indices_independently_validated`, `automatically_applied_to_replay` and `client_playback_validated` remain false.

Next inspect an actual synchronized journal-output ZIP with this importer. If no journal was produced, retain the blocked report and the exact native map/Galaxy error. Preserve all earlier replay candidates and synchronization data. Do not turn synthetic validation, the expected-build label or a screen message into a claim of recovered playback.
