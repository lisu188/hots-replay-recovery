# Catalog journal J2 — 2026-09-29

## Result and boundary

Implemented a second standalone catalog diagnostic, `TEN_GREYMANE_CATALOG_JOURNAL_98285.StormMap`, which uses a text journal instead of StormBank for the export. No R9 or other replay was generated or modified. R8 remains the latest replay candidate and has no confirmed user playback result. The last explicit playback result is still R5 showing Dragon Shire and stopping at displayed 0:04 with Replay Desync.

The scoped searches found diagnostic packages and documentation but no actual catalog-output or catalog-diagnostics ZIP or HRC98285 bank. This is not an exhaustive enumeration and does not establish why the P1 export was not observed. The prior 15:46 launch log establishes only that the user launched the P1 map on executable/data build 98285.

## J2 implementation

`runtime_catalog_journal.py` instruments the exact hash-bound source map and changes only MapScript.galaxy plus regenerated archive integrity metadata. BankList and all other gameplay payloads are retained. The original initialization is preserved. The exporter redirects debug channel 1 to the dedicated name `HRC98285_20260929_J2.txt`, enables diagnostic output and obtains two random numbers for a session nonce inside this standalone diagnostic. It is not a no-side-effect simulation of the old match; normal game initialization can still write its own logs/settings.

The exporter emits at most 64 catalog entries per periodic callback. It retains all original catalog indices, including empty/invalid entries. BEGIN, COUNT, ENTRY, DONE and END records bind a single session and record declared counts. Failure conditions are explicit. A screen message requests collection; it does not prove that native output was flushed or that the full catalog was written.

The bounded reader rejects missing, duplicate, out-of-order or mixed-session records, noncanonical integers, malformed identifiers, wrong labels and incomplete final lines. It compares 48 independently observed unit anchors but always leaves automatic migration eligibility false pending separate fresh-launch/context review. Catalog values are not applied to a replay. Unit anchors do not validate all ability identities, engine object allocation or historical game rules.

`scripts/run_catalog_journal.ps1` checks the map SHA-256 before starting the installed switcher, refuses an already running game and leaves installation files unchanged. Collection searches only the exact J2 filename in bounded document/log locations and records selected version evidence and digests. It creates a new journal-output ZIP even without an export. Collect-only mode never asserts a fresh launch. Junctions are rejected; cloud placeholder handling uses the existing tested tag policy, but an actual OneDrive provider was not exercised.

## Validation actually performed

J2 code checkpoint: `8f8cb1b92a7391026b68e3d9d70bc9d6db02b264`.

CI run `36607470642` completed successfully. Linux passed 143 parser/generator regressions, including 36 new tests. Windows PowerShell 5.1.26100.33438 and PowerShell 7.6.6 each passed the same 15 new collector tests. Thus this continuation added 51 distinct J2 tests, not 66. No failures or skips were present in the completed runs.

Native StormLib generated two identical maps and verified available archive integrity data. An independent mpyq-table/bounded-sector reader checked all 75 map members. The previously diagnosed stock-mpyq limitation on full-sized raw PNG sectors was not reinterpreted as a new map problem. The independently pinned Galaxy parser `rameshvarun/galaxy-parser` at `c2f9cc65f234fef07261879b27a23ee796ff07f3` parsed the original map script, the complete modified script and the J2 fragment, and rejected a malformed fixture. This is syntax parsing, NOT compilation or native-function execution by HotS.

The CI map archive and both Windows result archives were downloaded and their SHA-256 digests checked against GitHub metadata. Two initial Windows-artifact downloads timed out; the retries succeeded. Downloaded J2 source files matched the locally reviewed files byte-for-byte. The actual game was not launched in validation and no real runtime export was observed.

Map SHA-256: `4733de8491521fac99a26b41c1691f65c8fd894e8ac14f200dfa7afe905672be`; 2233496 bytes.

Source map SHA-256: `f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f`.

User package: `hots-catalog-journal-98285-2026-09-29.zip`, 2228290 bytes, SHA-256 `eea0d09b76a54cefa756b5aa2c6bd56e3235162003ff26f94529f1ba7ff3e617`.

## Recovered work

Recovered the previously unpublished full-command audit from local backup `c426b06` and published `command_identity_audit.py` with its 40 tests. These are recovered tests, not new discoveries in this continuation. A transcription error in one test was immediately corrected to the recovered source; the final blob equals the original reviewed blob. CI run `36608400910` at `e87eb7d51037fedf8f1bc7c14ae6b753ac1fa336` passed all 40 tests and regenerated the complete 4558-command audit twice with identical reports and JSONL. The source replay remained byte-identical. It used the previously committed original protocol, not a freshly fetched independent upstream decoder.

The downloaded source bundle preserves complete Git history through the tested `e87eb7d` code checkpoint, including J2 and recovered command analysis. Later delivery notes and this session supplement are retained separately in the dated backup. No private donor, account log or crash memory is published by this continuation.

## Next actual observation

Extract the user package into a new OneDrive project subfolder, close HotS and run START_CATALOG_JOURNAL.cmd. If the map displays `HOTS CATALOG JOURNAL: export requested`, exit it and press Enter in the launcher. Inspect the synchronized journal-output ZIP and its actual content before constructing a numerical mapping. Preserve any exact map/Galaxy error. The absent P1 output remains unexplained, and J2 may still fail at native compilation, initialization or output. It is not a promised fix for those unknowns or for replay desync.

## Primary implementation references

- Hash-bound map: jamiephan/HeroesOfTheStorm_S2MA at `2bc3715018424208faf200c141756d9a19f9aafa`, `s2ma/f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f.s2ma`.
- Extracted game trigger source: jamiephan/HeroesOfTheStorm_Gamedata at `0ef1ef4028b3725771c6dd28ca18753006b122d9`, heroeslib.galaxy uses TriggerDebugSetTypeFile and TriggerDebugOutputEnable; heroeslib_h.galaxy defines the existing Debug_Output journal name.
- Independent syntax parser: rameshvarun/galaxy-parser at `c2f9cc65f234fef07261879b27a23ee796ff07f3`, lib/index.js and lib/parser.js. Its successful return is not engine semantic validation.
