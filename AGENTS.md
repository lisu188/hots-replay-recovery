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

Read `progress.json` with the additive latest supplement `observations/startup-and-probe-diagnostics-checkpoint-2026-09-29.json` and `docs/STARTUP_AUDIT_AND_PROBE_DIAGNOSTICS_2026-09-29.md`. Preserve older checkpoint and diagnostic history. The old 43905 bootstrap state and R7-only progress are historical, not the current replay checkpoint.

Latest replay: `98285-resumable-r8`, SHA-256 `4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19`. R8 repairs the observed resumable record layout while retaining all synchronization data. No R8 client outcome has been confirmed. R5 rendering Dragon Shire then Replay Desync at displayed 0:04 remains the last explicit user playback outcome. R6 repairs packed references and R7 changes a bounded command-flag hypothesis; neither establishes current object allocation or deterministic simulation equivalence.

A fresh user Graphics log now confirms that the standalone catalog probe was launched at local time 15:46:00.559 on 2026-09-29 with executable/data build 98285. It does not prove Galaxy compilation or a successful bank export. New Variables.txt records the R7 basename, which is not an outcome or R8 evidence. See `observations/probe-launch-2026-09-29-1546.json`.

The read-only first-interval audit (`audit_startup_interval.py`, CI 36599057470) passed 55 tests and checked full observed event payloads with pinned Blizzard decoders. The diagnostic window 0 <= loop < 64 contains 29 game events, four catalog fields and two point-target commands without explicit ability links. Two catalog fields differ from modern reference anchors and two have no anchor. These comparisons do not identify the first divergent tick, prove cross-map catalog equivalence or authorize guessed replacements. Original/R8 sync bytes remain identical and their native semantics unresolved.

`COLLECT_CATALOG_DIAGNOSTICS.cmd` is a separate read-only collector for an existing unsuccessful probe attempt. It produces a diagnostics ZIP even without a bank manifest. CI 36600519761 at 39ed432 passed the same 23 tests separately on Windows PowerShell 5.1 and PowerShell 7. It does not launch HotS or confer capture eligibility. Real OneDrive-provider behavior is not tested; Windows cloud-tag classification and actual junction rejection are tested. Keep its diagnostic format distinct from the validated capture importer.

Next inspect a synchronized `catalog-diagnostics-*.zip` or an actual `catalog-output-*.zip` when available. Preserve exact Galaxy/map error text rather than inventing the cause of missing banks. A diagnostic map relaunch is not necessary merely to collect existing evidence. The normal capture importer still requires complete same-session banks, consistent version evidence and 48 independent unit anchors; eligibility for review is not authenticated runtime or ability/simulation equivalence. Never suppress synchronization checks or substitute another match's sync values.

## Latest additive diagnostic: J2 journal

Read `observations/catalog-journal-j2-checkpoint-2026-09-29.json` and `docs/CATALOG_JOURNAL_J2_2026-09-29.md` before continuing. J2 adds a separate bank-independent text-journal exporter; it does not supersede R8 or establish the cause of missing P1 output. The delivered package is `hots-catalog-journal-98285-2026-09-29.zip`, map SHA-256 `4733de8491521fac99a26b41c1691f65c8fd894e8ac14f200dfa7afe905672be`.

CI 36607470642 at 8f8cb1b passed 143 Linux tests and the same 15 Windows collector tests separately under PowerShell 5.1 and 7. It independently checked 75 map members and parsed Galaxy syntax, but never compiled or ran the script in HotS. No authentic journal export is yet observed.

For J2 inspect `journal-output-*.zip`, validate its inventory digests and actual fresh client/map/version evidence separately, and parse journal files using `runtime_catalog_journal.parse_journal`. The reader preserves all catalog indices and checks 48 unit anchors, but deliberately does not grant automatic migration eligibility. Do not send J2 output to the P1 StormBank importer or infer runtime success from a screen message.

The previously unpublished full-command audit is now recovered as `command_identity_audit.py` and its 40 tests. CI 36608400910 at e87eb7d passed and reproduced the original 4558-command report twice. It assigns no guessed ability names or confirmed caster identities. These are recovered results, not a new playable checkpoint. The complete source bundle through e87eb7d is saved on OneDrive; later notes are separate.

## Latest J2 import checkpoint — 2026-09-30

Read `observations/journal-import-checkpoint-2026-09-30.json` and `docs/JOURNAL_IMPORT_2026-09-30.md` as additive continuation state. `import_catalog_journal.py` now validates the complete J2 ZIP, inventory, reported launch context, version text and journal sequence; `--source` connects it to the existing original-only migration planner. It writes capture/summary/plan JSON, never a replay. Exit 0 means review eligibility only, 2 means a blocked inspected capture, and 1 means malformed input or I/O failure.

CI 36675547724 at 6ab371d passed 175 tests separately on Linux and Windows, including 27 new tests, plus four actual Windows collector-to-importer fixture cases across PowerShell and pwsh. Full-source integration used SYNTHETIC captures, not a real engine export. Never promote its 23 fixture name matches into new observations or replay changes. No actual J2 capture or new R8 playback outcome was found in the scoped searches. The source bundle preserves complete history through 6ab371d; later documentation is included separately in the dated backup.

Keep the delivered J2 map and launcher unchanged until new evidence warrants changing them. Inspect a real synchronized journal-output ZIP; diagnose a missing or failed export rather than manufacturing another mapping. Catalog review eligibility is not authenticated process identity, ability equivalence, unit-instance mapping or deterministic playback.
