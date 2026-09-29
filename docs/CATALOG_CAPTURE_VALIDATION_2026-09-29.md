# Runtime catalog capture validation — 2026-09-29

## Current result

This continuation added a capture importer, 43 new tests, cross-platform CI and a small diagnostic delivery package. It did not generate another replay or change synchronization data. The last confirmed game outcome remains R5 rendering Dragon Shire and stopping at displayed 0:04 with Replay Desync. No successful R6/R7 playback or actual runtime catalog export was observed.

The source checkpoint recovered at the start was `8fbbdcbd80ecacabfb429c5f409f5fe0465800f2`. It already contained the previously generated standalone diagnostic map and R7 work from interrupted responses. Neither is represented as newly generated or client-tested by this session.

## Implemented importer

`import_catalog_capture.py` reads the exact ZIP produced by `scripts/run_catalog_probe.ps1` without extracting its contents to arbitrary filesystem paths. It validates the allowed member names, file types, compression modes, size limits, ZIP integrity, UTF-8 input, duplicate-free JSON context, inventory lengths and SHA-256 values. It delegates lifecycle-independent bank completeness and catalog-index preservation to `runtime_catalog_probe.combine_banks`.

A collected set must contain a completed manifest, all required chunks, one consistent export session and all expected indices. The context must report a fresh launch of the hash-bound diagnostic map and internally consistent executable/version/data-build evidence for 98285. Collect-only, stale, missing and conflicting evidence blocks eligibility for unit-catalog review.

The CLI pins the independently observed 48 unit anchors by the observation file's SHA-256. A mismatch returns a diagnostic report and exit code 2. Malformed or incomplete captures are rejected, and existing reports are not overwritten. Catalog values are never silently renumbered or applied to a replay.

These checks verify the internal consistency of collector records, not the authenticity of a live process. Even a synthetically constructed full-anchor fixture correctly retains `actual_build_verified=false`, `evidence_is_authenticated=false`, `ability_indices_independently_validated=false` and `client_playback_validated=false`. Passing the gate means eligibility for review, not a complete simulation migration.

## Validation evidence

The completed local invocation passed 107 tests without failures or skips: 43 new capture tests and 64 existing diagnostic/MPQ-sector tests.

CI run `36570998775` at code commit `db77fea54f1d1b7ad52a610590cbf8bf9ef173e9` independently passed the same 107 tests on Linux and Windows. These are 107 distinct tests executed on each platform, not 214 distinct tests. Both downloaded archives matched GitHub's reported SHA-256 digests; their reviewed source files matched the local tested files byte-for-byte. The tests use synthetic captures, including a full 48-anchor fixture, wrong-build rejection and missing-chunk rejection. They do not launch HotS or exercise the PowerShell launcher against a real installation.

The unchanged diagnostic map was already structurally checked in CI run `36568633021` with 315 regressions, native StormLib and independent bounded-sector decoding. That earlier result is not counted as a new run here. No Galaxy compilation or actual game export is claimed.

## Delivery

Package: `hots-catalog-probe-98285-capture.zip`, 2229524 bytes.

SHA-256: `6c6c6e9a2744d2c8c416e3eb0c50eb6a3058c65a002cfcb03997ffe3b5edb474`.

The map, launcher and CMD entry point remain byte-identical to the previous diagnostic package. The package adds the importer under `validation/`, its pinned reference observation, test-result summaries and updated Polish instructions. It does not replace Try Mode, patch executables or alter installation files. Normal game initialization can still write its own logs/settings. The diagnostic records use the dedicated `HRC98285_20260929_P1` bank prefix.

The code source bundle preserves complete Git history through the tested `db77fea` checkpoint; later delivery notes and the supplement `observations/catalog-capture-2026-09-29.json` are retained separately in the dated backup.

## Required next observation

Extract the package outside the game installation, preferably inside the OneDrive project folder. Close HotS and run `START_CATALOG_PROBE.cmd`. If the map displays `HOTS CATALOG PROBE: export requested`, exit it and press Enter in the script window to collect `catalog-output-*.zip`.

A map or Galaxy error must be retained verbatim instead of interpreted as an export. Standalone map loading can omit talents or use a different initialization context, so all anchors must be checked before using any returned table. Original object allocation, ability identifiers and 2016 simulation behavior remain separate unresolved requirements. Do not suppress desync checks, fabricate indices or copy another match's synchronization values.
