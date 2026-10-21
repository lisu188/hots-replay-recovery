# Strict MapInfo empty-count framing converter

Profile: legacy-empty-mapinfo-count7-to-native31-v1.

The converter admits only the exact original41810, R8 and authenticated39445 battlelobby member digests and sixteen saved MapInfo spans. It derives only current191-type schema1828's count width31to7/max127 in private memory. Every decoded list count must be zero. No current schema file, production profile or module global is changed.

The operation preserves all preceding/following bits and every non-count token. It encodes the logical empty list using the current31-bit count in place of the old seven-bit zero count, adding24bits per record. It never overwrites24existing source bits. Nonempty source and target lists are refused. The independent published current MapInfo reader checks all32named fields, all decoded field values/types/shifted bounds and exact consumed spans. The inverse reads the converted bytes and restores the seven-bit empty counts; full source-member byte equality is required.

Actual proof, one guarded three-source run:

| Input | Records | Member bytes before/after | Growth |
| --- | ---: | ---: | ---: |
| Original41810 | 5 | 41746 / 41761 | 15B |
| R8 partial98285 | 5 | 41918 / 41933 | 15B |
| Authenticated39445 | 6 | 38870 / 38888 | 18B |

All16destinations passed:512named root-field and3888total field comparisons; every non-count token and all outside/prefix/suffix bits match; all three inverse whole members are byte-exact. Fresh historical metadata boundaries agree with the frozen source-span baseline. Source/replay/schema/code hashes remained unchanged. The raw replay input allowance was3726042distinct bytes(<4MiB),7452084bytes including before/after guards. No header, dump, PE or network body was read. The converted members existed onlyRAM; only a sanitizedJSON report was written.

The23focused unit tests use invented physical-bit fixtures. They cover all eight partial-byte starts, multiple records, independent physical splice equality, source/profile admission, all tested nonempty counts, record bounds/overlap, schema pins, inverse tampering, unchanged prefix/suffix/other fields and repr/summary privacy. Three mock-hash regressions prove wrong-type, wrong-size and oversized targets are refused before target hashing; source hashing remains expected. Only test fixtures patch admission, and the dedicated boundedness tests also wrap the hash callback.

The original code/test freeze is retained as history. code-test-freeze-v2.json binds the reviewed code and23tests before real-input proof; its pending-proof flag describes that earlier stage and is superseded by the actual proof and final receipt. The v1source/test snapshots and initialfreeze are not in the final publication allowlist. No actual-data unit tests were added.

Public API, when these sources are installed beside the existing native readers:

    result = convert_mapinfo_framing(member_bytes, PROFILE)
    assert inverse_mapinfo_framing(result, PROFILE) == member_bytes
    sanitized_summary = result.summary()

ReframedMember and edit models suppress values in repr. Both source and converted bytes are private RAM fields. The module provides no file writer or replay constructor. The proof driver requires an existing parent and a new .json output; it refuses an existing output before opening private inputs.

Run focused tests from a repository that contains the module:

    python -B -m unittest -v test_legacy_mapinfo_framing

This is a partial MapInfo framing step. Attributes, ClientInfo, resource registries/matrices and the rest of each member remain legacy bytes. A complete current OnlineStartGameRequest or playable replay is not produced or claimed. No ClientInfo voice/staff flags, player level, boost, ownership or permission elements are synthesized. The observed legacy profile is not an authenticated whole historical native schema.


Publication note: the executed private-input producer is preserved byte-exact.
It pinned its HERE converter source while searching repo before HERE. The repo
module was absent at that execution/review, consistent with the ready-module
run. Both private-input producers are immutable research snapshots, not
relocatable repository command-line tools. For a future private rerun, restore
verify_legacy_mapinfo_framing_guarded.py in a separate ready directory beside
byte-exact copies of the root converter, root test module and
code-test-freeze-v2.json from the published observations. Supply the original
task directory through --workspace and the repository through --repo; the saved
private inputs must already exist. The guarded producer adds a loaded-module
SHA check before replay reads. It has been syntax checked; no new three-case
raw-input execution is claimed for it.
The new CI step uses the restored original source and the published root module
directly, with source SHA/current-native/inverse checks and JSON output only.
Inspect hosted logs before claiming the new958-test/48-module run has passed.
