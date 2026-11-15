# Preserved J2 emitter with a 98348 runtime profile — 2026-11-15

`import_catalog_journal_98348.py` adds a separate bounded importer for the preserved
J2 diagnostic running on 98348. It writes catalog inspection reports. This
milestone provides no real J2 export, native execution result or replay conversion.
The legacy 98285 importer, exporter, collector, map and anchors remain unchanged.

The two identities have separate meanings:

| Evidence | Required value |
|---|---|
| Emitter token and collector declaration | `HRC98285_20260929_J2`, `expected_build=98285` |
| Journal BEGIN declaration | Literal 98285 and source-map SHA `f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f` |
| Delivered diagnostic map | SHA `4733de8491521fac99a26b41c1691f65c8fd894e8ac14f200dfa7afe905672be` |
| Supplied runtime Version | Exactly `2.57.0.98348` |
| Supplied runtime DataBuild | Independently exactly `B98348` |
| Supplied executable build | Independently exactly 98348 |

The emitter's build is a compiled literal. The importer retains it as
`emitter_declared_build=98285` and reports `runtime_profile_build=98348` separately.
Changing BEGIN or the collector declaration to 98348 is rejected. A GUI version
alone does not supply the DataBuild or executable evidence.

The [fixed anchor observation](../observations/runtime-catalog-reference-anchors-98348.json)
has SHA `8371d65c0c680ad8aaf9fa283f489f76c8dd6660595a566d438cbf62a003f73e`.
Its whole-file hash is checked before JSON parsing, capture reads or output
creation. Four reused legacy source files are also hash-pinned. Dependency
changes require an explicit review and re-pin of this additive contract.

The 12 prior genuine current-build Dragon Shire controls contain 105 observed tracker types.
Removing both names sharing index296 (`TownCannonTowerDead` and
`TownCannonTowerL3`) leaves 103 forward-and-reverse unambiguous anchors. The chosen 48
are ranked by supporting-replay count, then exact name; each occurs in at least
three controls. The observation includes per-anchor replay-digest provenance
and all 12 profile/inventory pins. These are reverified metadata sidecars bound
to earlier whole-replay/core-roundtrip evidence, not fresh raw-stream decoding.
The new profile does not establish cross-map or cross-region equivalence.
An actual export must still agree with its measured anchors. The 33 old-to-current
pairs remain separate migration evidence; their coverage is unchanged.

The new importer calls the legacy ZIP reader, strict JSON reader and journal
sequence parser unchanged. It validates the supplied collector context unchanged,
retains every nonruntime blocker and replaces exactly the three runtime version
checks with fixed 98348 checks. All inventory digests, map identity, explicit
booleans, warning checks, launch requirements and journal timestamp checks remain.
Collect-only output remains blocked. Empty or multiple journals are not resolved
by selecting a file or manufacturing a session.

Run the new command only on an actual unmodified collector ZIP:

```text
python import_catalog_journal_98348.py journal-output.zip new-result-directory
```

Output contains only `capture.json` and `summary.json`. Exit 0 means
`ready_for_98348_unit_catalog_review=true` for the supplied records; exit 2 means a
blocked inspected capture; malformed input or I/O failure exits 1. Existing output
is refused. The optional `--anchors` path must contain the exact pinned profile.
There is no `--source` option, migration-planner invocation or replay writer.

The legacy `ready_for_unit_catalog_review` and
`legacy_98285_migration_planner_eligible` flags stay false unconditionally. The
existing 98285 planner therefore refuses even a new profile's positive result at
its first eligibility gate. Actual-build authentication, ability validation,
automatic application, simulation compatibility and playback flags remain false.

Validation passed 23 focused new contract tests and 106 unchanged legacy tests.
New positive ZIP fixtures are explicitly synthetic test data, not engine exports.
Tests cover separate runtime fields, mixed builds, unchanged emitter identity,
ZIP and JSON rejection, stale timestamps despite true freshness flags, collect-only
blocking, anchor mutation, profile refusal before JSON/I/O, output preservation
and the legacy planner gate. Actual J2 export and semantic/native evidence are
still required; native/login state is tracked in separate receipts.
