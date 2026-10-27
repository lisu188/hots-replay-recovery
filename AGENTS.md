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

## Current live target — 2026-10-18

Read `docs/CONTINUATION_98348_2026-10-18.md` and
`observations/current-target-98348-2026-10-18.json` as additive state. The official
EU live manifest and installed client agree on **2.57.0.98348**. R8 is still the
latest replay and declares 98285; no new playable checkpoint or engine outcome
was produced. All three current public Heroes Profile objects returned HTTP
403 before download. This is not schema incompatibility. The updated public
reference tool distinguishes acquisition failures from validation failures.

The original map exists locally and matches its content hash; the four original
standard-data cache handles are redirects, not historical mod payloads. No real
J2 export was found. Preserve the old J2 package and its 98285 identity; do not
label unmeasured 98348 catalogs or copied anchors as verified. Next obtain an
authorized native-client result and genuine current-build reference/capture;
retain all old sync data and the full-match recovery objective.


## Offline current-reference checkpoint — 2026-10-18

Read `docs/OFFLINE_CURRENT_COMPATIBILITY_2026-10-18.md` and
`observations/offline-eight-current-references-2026-10-18.json` as newer additive
state. Eight genuine public NGS Dragon Shire replays now verify executable,
base and data build 98348, with exact observed core-stream round-trips using
the canonical pinned Blizzard 96477 schema. This supersedes the earlier
no-current-reference-acquired state; Heroes Profile's separate 403 outcomes
remain valid. Public source URLs and hashes are retained; raw donors and
player/chat contents are not published.

The independent unmodified .NET reader fully accepts Stormblessed, encounters
a pregame mapper mismatch on Protectors, and fails in R8 battlelobby attribute
definitions. Its isolated core readers complete on all three and agree with
Python event counts; this is not full parser acceptance for R8 or Protectors.
R8 retains old attribute count/index widths after its dependency-prefix update.
Investigate reversible, source-preserving transcoding; never copy donor
attribute catalogs, defaults, player identities or sync data.

All eight controls agree on mod checksum 13528913; R8 still declares 2276260760.
The map checksum and observed dependency paths agree with current controls.
Catalog mappings remain partial and ambiguity must remain explicit. The
historical J2 launch did run B98348, then ended during loading without an
observed export or established cause. The user now requests offline testing
without running the client; continue with that constraint. R8 remains the
latest replay and no new playback or simulation compatibility is established.


## Reversible battlelobby attribute layer — 2026-10-18

Read `docs/BATTLELOBBY_ATTRIBUTE_LAYER_2026-10-18.md` and the fixture and
independent-reader observations. The new bounded codec widens actual old
attribute-count/index fields, preserving every decoded numeric/unknown field,
source setting, dependency path, locale and complete opaque suffix. It checks
same-profile and inverse byte equality. All 428 source attribute values agree
with the separately decoded original attributes stream. R8's prospective
member is 42106 bytes, SHA bee7a6367574224321539ab21f0613e7c8e369a588327a2758ec53d64efe5edd.

This creates member files and reports only, never a replay checkpoint. The
unchanged independent decoder now advances past attributes and fails later
in mod metadata (ChoiceSection2); this is evidence of a partial fix, not full
member compatibility or whole-parser success. The remaining source suffix
stays byte-identical and requires its own migration. Keep R8 as the latest
replay until a properly audited later replay actually exists. No client
launch is authorized under the user's current explicit offline-only goal.


## Historical mod metadata and expanded controls — 2026-10-18

The later read-only `audit_battlelobby_mod_metadata.py` and
`docs/LEGACY_MOD_METADATA_2026-10-18.md` walk the exact source mod section,
with all scalars/blobs privately reconstructed and unchanged. Actual source
and R8 have five used mods and five metadata entries, not the misaligned
current-layout diagnostic's 16/18. Five CAFEBABE sentinels and five terminal
s2mh handles validate the observed boundaries. Dependency ID components
resolve; offset fields are retained and hashed but their semantics remain
explicitly unvalidated.

The primary community source explicitly lists build 41810 under schema 2.
Its old four-bit field of value 3 is fixed data, not a declared choice tag.
Two following 447-bit unknown payloads contain nonzero information. No
source proves their mapping to the modern counted/choice structure. Never
retag, clear, drop 47 bits, or copy another replay's hero metadata to force
acceptance. An envelope-only scratch hybrid still fails the unchanged C#
reader and is not a new replay or a compatible format profile.

The saved NGS Dragon listing is now exhausted at 13 downloaded files: 12
genuine current 98348 controls and one October 5 file actually built with
98304, excluded from the current cohort. Date labels are not build proof.
The expanded proposal remains 33 unambiguous unit pairs and 17 unresolved
types. See the new expanded-current observations; preserve the earlier
eight-control evidence as history. No new replay was created, no sync data
was changed, and the user's no-HotS-launch constraint remains active.

Attribute-layer CI run 39152968629 at f928ec7 passed on Linux and Windows,
23 focused tests and real original/R8 fixture checks on each. New mod-audit
code has separate checks; do not relabel the earlier CI run as testing it.


## Verified combined offline validation — 2026-10-18

Run 39153672088 at 7e23a6a passed both Linux and Windows: 37 focused tests,
two real attribute fixture files and three mod-audit cases per job. Local
combined regressions passed 56 tests. The read-only mod audit and source
comparison remain diagnostics; none resolves the two unknown old hero
payloads, all remaining catalog/ability/instance/rule/sync differences or
full current-build playback. Keep the no-client instruction and full replay
upgrade objective active. R8 remains the latest replay.

The full-history source backup through 7e23a6a is uploaded in the new dated
OneDrive checkpoint folder. Fresh cloud size/QuickXor metadata matches local
bytes; remote re-download returned403 serviceReadOnly, so no independent
remote SHA256 claim is made. Preserve old cloud files. Later validation-only
notes must accompany that base bundle rather than rewriting older artifacts.


## Static collection evidence workflow — 2026-10-18

`docs/COLLECTION_LICENSES_2026-10-18.md` and the catalog-only observation
introduce a bounded direct-declaration collector. The old263-name/current5418-ID
representation difference is observed; no ownership conversion or rename mapping
is established. Fifteen version-unbound public XML files provide1418 direct
License matches, not complete current catalog proof. The new workflow requires
the official live98348 manifest, extractor version and actual named Version plus
IsPtr=false extracted metadata before publishing measured results. Its first
remote outcome must be recorded separately. Local33tests ran32passed/1Windows
synthetic-symlink skip. No client is launched; R8 remains the latest replay.


## Named static arrays and complete member coverage — 2026-10-18

`docs/AUTHENTICATED_ARCADE_SECTIONS_2026-10-18.md` supersedes the old447-bit
unknown-hero interpretation above. All five original s2mh headers were fetched
from Blizzard's current depot endpoint and SHA256-verified. Package id/version
and extraDependencies match. Two headers' howToPlaySections numerically reproduce
the member bits: genuine four-bit array count3, three80-bit headers and nine
localized items. The unchanged community C# reader misreads this as choice3.
Neither47-bit deletion nor3-to5 retagging is justified. New audits use generic
counted arrays for both profiles. Original reports remain historical evidence.

R8's old map archive handle still conflicts with its newer dependency prefix.
Only three current US package headers were acquired; the other three returned404,
and EU requests for all six US hashes returned404. Current observed arrays are
not relabeled authenticated header bindings when exact headers are unavailable.
Twelve current controls have identical static mod sections despite different
selected hero rosters; region-specific package equivalence is not established.

`docs/BATTLELOBBY_TAIL_2026-10-18.md` covers the remaining suffix through strict
EOF and full-member byte reconstruction. All14 actual fixtures (original,R8,
12current controls) pass private identity/slot and both random-seed crosschecks.
Local focused tests:28mod/arcade+20tail+23attribute=71. Remote results for the
expanded workflow must be recorded separately. The174-to198-bit player block
remains opaque in every pinned source; no insertion/default is proven. Full
tail serialization coverage is not a cross-profile migration, full parser
acceptance or deterministic compatibility. R8 remains the latest replay. Keep
the offline-only instruction and full replay upgrade objective active.


## Canonical upstream line endings — 2026-10-18

CI39156545185 exposed an exact-source hash mistake in the new tail verifier:
the41810 hash a970f107... was a CRLF checkout, while the pinned official Git
blob is879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd.
Windows also checked out96477 as CRLF. The verifier now requires the actual
41810 Git blob digest, and CI materializes and hash-checks both exact upstream
blobs from pinned9af3ea7 on each OS. No schema semantics were changed and no
hash guard was broadened. The new canonical-lf fourteen-fixture report repeats
all EOF/member/private identity/seed checks successfully; keep older reports as
history with their original working-copy digest. Record the subsequent remote
run separately; the failed run is not passing CI.


## Measured current collection evidence and broader check — 2026-10-18

Run39156204685 succeeded,33Linux tests allpassed. Bot38469fa published exact98348
XML-declaration evidence:5418/5418 observed current collection IDs have direct
License candidates;5419 direct IDs exist. Legacy263names yield56 exact-name
observed candidates (54without recorded declaration reason,2with unresolved
parents),6exact records without a direct License and201absent exact names.
Do not promote this into a263-name migration. Preserve207 unresolved names and
all availability bytes. See dated direct-candidate assessment and collection doc.

One broader sandbox discovery run at93a5d0b ran761tests with4failures,9errors,
4skips. Permission-limited rename/junction operations and missing R3/R4/native
fixtures remain explicitly recorded. One failure was historical config CRLF
drift: its canonical1201-byte blob MD5d170b1ad65ebcde3f4252e3088b0c102 is now
materialized locally and pinnedLF in .gitattributes. Its7BuildConfigTests pass.
This focused correction does not relabel the broader run as passing or duplicate
the separate PR branch's prepared regression lane. No replay or client changed.


## Passing canonical CI and direct-candidate planner — 2026-10-18

Run39156842765 at1366ae0 passed Linux+Windows, each71focused tests,2real attribute
fixtures,3mod cases,14complete-tail fixtures and10content-addressed header
bindings/4arcade sections. Both source-static reports have identicalSHA256
abc902b7bcf3fc000da99a4444db1b11307b7dbe8816bbc174572012b5ce5820.
This supersedes the failed newline-binding run, not the separate unsuccessful
broader sandbox discovery result. No client or replay write was performed.

The new `plan_collection_candidates.py` accepts the exact hash-bound98348
license projection and its bound catalog-only collection observation. Local
13focused tests pass including the actual fixture. Its new report explicitly
keeps56candidates (54without recorded reward-declaration reasons+2with parent
reasons),207unresolved names, field-level unresolved reasons, namespace
collisions and duplicate blockers. It never marks the whole collection eligible,
infers aliases or writes ownership/member/replay data. Its separate small
Python-only CI avoids another game-data extraction; record its result separately.
R8 remains latest, the full upgrade objective is unfinished and no client launch
is permitted under the user's current instruction.


## Verified candidate plan CI — 2026-10-18

Run39157801856 at7ce68ca passed both Windows+Linux, each13tests/no skips and
an actual pinned-source CLI reproduction of56candidates/207unresolved names.
This is separate from the71-test/full14-fixture format CI and33-test exact-data
collector run. All intended offline milestones are published; no new replay
exists. Preserve original/R8 and the offline-only/full-upgrade goal, which
remains unfinished because legacy aliases, opaque player-field migration,
package/catalog/ability/instance/rule/sync compatibility remain unresolved.


## Incremental source backup through ac52010 — 2026-10-18

The verified source delta6fffca8..ac52010, current docs and focused-CI/candidate
reports are saved as hots-offline-static-catalog-ac52010.zip (807013bytes,
SHA256b5cc33e7810f6a35dc88bc4917c91898eb87bc670f1c75b8db8eb14cb9a327a1).
It requires the existing base7e23a6a archive and6fffca8 addendum; preserve both.
Upload to the existing OneDrive checkpoint folder succeeded, and fresh cloud
size/QuickXor matches local bytes. QuickXor is not cryptographic, and no remote
SHA256 re-download was performed. The archive includes all new source and CI
throughac52010; this later upload receipt is separate bookkeeping. No raw donor,
new replay or client result is included. Keep the full-upgrade goal unfinished.


## Additional current controls and unresolved-field research — 2026-10-18

The later offline evidence expansion adds6current98348 replays on6other maps,
7,247,399bytes total. Independent review confirms183equal type/link comparisons
across75shared types, no disagreements; a fresh Abathur control core audit and
separate lifecycle walker agree with saved results. These yield9new other-map
candidates,42combined unambiguous candidates, while the33Dragon-only decisions
remain unchanged. All6share4base handles but have different further packages
and mod checksums. Do not infer full cross-map independence or automatically
apply the9candidates. Exact URLs/digests/context are retained; raw donors are not.

The player-opaque forensic summary authenticates no named internal slice or
174-to198-bit conversion:146varying known-field groups have no matching slice,
constant hits fail wrong-player/match controls, and the adjacent known identifier
is a strong positive control. Do not append24zeros or transplant account data.

The header recovery investigation SHA-checks591cached headers. EU candidates
point to all6currentpayloaddigests but admit936unselected version combinations
under unproven zero-version semantics; no98348header binding was obtained.
The exact3USdepot objects still404. Do not truncate depot SHA256 into CASC keys
or select regional versions by recency. CASC contents were not enumerated.

Nineteen inspected public XML files now match98348projection file digests exactly.
Their old-name hits are visual model references; their explicit conversion table
maps currencies/loot chests, not source entitlements. This bounded subset does not
rule out fields elsewhere. A broader exact-build alias scan is still separate.
R8 remains latest; full upgrade, replay determinism and gameplay stay unproven.
The user continues to prohibit launching HotS.


## Bounded replay screening and exact XML scanner — 2026-10-18

The NGS ranged metadata control matched complete local header/details with6HTTP206
requests/1821bodybytes. The prototype then screened40objects within243requests/
205526bodybytes, allobserved98348/rootgates; these remainpartial metadata evidence.
The new portable ngs_range_details.py has15passing focused tests, including an
authentic offline fixture, bounded inflation/sector refusal and strict transport
guards. It does not validate fullobjects or infer unitmapping. No rawplayers,
chat or donors are published. Dedicated2OSfixtureCI is separate fromliveproof.

Two selected Nova objects were fully acquired with their observed strongETag
If-Match and independently protocol-roundtripped. Other-map downloads total
10,717,617bytes under12MiB. The8other-map controls nowyield256equal comparisons/
79sharedtypes and44combined candidatepairs, includingHeroNova75->112 and
NovaHoloClone89->743. The earlier33Dragon-only decisions remain unchanged; the
11othermapcandidates do not establishcrossmap independence/automaticeligibility.
BothNova trackers have noNovaHoloCloneCloaked typename. One exact98348NovaXML
file declaresNovaHoloClone withcloakbehaviors; itsCloaked absence remainsfile-only.

scan_collection_alias_nodes.py has30focused tests and independent19/20-file
realdata checks. It requires every5575XML descriptor/hash/metric plus fresh
version/IsPtr metadata before claimingcomplete coverage. It keeps207collection
queries separate from4fixed CUnitidentity queries, noalias/effectivecatalog
orownership mapping. The forthcoming exact-extraction workflow outcome must
be recorded separately; subset absence flags remainnull. RawXML staystemporary.

The concurrent completeoffline regression workflow was preserved during rebase.
Run39159375110 at3d786d2 passed801tests/38modules in each of3prepared lanes,
with explicit skips:38Linux,4Windows/pwsh,4Windows/PowerShell5.1. This broader
prepared-corpus evidence does not erase the earlier local limited result and
does not prove engineplayback. R8 remains latest; no client was launched.


## Full XML evidence and prepared-fixture correction - 2026-10-18

Run39160460385 at4f3757a passed30tests and all5575exact XML checks; botccb25a1
published238exactmatches for63legacy names. Absence applies to this projected
XML scope; numeric links/replacement/entitlement semantics are not inferred.
Dedicated Range run39160460366 passed15tests on both OS including realfixture.

Complete regression39160460383 correctly failed on one unexpected missing NGS
fixture skip per lane:846tests/40modules ran with no unittestfailures/errors,
but skips were39Linux/5eachWindows. The workflow now stages the same bounded
SHA-pinned public fixture and sets NGS_RANGE_CONTROL. No whitelist, assertion
or runner was weakened. Record the corrected run separately; no client or
replay write occurred, and R8/full-upgrade state remains unchanged.


## Complete current XML assessment and offline installed storage - 2026-10-18

The complete 5575-XML report is now assessed in dated collection-reference docs
and projections. NovaHoloCloneCloaked has zero direct CUnit declarations in that
XML scope; NovaHoloClone/AbathurEvolvedMonstrosity have one each and the tower
has eight, including Dragon. No numeric replacement is inferred. The 33 visual
families each have 3-5 current License candidates (121 total); same-file-only
uniqueness is false. Five HyperlinkId/reward chains are source-reference
candidates only. Independent joins/global identity counts agree. Keep existing
56 exact-name candidates and all 207 unresolved conversion names unchanged.

Installed CASC was opened offline with verified managed DLL provenance and
read-only index/data paths. Configuration ReadWrite opens used scratch copies;
a denying HTTP handler passed its canary and operations recorded zero requests.
Actual root MD5 matches c3b3c8bc82e3a5a62e550fdde9a40c28. All 1208637 filenames
were scanned: 324 exact metadata names and no .s2mh filenames, a filename-only
absence observation. Three identified Dragon metadata files total 2311 bytes,
all MD5/CKey verified, and differ from cached map metadata. The only explicit
dependency999/0.0/local path gives no new exact header route. Partial-path Clear
NullReference is retained. Independent review passed; raw members/DLL stay local.
Frozen machine-bound research sources are retained under research/ with docs.

Corrected CI39160865689 at8c91741 passed all three prepared lanes: 846 discovered
and run tests/40 modules, no failures/errors/unexpected skips, declared skips
38 Linux and4 per Windows lane. The genuine NGS fixture test actually ran.
Earlier failed run39160460383 stays historical. Original and R8 SHA256 values
were rechecked unchanged; no client launched, no new replay, full upgrade remains
unfinished under the offline-only user instruction.

Two PowerShell-produced CASC JSON reports are stored as LF by .gitattributes.
The publication-binding v2 retains original artifact and published Git blob
digests/sizes, verifies identical JSON values and every staged file hash.
Executed research-code hashes are unchanged. Original artifact receipts retain
their original CRLF report digests; they are not relabeled published hashes.


## Verified source/evidence backup through 1e31a3d - 2026-10-18

Complete regression39161650744 passed the published1e31a3d source: all three
lanes846tests/40modules with declared38Linux/4Windows skips, actualNGSfixture
executed and no failures/errors/unexpectedskips. The small source delta
ac52010..1e31a3d and new docs/projections are backed up as
hots-offline-evidence-1e31a3d.zip (373204bytes,
SHA25606b01243ef256c30e87470595f4e166f3e9a1b777ea21395365a7b2a2911dcb4).
Existing OneDrive checkpoint upload succeeded; fresh cloud size/QuickXor equals
local bytes. No independent remote SHA256 download claim is made. Preserve the
three earlier base/addendum archives listed in the manifest. This later receipt
is bookkeeping after the backed-up source commit. No new replay/client outcome;
R8 and the unfinished offline-only full-upgrade objective remain unchanged.


## Genuine current EU reference and static registry proof - 2026-10-18

One public Heroes Lounge Lost Cavern replay (978482bytes, SHA256a3c97e9a...a01c4)
passes exact98348 build/base/data/root gates, all observed official/semantic
core roundtrips (144708/99/6181 events), full mod/tail EOF and private slot/seed
checks. EU is explicit in player/creator regions and all8 terminal handles.
It binds shared base packages169990/65580,170002/65559,169991/65552,169992/65663.
First3exact headers downloaded/SHA/wireverified and equal cachedbytes; fourth
f644ce88...ee75c0 returns404 and is outside all13cached HeroesData versions.
None of previous936 relaxed combinations is this current full tuple. ARAM
does not bind the final Dragon package. No missing header substitution.

New registry auditor12tests and independent33header reproduction establish
original HeroesData264names -> first-dedup263 EXACToriginal/R8order; other4old
registries empty. All28cached candidates/936combos fail current5418coverage.
Closest65662 raw5488/unique5409 is exact current relative order missing9OWC20
tints, each bound to currentXMLLicense. License1209137 exists in rawXML but
not observedregistry, so all-declaration concatenation is not a generationrule.

Availability15case aggregate has13identicalcurrent keylists,13differentcurrent
availabilityblobs, original/R8same; nonezero/constant. Do not zero-fill or copy
availability as static data. Registry keylist proof does not resolve the32byte
record semantics or207legacy conversions. Actual research source stays frozen.
Full offline CI now includes boundedSHAcurrentEUfixture+stream/lobby/package
checks and12newregistrytests; record its remote result separately. Remaining27
NGScandidates screened within162HTTP206/48405bytes; no newNova/Abathur.
R8unchanged, no client launched, full upgrade remains unfinished.


## Verified EU/registry CI and source backup through 4897152 - 2026-10-18

Complete offline regression39164232875 passed published4897152 on Linux and
both Windows PowerShell lanes:858discovered/run tests in41modules, no failures,
errors or unexpected skips; declared38Linux/4Windows skips. The actual pinned
NGS range fixture ran. Each lane also acquired and verified the genuine current
EU fixture:144708game/99message/6181tracker events, complete lobby EOF and exact
four shared package tuples through HeroesData169992/65663.

The verified small source delta1e31a3d..4897152 and sanitized docs/projections are
saved as hots-offline-eu-registry-4897152.zip (153056bytes, SHA256
994e33a81453735cec45326d0bf63f3fb6543db63703b55fb6652f0510bc6820).
Existing OneDrive checkpoint upload succeeded; fresh cloud size and QuickXor
match local bytes. No independent remote SHA256 claim. Keep all four required
earlier archives in its manifest. This later bookkeeping receipt is outside
the backed-up4897152source. No new replay or client outcome; R8 and the
unfinished offline-only full-upgrade objective remain unchanged.


## Exact current EU HeroesData header recovered - 2026-10-18

Read docs/EXACT_EU_HEADER_RECOVERY_2026-10-18.md and observations/exact-header-98348.
The222049-byte HeroesData169992/65663 header was reconstructed inRAM and matches
the FULL genuinecurrentEUreplay SHA256f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0.
Independent RAM assembly reproduces both candidate digests; onlygap1502matches.
The exact private header passes independent generic completeEOF and lossless
roundtrip. Its rawregistry5497/unique5418,12localehandles,14attribute definitions
and99scorelocalization keys are artifact-authenticated. This supersedes the
missingEUHeroesDataobject state, not the earlier depot404 or failedXMLcontrol.

New boundedlosslesscodec21tests and36authenticcontrolheaders pass; attribute
projection73wireexactcontrols/5negativecontrols and registry7tests/2alternatives
also pass. Source/receipts are frozen with byte-preserving attributes so actual
executed SHA pins remain truthful. OlderinputURLs404; do not claim CI rebuilt
the realheader. No rawheaders inGit, newreplay, clientlaunch or deterministic
playback proof. EUDragonfinalpackage,3missingUSheaders, availability/207legacy
aliases and opaqueplayer conversion remain separate work. R8 unchanged.


## Portable exact-header reproduction - 2026-10-18

Root recover_current_eu_heroesdata_header.py now accepts explicit source65662,
prior65661 and currentEUreplay paths, verifies actual complete core/schema/root/
region/package/terminalhandle context and reconstructs inRAM. Only FULLf644SHA
permits independent complete decode and exclusiveheader creation. Existing
outputs/reports refused; mismatch creates noheader. Root actualCLI reproduced
222049-byte f644 after pure AST-identical registry helper extraction, recorded
in root-published-portable-reproduction.json. Eight writeguard tests and seven
registry invariant tests pass; independent root transform review passes.

Complete CI39165393339 at07304a0 passed879tests/42modules on all3lanes,
38declaredLinux/4Windows skips, actualNGSfixture and genuineEUcore/lobby checks
executed. It did not reconstruct the realheader. This later portable milestone
adds15tests; record its remote result separately. Raw headers remain outsideGit.

Three known US/EUCore/Teams/Heroes pairs have identical archivepayload digests,
attribute field5 and outerroot1 bytes, but30/31 regional leaf differences in
identities/namespaces/workingSet/locales/dependencies. Do not use a region-only
replacement. A bounded five-division HeroesLounge EUDragon route found no replay
links/zero matches in87standings rows (242128HTMLbytes); this is scoped evidence,
not global absence. No more replay downloads or clientlaunch. R8 unchanged and
full replay conversion/simulation remains unfinished.


## Verified894-test source and source-only cloud backup - 2026-10-18

Complete offline39165828602 atf97e57a passed allthree lanes894tests/44modules,
no failures/errors/unexpectedskips,38declaredLinux/4Windows skips. All15new
outputguard/registry tests actuallyexecuted, plusNGSfixture and genuineEUcore/
lobby checks. Actualf644reconstruction remains independently verified LOCAL
fullSHA evidence, not a hostedCI fixture claim. OfficialEUmanifest rechecked
2026-10-18T21:04:20Z still2.57.0.98348/samebuildconfig;874bytes SHA recorded.

The source delta4897152..f97e57a plus sanitized reports is backedup as
hots-offline-exact-header-source-f97e57a.zip,168632bytes SHA256
32d9c801ae62793d3d3a7519ea60210b4fb6c0b64d81d2098438116ce07bdbb5.
ExistingOneDrivefolder upload andfreshsize/QuickXor matchverified; no independent
remoteSHA256. This source-only ZIP contains no rawheaders/replays/playerrecords.
The separate298106-byte localarchive with3staticheaders remainslocal: automatic
approval review rejected its cloud upload and a specific user question is
pending. Do not retrythat payload without approval. This later receipt is not
inside thef97e57abackup. Keepallprevious5basearchives. No client/newreplay or
full-upgrade completion; original/R8 unchanged.


## Two exact current US recoveries and availability representation - 2026-10-18

Read docs/US_HEADER_RECOVERY_AND_AVAILABILITY_2026-10-18.md and new us/availability
receipts. All3knownUSbaseheaders were reconstructedWHOLE-byte/fullSHA from EU
with actualUSmetadata and namespaceoffset held out from each testedtarget;
6wrongmodule controls reject, independentroot/reviewer repeatsPASS. Missing
USHD243553/65665/0633... (222049B) and Dragonmap243571/65624/3c2d... (4057B)
nowexactfulladvertisedSHA matches, genericEOF/wire/privateactualreplaybindings
andindependentRAMrepeatPASS. Rawheaders remainprivate. CurrentUSset5of6exact.

DataMod280539/16/42afe remainsunresolved. Initialbcbacce negative and separate
one-shot source-namespace-preservation50d7f158 negative are unsaved. The EU
DataMod lies outside the base namespace relation; misses do not identifyactual
USnamespace/otherfields. Stoprecipespendingconcretenewsourceevidence.

Availability15case/2270720B representationaudit20tests and two independentfresh
JSON-exact rerunsPASS. Two2Bpatterns globallyidentical, zero+one-set-bitpattern;
notall16bitsset.10active/varying positions matchdetails participants but5760
bijections remain; workingoccupiedrelation8709120 andordinal0. Fourcurrentcases
haveextraoccupiedobservers. No patterns/IDs/vectors emitted orownership/default/
unique-slot mapping inferred. Local20tests separatefrom894CI sourcebaseline.
Original/R8 unchanged, no client ornewreplay; fullupgrade unfinished.


## VerifiedUS-recovery milestone CI and cloud source backup - 2026-10-18

Complete offline39167582802 at537555b passed894tests/44modules on all3lanes,
38declaredLinux/4Windows skips, no failures/errors/unexpectedskips; actualNGS
fixture andcurrentEUcore/lobby checks executed. Realheader reconstruction and
20availability tests remain explicitlyLOCAL evidence, independently reproduced.

Source/evidence deltaf97e57a..537555b is in hots-offline-US-header-source-537555b.zip,
112081bytes SHA2562b4507c7931a8cd2de8b9ec96be12b441c549d235017fa6b354db7abf12928e3.
ExistingOneDriveupload succeeded withfreshsize/QuickXor match; no independent
remoteSHA256. It contains no rawheaders,replays orplayerrecords. Preserve prior
sixrequiredsource archives. Two exactUSheaders also havea45278-byte LOCALzip,
SHA2562cc529da11bf69b98c21309a93ee007cd97c95107031a0cc15fa7e35ccba555b;
no cloudrawuploadattempt. EarlierEU3headerarchivepermissionquestion remains
pending; neverretryitsrejectedcloudpayloadwithoutapproval. Thislaterreceipt
isoutsidebackedup537555b. Original/R8 hashes recheckedunchanged.5/6USheaders,
DataMod42afe unresolved, no client/newreplay/full-upgradecompletion.


## Availability vectors across21current controls - 2026-10-18

Read docs/AVAILABILITY_VECTORS_21_CONTROLS_2026-10-18.md and availability/vectors
research/receipts. Frozen13:5760=2880active x2never-participant arrangements,
12/19same-account exact,0/7781different-account exact,2statisticalmaxima.
Extension admits all8existing other-map controls:21cases/0failures/0acquisition;
frozen13comparison reproduced exactly.240active arrangements exhaustively
checked,59/81same-account exact,0/20919different exact,1statisticalmaximum at
direct working-set alignment.22same-account pairs still differ1-12rows/74total;
no arrangement makes all81equal. No ownership or semantic mapping is selected.
28focusedtests/no skips and independent fresh13+21JSON-exact reproductionPASS.
Actual explicitreads61018250B/distinctreplay29002257B/availability3640896B.
Extension fresh actual98348/root+fulltail/privatecrosschecks binds prior core
profiles, does not rerun core event decode. Researchtests local, separate894CI.
Private vectors/accounts/permutations absent from public output; no generated
availability/replay/clientlaunch. Original/R8 guards unchanged, fullupgrade
unfinished. Frozen code remains byte-preserved; see publication-bindings.json.


## Authenticated access helpers and bounded acquisition limits - 2026-10-18

Read docs/ACCESS_SEMANTICS_AND_SOURCE_LIMITS_2026-10-18.md and new access-semantics,
us/depot-search, legacy-build-root receipts. SixcurrentCASCtext779428B complete
MD5/SHA and4zeroHTTP/canary/configunchanged guards pass; retainedClearNullRef.
ActualHeroesLib/Config localGitblob identities and fullrootrefetchedpublicSHA
match pinnedpublicsource. Fourcurrenthelpers combine rewards and free/practice/
rotation/modebranches, notownership oravailability32B semantics. Authold263
registry DOES NOT contain NovaHoloCloneCloaked/AbathurEvolvedMonstrosity/
TownCannonTower; keep their unit-catalog investigation separate. Oldspelling
groups145Skin/8otherMount/110remaining are notcatalogclasses. Staticfindings
RAM-exact rootrecompute + independentreviewPASS, no newunit/CIclaim.

ExactDataMod42afe stillmissing:5newdocumentedroutes, KR/CNHTTPS404 and3legacy
URLError,0bodybytes/0save/5acquisitionfails/0validationfails. PriorUS/EU404not
repeated.8localguards+independentfakeopener5attemptreproducePASS. Bothcomplete
primaryURLsourceblobs rootrefetched/fullSHAverified; no moreheaderspeculation.

Original41810header root83d43a8647bb5ca5caa6f2f09064da55/fixedc585f3548fb8f9776fa1fba4dfec2b9a
freshverified.12operationprimaryhistorysearch foundno41810config/EKey/catalog;
BlizzTrack202records/10perpage needs21pages despite20reported, final2ontail.
Oldestobservedmanifest2022-06-10/88122, not41810.4APIresponses5592B and offline
exactreproducer+independentreview retained; scopednegative, notglobalabsence.
No CDNrequests/keyreinterpretation/fullclientdownloads, no client/newreplay.
Original/R8 unchanged and fullupgradeunfinished. Raw6game-text/headerbodies
remainprivate; frozenresearch sources/hashes exact in publication-bindings.


CompleteofflineCI39168917474 atd8f0f8e passed all3lanes894tests/44modules;
38declaredLinux/4Windows skips, zero failures/errors/unexpectedskips. Actual
NGSfixture andcurrentEU144708/99/6181/fullLobbyEOF checks executed. Frozen
28vector/8endpoint tests and staticaccess/historyactualproof remain LOCAL,
not hostedCI orengineproof. See availability/vectors/complete-offline-894-vector-milestone-CI.json.


## Verified vectors/access source-only backup throughd3e0af9 - 2026-10-18

Source/evidence delta537555b..d3e0af9 is backedup as
hots-offline-vectors-access-source-d3e0af9.zip,192422B SHA256
523034d2afbda9737244a3595d3eb68bd89f210b6577b8e811e53dd1f08c7570.
Bundle and ZIPinventory verify; no rawheaders/replays/game-text/playerrecords.
ExistingOneDrivecheckpoint upload succeeded, fresh cloudsize/QuickXor matches
local. No independent remoteSHA256 claim. Preserve all7earlier sourcearchives.
This later receipt is outside the backedupsource. Original/R8 hashes rechecked
unchanged; current21-case/sourceproof updates are in the taskoutputs status.
Earlier rawEUheaderarchive cloudapproval question remains pending; no raw
archive retried or uploaded. No client/newreplay/full-upgradecompletion.


CompleteofflineCI39169427494 atd3e0af9 also passed all3lanes894tests/44modules,
38declaredLinux/4Windows skips, no failures/errors/unexpectedskips. ActualNGS
fixture andgenuineEUcurrentcore/lobby checks executed. No privateCASC/history/
realheaderrecovery or28vector/8endpoint researchtest claim inhostedCI. This
receipt islaterbookkeeping outside the source-onlyd3e0af9ZIP.


## Native serialization labels and preserved 41810 module evidence - 2026-10-19

Read docs/NATIVE_AND_PRESERVED_41810_EVIDENCE_2026-10-19.md and the matching
native-serialization, preserved41810, player-block-history and catalog receipts.
Byte-only inspection binds the 53,573,840-byte current PE to SHA256 efdf5a2f...dca9.
Independent checks reproduce all 320 selected literals, 11 contexts (33,666 bytes),
29 RTTI structures, and the text-version/fixed-word distinction. Observed
ClientLicensesList and BnetHeader neighborhoods establish no field membership,
bit layout, ownership meaning or missing namespace value. Nine selected integer
address scans have no matches. Investigate the embedded table/index grammar.
No client image or DLL was loaded, no debugger/injection used, and no binary copied.

Five preserved 2022 dump module/RSDS records identify the old 0.17.0.41810 image:
size 89,478,144, checksum 45,759,189, timestamp 1458935250; PDB GUID
7BF26548-FE37-4F3F-94F0-218512BDB807, age 49. The old executable/PDB body is unavailable.
Only metadata and first 45 Error-header lines are decoded. Their generic
NGDP:E_DATA_ERROR identifies neither an object nor its cause. Full input hashes
are unchanged; root independently verifies first-module structures and headers.
Memory streams, later diagnostic hex/session sections and Variables remain unread.

Separate 15 manifest/NGDP/trace files total 13,364 bytes, read twice. Five identical
740-byte manifests declare 88481, BuildKey 0534650161f366f2f048320d85b32893 and
CDNKey c53d29ee65044954474c758516b15ab4. The old replay root is absent in those
15 texts. Independent captured-read recomputation matches JSON and serialized
bytes. These manifests do not establish which content the old executable loaded.
Keep module identity, saved content manifest and replay root separate; no original
41810 BuildConfig is recovered.

The additional 6 catalog-route, 10 historical-archive and 8 player-history calls
are scoped negative evidence. Unsupported endpoints do not imply source absence.
No 41810 catalogs or internal 174-to-198-bit layout are admitted. Static research
checks are local evidence, separate from unit/hosted CI and engine proof. Raw
binaries, dumps, logs and private values remain outside Git. Original/R8 are
unchanged, full migration remains unfinished, and no further guessed header
recipe is supported. Frozen producer bytes are bound in publication-bindings.json.


## Native BSN and current ClientInfo binding - 2026-10-19

Read docs/NATIVE_BSN_AND_CLIENTINFO_2026-10-19.md and the native-bsn receipts.
The actual 98348 PE contains a complete 391633-byte BSN metadata container,
8330 types. Cross-game public source suggested the grammar; actual HotS record,
reference and name validation supplies the binding. Do not treat cross-game
source as an exact HotS release. Header bit6/native memory offsets are unknown.

Current ClientInfo has 18 named fields. All21 current controls/222player records
bind all13 anchors, player ends and exact consumed-bit reencoding. After invalid
TalkerId, network8+voice64+profile96+empty permission-count31 total199bits. The
frozen current-tail profile incorrectly consumes the first network bit as a
secondary-present flag and treats the remaining198 as opaque. All actual first
bits are0, so this did not break that cohort's byte reconstruction. A one-bit RAM
negative control preserves native layout and makes the old profile reject.
Preserve historical/current observed profiles and their old receipts. Use the
separate explicitly pinned native reader for new current ClientInfo inspection.
The old174 region is unproven; do not zero-extend or infer a 41810 migration.

Native client License::Id is32bit, distinct from resource-map64bit identifier.
No ownership or32byte availability semantics, missingDataMod namespace, complete
conversion or simulation result is established. Private inputs remain outside
Git. No client execution. Original/R8 unchanged; R8 still declares98285.


## Native ResourceAccessMatrix representation - 2026-10-19

Read docs/NATIVE_RESOURCE_MATRIX_2026-10-19.md and native-resource-matrix receipts.
Actual native type5830 is count32 x ScopeResources[16] x ResourceState/u16,
distinct from ResourceAccessList. StartGameRequest places resourceMap, matrix,
disabled-list adjacently. Fresh21 controls bind boundaries, all113778rows /
1820448cells and exact block bytes with fullEOF/private/build/root guards.
All5418 ordered resource IDs agree. No state bits, ownership, entitlement,
scope/player assignment, license filling or historical mapping is inferred.
One static PE read; actual audit61324571 explicit input bytes,3640896 row bytes.
12local research tests PASS; independent code/static/saved-report review PASS,
without claiming another fresh actual-matrix run. Raw values/patterns remainRAM.

Portable v3 independent code review14tests PASS, post-recursion cap and mutation
rejection verified; root14new+20existingtail testsPASS. Eight-attempt oldfixture
search includes2blocked calls,4GitHub+2web calls; no exact41810/header acquisition
in that search. Filename39445 and one unversioned fixture are not build proof.
Later bounded header acquisition must be recorded separately. No client/replay
write/full-upgrade completion. R8 remains98285; old174 layout remains unbound.


The native-reader source checkpoint af8ef7c passed complete CI run 39173281503:
908 tests across 45 root modules on each of Linux, Windows PowerShell 7 and Windows
PowerShell 5.1. All 14 new tests executed, and each lane decoded ten actual EU
ClientInfo records with matching anchors, identities, ends and exact spans.
Declared skips remain 38 on Linux and 4 on each Windows lane. The actual NGS
range fixture and current EU core/lobby checks executed. These hosted checks
did not inspect the installed PE, private dumps or rerun the 21-case matrix audit.

A subsequent 4096-byte HTTP 206 prefix read of the formerly unversioned public
fixture reports 2.35.0.66488 with executable/base/data66488, excluding it as an
41810 candidate. Exact Content-Range and immutable commit URL are retained.
The prefix was decoded with the pinned official schema, then discarded; no
full replay/Gitblob hash or complete archive validation is claimed. This header
check is separate from the earlier eight-attempt zero-acquisition search.


## Native reader and matrix CI and source backup - 2026-10-19

Complete offline CI39173707346 at cbc2113 passed all three lanes:908 tests across
45 root modules;38 declared Linux skips and4 Windows skips. All14 native-reader
unit tests,10 actual EU ClientInfo records, EU core/lobby and NGS fixture checks
executed. The21-case matrix research and12 focused matrix tests remain local,
with separate independent code/static/saved-corpus review; no hosted actual-PE,
dump or complete-matrix-corpus claim.

Source-only delta3e5ebb7..cbc2113 is saved as hots-offline-native-bsn-source-cbc2113.zip,
264527 bytes, SHA256bdab412e6b9bfe08d13e25a2773c19ccf025ce61fa75877722de9db6ced4df62.
The bundle/inventory verify. All35 copied source/evidence entries exactly match
already-public Git blobs. Initial upload approval rejection was resolved after
complete public-payload and existing personal-project destination checks; upload
then succeeded and fresh cloud size/QuickXor match. No independent remote SHA256
claim. Preserve all nine prerequisite source archives. This receipt is later
than the archive and does not alter its backed-up commit.

Four external tool calls/six queries found no ResourceState flags or scope-index
constants; cached exact-name negatives and full limited search metadata are
pinned. Root reproduces the saved ledger JSON exactly. No source definition was
accepted, no state-bit or ownership mapping inferred, and no global absence
claimed. Original/R8 unchanged; no client or new replay/full migration completion.


## Historical layout and formal namespace research - 2026-10-19

The source/JSON checkpoint in docs/HISTORICAL_LAYOUT_AND_NAMESPACE_2026-10-19.md
publishes five bounded lanes with exact frozen byte bindings. Five old41810
preserved dumps supplied only the two approved image fragments:1036 bytes/case,
5180 total. No complete BSN candidate in those ranges/version1..16 heuristic;
no old native schema or widths established. Independent saved-proof/source
review reran13 synthetic tests without reopening dumps.

HTC20 immutable fixture prefixes:20 strict206 reads/81920 application bytes,
20 decoded headers,zero41810;24 canonical Git trees recomputed. Prefix SHA is
not whole-file authentication. A separate652332-byte full39445 control has
fullSHA/Gitblob and all six core stream checks. Its unchanged historical-tail
failure remains retained. Separate pinned schema1 diagnostic passes EOF,
reencoding and10 private identity/seed gates; no41810 schema follows.

Original/R8:only count7/count31 tested. Seven-bit count candidate fits175-bit
boundaries; current31-bit count is physically impossible in all20 records.
Current-named first-five-field prefix alignment does not authenticate old
field names/semantics. Community build32 values64541/60636 do not match source
header builds. No old-to-current value conversion or seven-bit parser change.

Formal namespace145 is nativeu32. S2MapInfo graph has no path to that type.
Five exactUS headers account for all87 observed definition pairs; no formally
attributed missingUS DataMod namespace exposed. EU source zero definitions
and root namespace do not establish US value/package ownership. Count9 is
DefinitionList count width; observed11 is index width. No arbitrary4byte scan,
offset choice, candidate header or full native-prefix claim in this lane.

Frozen sources/reports copied byte-exact under new exact-header subdirectories;
33 focused scratch tests pass/no skips;31 self-contained relocated tests pass.
Two HTC metadata tests retain private-cache dependencies and are not repeated
after relocation;24 public Git trees independently recompute. Saved-proof gates
pass. Producers retain private scratch dependencies; publication verifier uses
only public checkpoint files. No new actual private-input rerun, hosted CI,
client launch, replay write, ownership mapping or migration completion.
Original/R8 unchanged; no backup or root module/CI/output-status changes here.


## Native MapInfo and historical count constraint - 2026-10-19

Read docs/NATIVE_MAPINFO_2026-10-19.md and native-mapinfo source/observations.
The separately pinned191-type snapshot names all32S2MapInfo fields. All21
current controls/136records match complete ends, handle identities and exact
consumed bit spans, with fresh build/root/fulltail/privateidentity/seed guards.
Last32bits resolve to m_addMultiMod1 plus m_requiredPermissions count31, empty
in all136.13focused testsPASS; independentphysical-bit reconstructionPASS on
6actualUSDragon records. Independent382-type PE projection matches all191
selected records exactly. No PE/client is needed by the portable root reader.
CI adds8actualEUMapInfo records; inspect new run logs before claiming its result.

Read docs/LEGACY_MAPINFO_COUNT_CONSTRAINT_2026-10-19.md and legacy-mapinfo
receipt. One explicitly derived RAM-only graph changes only PermissionList
type1828 count31to7/max127. Original5+R8same5+genuine39445six all32fieldends,
identities, arcade section boundaries and independentphysicalbits match; all
16counts zero/finalwidths[1,7]. Original/R8derivedtokensidentical. Current
unmodifiedgraph has13wrongends+3lastrecordphysicalpayloadfailures. This is
structural consistency, not authenticatedoldnative semantics or a conversion
rule. Frozen production profiles are unchanged; do not silently zeroextend.

Header-field-exposure receipts bind all15sharednamed fields and9commonvariant
fields per each5exactUSheaders to MapInfo. EUDataMod retains12/15exact;3
differences(identity/visuals/deps)werealreadyreplacedbytheearlierrecipe.
Header.root1 is GameHeader.m_dummy BOOL, not an author record. Other header-only
fields and the target namespace remain unobserved; no new recipe is supported.
Source/archive/core/simulation proof remain distinct. No rawPE/fullBSN/header/
replay/playerdata published. Original/R8 unchanged; no client/newreplay and
full migration unfinished. See exact publication-bindings for frozen bytes.


## MapInfo complete CI, source backup and original-header constraints - 2026-10-19

The MapInfo source checkpoint 4531b64 passed complete CI39176244114 on Linux,
Windows PowerShell7 and PowerShell5.1. Each lane discovered46root modules and
ran921tests, with38declaredLinux/4Windows skips, zero failures/errors/unexpected
skips. All13newMapInfo and14existingClientInfo tests executed. Each lane also
checked8actualEUMapInfo and10ClientInfo records with exact native span bytes,
EU144708game/99message/6181tracker/fullLobbyEOF, and actual NGSrangefixture.
The21case/136record research,14header research and preserved-dump reads remain
separate local evidence. No hosted current PE, private header or dump claim.

Source-only cbc2113..4531b64 bundle and ZIP are verified in the existing OneDrive
project checkpoint: hots-offline-native-mapinfo-source-4531b64.zip,322542B,
SHA256c02717a75651e05a4cbc1b2b6d3ce6e0c8b6ee1c5d18f627de22aa8ff3d34433.
All65source blobs across3commits were fetched from public GitHub and matched
exact SHA256/Git identities. All37ZIPentries accounted for:35exact public Git
blobs, verified bundle, generated relative-path/pin manifest. Fresh cloud size
and QuickXor match; no independent remoteSHA256. Preserve10prerequisite source
archives. Later CI/cloud/original-header receipts are outside that source ZIP.

Read docs/ORIGINAL_HEADER_MAPINFO_2026-10-19.md and original-header-mapinfo
receipts. All5exact original headers, including originalDragon, match75shared
named fields against the derived count7MapInfo hypothesis. Each explicitly has
root/0/17 as an empty versioned ARRAY; no absent field defaulted. All5complete
currentHeader bindings fail with old extra Bnet tags6,11,23 and missing24.
8synthetic guard tests PASS; total header reads243431B<262144 including an
aborted adapter check, with no further actual-header reread needed. This is an
independent empty-array correspondence; it does not authenticate old native
names/count width/permissions or authorize a conversion. Original/R8 unchanged.

Official live EU manifest refreshed2026-10-18T23:29:24UTC remains2.57.0.98348,
same874B/SHA as prior observation. No game client or new replay. Full migration
and deterministic compatibility remain unfinished.


## Complete native online lobby structure - 2026-10-19

Read docs/NATIVE_ONLINE_STARTGAME_2026-10-19.md and native-online receipts.
Native type5917 OnlineStartGameRequest is the ENTIRE current battlelobby member,
starting at bit0. The selected513-type graph names all25root fields. All21current
controls consume the exact whole member and reproduce everybyte, with12named
surrounding anchors/case,136MapInfo ends and222ClientInfo ends. The aggregate
is8897304typed fields and3314146wire tokens. EOFpadding0..7bits is explicitly
separate and must be zero. The portable reader has local independent budgets
and never changes shared native_clientinfo globals. All14focused synthetic
tests pass. No native PE or game process is needed for portable decoding.

CI now checks one actual currentEU whole member in addition to prior streams,
8MapInfos/10ClientInfos. Inspect hosted run logs before claiming new CI results.
The21case corpus is local evidence; no hosted private corpus claim. Old opaque
postplayer group names are not native field boundaries: licenses useu32 IDs,
globalResourceMap usesu64 IDs, and neither establishes ownership or scope bits.
This milestone is read-only. No original/R8 changed, no client launched, no new
replay written. Historical conversion and deterministic compatibility remain
unproven; full replay upgrade is unfinished.


## Native review and catalog-gap refinement - 2026-10-19

Read docs/OFFLINE_CATALOG_AND_NATIVE_REVIEW_2026-10-19.md and exact frozen
native-online-review/native-parent-tail/legacy-empty-permission-design/
startup-catalog-coverage/source-unit-lifecycles/EU-Dragon-new-route receipts.
Independent one-control whole-member physical proof and15research controls
pass. The2historical startupnullanchors are now sameDragon Greymane614 and
FaerieDragon470; Anubarak468 sameDragon, Kaelthas632 crossmaponly. This is
3/4same-map startupcoverage, not4/4. Expanded current44pairs/6unresolved.
All3unobserved types are materially used in sourcecatalogfields: Monstrosity36
191fields,NovaHoloCloneCloaked20731,TowerL2Standalone532140. Old531's407L2
and2Deadfields are unresolved, no globalalias. Original/R8targetedstats equal;
sourcegame/trackerexact. No source rules or deterministic equivalence follows.
CompleteClientInfo needs36additionalbits beyond count; no guesseddefaults.
Latest2EUDragonheaderprefixes97771/98025 rejected, no new donor/tuple.
OfficialEUmanifest2026-10-19T00:00:44UTC98348. No client/newreplay/fullupgrade.


## Source-limited MapInfo framing conversion - 2026-10-20

Read docs/LEGACY_MAPINFO_FRAMING_2026-10-20.md and legacy-mapinfo-framing
receipts. New explicit profile admits exactly3source-memberSHAs/16savedspans.
Only empty type1828 PermissionList framing count7to31 changes,24addedbits each;
all other fields/tokens/outside bits preserved. Original5/R8same5/39445six
actualrecords pass512root/3888allfield comparisons to unchanged currentreader;
all3wholemember inverses byte-exact.23synthetic tests and independent physical
splice/alignment/guard review pass. Newfailfast targetbounds guard precedesSHA.
No ClientInfo's36additional current-onlybits or entitlement values defaulted.
No rawmember/replay output, no HotS launch, no oldnative schema/fullupgrade claim.
CI adds actualoriginal5record RAMconversion/inverse JSON; inspect958test/48module
hosted results before claiming success. Executeddriver is frozen; futureguarded
copy adds loaded-module hash validation and has no additional actual-run claim.

Source5ad0131 backup verified in existing personalOneDrive project:292415B ZIP,
SHA256e40f8e3d40b78ab34bf3074c2ff5abd23717097aef49fe99a23cd64aabc8090c,
38entries,62publicblobstates/884776B exact,3commitdelta from4531b64.
Fresh cloud size/QuickXor match; no remoteSHA256 claim.11prerequisites retained.
This new framing source and laterreceipts are outside that older source ZIP.
Oldpackage metadata supplies no untried distinct globalrules archive route;
currentXMLspellings/Novareferences do not establish oldalias/ruleequivalence.
OfficialEUmanifest2026-10-20T06:25:32UTC still2.57.0.98348, same874B/SHA.


## Native setup value codec - 2026-10-25

Read `docs/NATIVE_SETUP_CODEC_2026-10-25.md`,
`observations/native-setup-codec-provenance-2026-10-25.json` and
`observations/native-setup-two-actual-2026-10-25.json` as additive state.
`native_setup.py` now exposes a strict value writer for the distinct native775
200-type graph used by current replay.initData. It pins its anonymous schema,
native STRING validator and private reader/writer, and compares with pinned
Blizzard96477 outer71/inner70. Canonical writing zeroes internal padding;
unchanged source reproduction validates and preserves original internal bits.

Local validation passed 46 new tests and 64 neighboring codec tests. Current EU
and R8 members both reproduced byte-for-byte, with 87,427 official logical nodes
compared. The existing CI current-EU gate now checks the new codec as well; its
future run is separate evidence. The official EU manifest checked today still
reports 2.57.0.98348. No Computer Use, client, replay write or sync change occurred.

This is a production offline codec milestone, not a completed historical
conversion. R8 still declares98285 and remains the latest replay. Preserve the
source and all checkpoints. Resource identity/ownership, current-only ClientInfo
semantics, historical catalog rules and deterministic synchronization remain
unresolved. The full5917 lobby encoder remains inverse-only; never treat this
native775 writer as a writer for that separate graph or guess missing values.


## Current whole-lobby value writer - 2026-10-25

Read `docs/NATIVE_LOBBY_VALUES_2026-10-25.md` and the new
`observations/native-lobby-zero-context-static-proof-2026-10-25.json`,
`observations/native-lobby-values-21-current-2026-10-25.json` and
`observations/native-lobby-values-local-tests-2026-10-25.json`.
The new `native_lobby_values.py` supplies an actual typed-value writer for the
current online5917 graph. The previous `native_startgame.py` remains unchanged
and source-only. Do not apply the older inverse-only limitation to this new API.

Fresh read-only Ghidra exports prove context0 for Battlelobby reader and writer,
plus CHOICE tag/child lookup, strict ASCII1..126, NULL and raw REAL patterns.
The exact existing selected513-type schema includes online5917 and offline5962;
public value APIs support online5917 only. All513 types/16kinds have synthetic
coverage; actual21 controls observe400 types/13kinds. Current native775 remains
a separate registry/root, sharing only the authenticated STRING helper.

All21 complete current members reproduce source and canonical bytes exactly;
8,897,304 logical nodes agree with the frozen independent reader. A public-EU
seed BLOB4B edit exists only in RAM: exactly one changed bit in its known span,
independently decoded, all other bits preserved. All source files are unchanged.
22 new tests plus110 neighboring tests pass locally. The new CI gate repeats
current-EU canonical/source identity and independent RAM mutation checks; assess
its exact published commit separately. No original/R8 replay or client was used
in this21-control integration, and no archive/member payload was written.

Full historical conversion remains false. Do not insert guessed ClientInfo or
SharedPlayerInfo fields, ResourceState/ownership values or catalogs. Current
ctor defaults and optional field preambles do not supply historical values.
Preserve all synchronization data. Latest replay remains98285-resumable-r8;
no Computer Use or game launch under the current user instruction.

## Latest human constraint — 2026-10-27

The user declined the proposed single current98348 control launch and selected
**"Keep all work offline"**. Continue with local files and static/offline checks.
Do not launch HotS, use Computer Use, make new network requests, or publish to
GitHub/OneDrive under this instruction. Do not repeat the same permission request.
The persistent full-upgrade objective is unchanged and remains incomplete.

The prepared `scripts/run_current_replay_control.py` and its policy tests have
not executed a game. A read-only preflight verified the immutable current
control, signed Switcher and installed98348 PE before the latest constraint.
The signature helper's PowerShell child clears inherited PSModulePath to avoid
loading a PowerShell7 module into Windows PowerShell5.1. The preflight is launch
readiness only, with no login or playback claim. Keep this preparation unused.

## Offline native event-ID binding — 2026-10-27

Enum138 now has selected reader/writer and dispatch-table bindings. Original
slot27C9FAC supplies138 to context14393EB80 at reader1352350 and writer1354850.
The116-entry table has90 active entries, exactly the enum tags; table bytes are
separate from5928decoded code bytes. Selected constructed tables for IDs23/25/27
lead to payload roots274/287/291 through their virtual read/write methods.
The three physical payload graphs match pinned upstream96477; native names,
runtime vptr identity, all callback aliases and archive-filename binding remain
unproved. See the dated native game-event ID/command payload report.

The actual payload-only model checked4558R8 and26899current-control ID27 command
payloads with equal values/bit spans and zero checked metadata violations. Other
payloads and frame envelopes still use upstream96477; this is not a whole native
stream decoder or gameplay proof. IDs23/25 were absent from those recordings.
Do not rewrite flags or fabricate a new replay from this result. No network,
game, Computer Use or remote publication occurred; the offline-only instruction
still applies and R8/full-upgrade state remains unchanged.

## Offline native game-member and frame route — 2026-10-27

Read `docs/NATIVE_GAME_MEMBER_FRAME_ROUTE_2026-10-27.md` and the three dated
native-game-member/frame receipts. The exact game filename's initialized string
object reaches member selection in134F770, constructor134B8F0 and state+1A0.
Caller1330CC0 supplies the same state to sequential reader13266B0 because
50C58+498=510F0. This is conditional static data flow, not live object identity.
The reader's four RuntimeFunction fragments are chain-qualified as one selected
414-byte/119-instruction union. Seven selected ranges total2481B/600instructions.

Frame roots50/890/138 have a complete12-record closure and match upstream96477
physical graphs. A separate local bit cursor checked248965actual envelopes,
4979308framebits and31457ID27payloads across R8/current control. Every value and
bit span agreed; replacing only observed frame fields in RAM preserved whole
member bytes. Zero checked bounds/membership violations; userid16 observed.
Delta tags2/3 lack actual-case coverage. Native bit-reader implementation is
still unproved; all other payloads still use upstream96477. The counted event
container135EB50/135F070 is a different route: do not add its count to a member.

No game, Computer Use, network, remote publication, replay or sync write. Keep
the prepared launcher unused and preserve the dirty drafts. Original/R8 remain
unchanged; full upgrade and playback remain false. Next offline boundary is
binding the other observed payload cases and native bit-reader behavior, not
guessing historical state, catalogs, ownership or missing player fields.

## Native observed game-stream value codec — 2026-10-27

Read docs/NATIVE_GAME_EVENTS_CODEC_2026-10-27.md and the five dated native-game
codec receipts. New native_game_events.py supports exactly22 observed payload
IDs through a pinned191-type closure, with no upstream fallback. All44 selected
vmethods/1892B/440instructions bind matching read/write roots; ten leaf ctors add
611B/150instructions. STRING +2/max*4 and sequence-count rules come from pinned
same-context evidence. Full90-payload support and runtime objects are unproved.

The complete R8/current game members compare248965events and4445854native nodes
with pinned upstream values/bit spans and reproduce everybyte from typed values.
All11supported kinds occur. A current-control synthetic RAM-only ID110 edit
changes onebit; independent upstream comparison preserves all other144708event
values/positions.16 focused tests pass. The current-control CI gate was extended
but has not run; no full local corpus or peer-review claim. Encoding canonicalizes
delta tags/padding and is not a generic source-preserving API.

Original41810 game member is NOT R8's member. Independent old-protocol comparison
first differs at zero-based event22/ID28 SelectionDelta, start4312bits, old end
4438/aligned4440 versus native-model4387/aligned4392. First22frames agree. A later
unbound-ID stop is misalignment, not an authentic old-ID binding result. Do not
claim that the unmodified original passed or infer historical semantic fidelity.

This supersedes the previous non-command-payload fallback limitation for these
two whole members only. Original/R8/control, sync data and unused launcher drafts
remain untouched. Keep all work offline: no game, Computer Use, network or remote
publication. Full upgrade/playback remain unproved; do not guess missing state.

## Original-to-R8 native game fidelity audit — 2026-10-27

Read docs/NATIVE_GAME_MIGRATION_FIDELITY_2026-10-27.md and the three dated
native-game-fidelity receipts. audit_native_game_fidelity.py reconstructs the
entire104257-event R8 game member from original41810 values plus explicit existing
recipe rules, using the native codec. Every payload difference is accounted for;
all event order/deltas/userids/IDs remain equal and whole R8 bytes match.
It audits existing assumptions; it does not authorize them as historical truth.

Counts:20build fields,4558absent vectors,3247flag changes,15346tag references/
15301changed tags,1mouse modifier default. The flag mapping is noninjective:
606old0x100100->0x80100 and16old0x80100 unchanged,622commands total. Do not call
this a unique flag inverse or use format agreement as semantic equivalence.
Preserve the source/per-event audit. Do not enable the unobserved0x40100 hypothesis
or claim a desync cause. Runtime flag meanings, absent vectors, zero modifiers,
and runtime instance allocation remain unproved. No conversion rule changed.

Eight new tests and16neighboring codec tests pass; actual whole-member
reconstruction and edited CI block parsing are local evidence. New CI gate
retains explicit collision assertions but has not run remotely. No full local
corpus/peer review claim. Original/R8/sync/drafts remain unchanged; no new replay,
game, Computer Use, network or remote publication. Full upgrade stays false.

## Current command flag transport and selected target gate — 2026-10-27

Read docs/NATIVE_COMMAND_TARGET_GATE_2026-10-27.md and the three dated native
command flag/gate receipts. Factory6D4250 constructs the ID27/header0x3001B object;
202ADB0 initially copies source+0C32-bit flags directly to recorded+30. Consumer
132B890 checks that header and calls validator202AFB0. Four qualified ranges total
2423B/673instructions; the factory's three RuntimeFunction fragments are chained.
Raw xrefs and the exploratory slot38 RET-imm overrun are excluded from claims.

New native_command_target_gate.py models only post-callback202B475..202B4E7,
114B/36instructions.128 finite opcode-interpretation cases agree with the model.
This is a conditional continuation gate, not whole-command validity or runtime
execution. Bits18/23, callback class0..3 and uninterpreted contextbit2 matter.
For None/contextbit2clear, existing0x80100 passes class0 only; unapplied0x40100
passes classes1/2/3 only. Current/historical callback meanings remain unproved.

All16 old exception cases are explicit/None, cmdindex0, no otherUnit/unitGroup
override: link126x9 and351x7, firstloop1682. Current control has531explicit/None
0x80100 commands and no0x40100; do not generalize absence or assign ability names.
The64-loop window is not a measured divergent tick. No flag mapping changed.
Keep all work offline and preserve original/R8/control/sync and unused drafts;
no game, Computer Use, network, remote publication or new replay. Full upgrade,
catalog/callback identity and deterministic playback remain unproved.

## Offline current ability callback route — 2026-10-27

Read docs/NATIVE_ABILITY_CALLBACK_ROUTE_2026-10-27.md and the three dated
native-ability-callback/source-context/validation receipts. The validator's
callback now follows runtime type getter5E48D0 (registry3388B18, resolved+24),
type descriptorA51A70 (0..18, bitmap36350C0, base3604290/stride2A48), and
slot getterA27340 (index*A8, nonzero byte+8, pointer+80). Stride is not extent.
Separate mask getterA27180 falls back to TRUE for inactive/out-of-range slots;
pointer getterA27340 instead returns null. Both real fallback blocks are included.

Selected builderB91D80 for numeric type5 assigns callback classes3/2/2 to
indices0/1/2; type6 builderC03A40 assignsC02780 to index0. These are conditional
static assignments, not live table or complete helper-alias proof. C02780's
nonnull data field+190 maps0/1/2 to classes1/2/3, others/null to0. C09D00 delegates
to another callback. No current type or data value is authenticated for old
links126/351. The named ECmdFlags registration binds only10 rows (Unknown and
values0..8); it does not identify replay flag bit18/19 or the whole26-bit word.

Actual original source has61 commands for links126/351, all cmdindex0:21/24
Unit+0x100 and9/7 None+0x80100 in selected-unit contextsHeroFaerieDragon/Tyrande.
Selection is not executed-caster or ability-name proof. With shared callback
class/contextbit2, no class0..3 passes both shapes when contextbit2clear; class2
does when set. Those assumptions are unmeasured, so this is not rejection,
self-cast, desync-cause or flag-rewrite authorization. Conversion stays unchanged.

21 selected code ranges12067B/2180instructions, original fragment-chain checks,
260 bounded raw-opcode cases,4 constant callback patterns and6 existing gate
tests pass locally. No production code change, full corpus, hosted CI or peer
review. Original/R8/control/sync and unused launcher drafts remain unchanged.
Keep all work offline: no game, Computer Use, network or remote publication.
Full upgrade/playback remain false; continue from authentic catalog/data values
and context dependencies, never guessed flags or metadata retagging.

## Offline command context producer — 2026-10-27

Read docs/NATIVE_COMMAND_CONTEXT_PRODUCER_2026-10-27.md and its two dated
native-command-context-producer observations. GetterA271F0 selects slot+40,
separate from class slot+80. Validator202B2DD zeros EDI,202B390 seeds context+8;
local direct-CFG domination and no intervening explicit RDI-family write check.
Default slot+40 is null. Exactly4 E8/E9 transfers to setterA27710 exist in the
pinned transformed-text scan: type9/index0->BA59D0,11/0->BC2420,15/0->C09C10,
16/20..29->C0C650. This is not all indirect/alias/later-write coverage or live data.

BA59D0 clears bit2 on resolved paths, otherwise preserves it; BC2420 andC0C650
preserve it in explicit writes. C09C10 delegates the same context. Helper201A490
reads its firstQWORD and loses the original context address before calls, with
disjoint output/other args required. Zero bit2 is invariant only for finite
returning delegation inside this selected/null family, valid disjoint objects,
normal ABI and no other alias writes. Never assert a universal runtime zero.

This narrows the conditional contextbit2=true gate escape for the prior61 source
commands, without authenticating their type/callback/data or stable class. No
class0..3 passes Unit/0x100 and None/0x80100 with shared class and zero bit2;
this is not rejection/desync/self-cast proof or flag-rewrite authorization.

15selected ranges3705B/932instructions, a separately rechecked1467B/393-instruction
validator, original fragment chains and1820 finite raw-opcode update cases pass.
No production-code change or unit-test rerun; source context report reused.
Original/R8/control pins and unused drafts remain unchanged. Keep all work
offline: no game, Computer Use, network or remote publication. Full upgrade and
playback stay unproved; continue toward authentic ability/type/data values.

## Offline native ability class names — 2026-10-27

Read docs/NATIVE_ABILITY_CLASS_NAMES_2026-10-27.md and its two dated native
ability-class-names receipts. Registered EClassIdCAbil has20 original24-byte
rows (Unknown plus0..18), bound through5FA79A/1600E80/16001D0. It is a type enum,
not replay link IDs or target classes. Direct constructor/name bridges checked
only for6/9: type6 factoryA51400->table26AEF18->slot68/A511D0->CAbilAugment;
type9 A51540->26AF6A0->slot68/A51200->CAbilEffectTarget. The initializer pairs
factory slot+1528 and descriptor+1530 at registry3602D60/index*2A48; getterA51A70
uses the latter. Normal initialization/copy/construction/no-alias conditions
remain; this is not a live instance or all19 constructor-name bindings.

The prior +190 query is Augment's C02780 route, not generic EffectTarget data.
EffectTarget's selected cmd0 callbackBA6130 callsA8B390 with record+140 and
normalized byte+0A (NOT command-index byte+08; semantic name unbound). A8B390
uses201F770/201F540 then B2AD50: runtime table36DE920, stride72, offset0, no
bounds check in that selected leaf. It calls the resulting pointer or returns
FFFFFFFF on checked failures. BA61C2..DE maps0/1/2->target classes1/2/3, others0.
Selector namespace, reference field name and actual runtime values stay unbound.

20 selected ranges10917B/2036instructions, original table/name slot bytes and260
finite raw-opcode mapper cases pass. Cached publisher41810 projections remain
separate from authentic numeric link/catalog/state/rule bindings. Source126/351
are not named or assigned current types; flags/conversion stay unchanged.
No production-code or unit-test change/rerun, broad corpus, hosted CI or peer
review. Original/R8/control/sync/drafts preserved. Keep all work offline: no
game, Computer Use, network or remote publication; full upgrade/playback false.

## Offline recorded talent choices — 2026-10-27

Read docs/TALENT_CHOICE_OBSERVATIONS_2026-10-27.md and the two dated talent-choice
observation/validation receipts. New talent_choice_audit.py joins already-decoded
selections with unique same-player TalentChosen purchases exactly+1loop, using
explicit prior user/player setup and a prior stable Hero identifier. Ambiguous
keys remain unpaired; no nearest-time, user+1, tier or array-order inference.
It returns aggregate identifiers only and never writes a replay or sync data.

All70 source,70R8 and70current-control selections pair uniquely. R8's70 actual
index values/associations equal the source and its tracker bytes are unchanged.
This preserved historical tracker is NOT current-client execution. Source41810
Dragon Shire and the pinned98348 Lost Cavern control share HeroKaelthas. Index15
is source KaelthasLivingBombSunKingsFury versus current KaelthasLivingBombIgnite;
index20 is GenericArcanePower versus KaelthasMasteryFlamethrower. Three other
shared indices have equal names. Map/mod contexts differ: do not isolate build
effects, assert removed talents, mechanical equivalence, safe replacement
indices or a desync cause from these observations. No talent mapping changed.

Twelve focused tests and210actual pairs pass; source/R8/current file pins and
draft hashes are preserved. Whole game counts104257/104257/144708; source game
uses pinned41810, R8/current use native observed22, tracker uses official
41810/96477. No broad corpus, hosted CI, peer review or client execution. Keep
all work offline: no game, Computer Use, network or remote publication. Full
upgrade/playback stay false. Continue toward authentic target-context talent
definitions and historical/current rule equivalence without guessed indices.

## Offline literal current Kaelthas talent definitions — 2026-10-27

Read docs/CURRENT_KAELTHAS_TALENTS_2026-10-27.md and its two dated current-kaelthas
talent definition/validation receipts. Cached276044B Kaelthas XML SHA39cf6954...
matches the frozen98348 extraction inventory. Its literal CHero tree has21
entries. SunKingsFury is present at Tier3/Column2/document position7; original
recorded index15 selected it twice. GravityCrush/index7 and GenericArcanePower/
index20 are absent from this tree only; do not assert global removal or rename.
All7prior current-control Kaelthas observations match zero-based XML document
positions, which are NOT generally authenticated native indices.

Fresh original decode reproduces all70 earlier pairs; the two Kaelthas players
made14 purchases,10 distinct index/name pairs. Two names/purchases are missing
from this tree, two purchases differ from document position,10 match. One
source player bought both BurnedFlesh and SunKingsFury, whose literal current
Tier is3. A by-name lookup therefore has a conditional same-player tier
collision; this is not current rejection, universal tier exclusivity, old tier
identity or desync proof. The pinned global CHero default separately declares
Tier3/Level7 and Tier6/Level16; effective inheritance/load order remains unbound.

Independent Expat/ElementTree agree on21tree entries and7default tiers. Prior
current7observations are reused, not freshly decoded. Replay/draft pins remain
exact. No production/conversion change, new unit tests, broad corpus, hosted
CI, peer review or native execution. REA readiness had no open target; no IDA
or Ghidra analysis was performed in this definition audit. Keep all work
offline: no game, Computer Use, network or remote publication. Full upgrade/
playback stay false. Do not apply a guessed15->7 or missing-name replacement;
authenticate native index/selection rules and effective/historical definitions.

## Offline native talent index transport and array query — 2026-10-27

Read docs/NATIVE_TALENT_INDEX_ROUTE_2026-10-27.md and its two dated native-talent
index-route receipts. Header3006E/table26A77D0 bind event110; selected read/write
methods94B300/94B260 use object+30/root564->565->3 singleuint32. Factory94B560
stores incomingECX directly at+30 on its nonnull allocation path, then forwards
through8418D0 to13340E0. The actual dispatcher/consumer is unproved.

Sender8C0EF0's seven chained RuntimeFunction fragments form485B. The same DWORD
at secondarg+1C goes toB0F1F0 and the factory. Query failure at8C0F6B branches to
8C0FC6 and can still reach construction. Do NOT treat query failure as event
rejection or the query as universal playback validation. B0F1F0 obtains an
unbound object via9D5080 and passes object+50/index/output toB0F160. That query
masks a resolver result with~1F, checks unsignedindex<count at+500, then copies
an entry atpointer+510 plusindex*64. No live count/base/entry is captured.

Entry+8 is copied tooutput+8 and used inB0F720's secondary lookup: first low-byte
selector<16, second unsignedselector<32, table3677A30, DWORD stride4. Neither
selector's semantic namespace nor a talent-tier interpretation is bound.
TalentTreeArray literal registration at51115E suppliesR9D470 to1601160; the
parameter meaning/object adjustment and link toquery offsets500/510 remain
unproved. Owner descriptor2BC5320 is opaque, not a name string. Do not infer
CHero identity or XML order. The TalentChosen label reference is in a stat
writer, not a proven executed-purchase producer.

Ten qualified ranges1242B/338instructions plus2selected metadata windows511B/
92instructions; exact bytes, original method slots/chains and branch targets
checked locally with GNU objdump/WSL. Overlong leaf/jump-table sweeps excluded.
No REA native Evidence, target execution, new unit tests, broad corpus, hosted
CI or peer review. Replay/draft pins preserved; no stream decode or production/
conversion change. Keep all work offline: no game, Computer Use, network or
remote publication; full upgrade/playback false. Next bind metadata/query array
and the actual event consumer before any guessed talent-index replacement.

## Offline named native talent field/layout bridge — 2026-10-27

Read docs/NATIVE_TALENT_FIELD_BRIDGE_2026-10-27.md and its two dated native-talent
field-bridge receipts. Descriptor2BC5360 names CHero; call50F046 stores its
metadata result atRBP+978, restored toRBX510579 for TalentTreeArray call51115E.
The earlier2BC5320 names SHeroModification and is not that field owner. Name/
initializer SHeroTalentTree/509AF0 pair yields size64 and metadata restored from
RBP-50. R9D470 is forwarded through1601160/16003F0 tofield-descriptor+80.

Descriptor2BC5220 names SHeroTalentTree. Its fields Talent/Tier/Column register
at0/8/C; selected copy callback505910 calls50B800, the same query copy helper.
Thus output+8/B0F720's second selector has a Tier binding in this named-entry
context. First-selector player/user namespace and purchase exclusivity remain
unproved. CHero init505CF0 calls614460 onobject+90; that leaf zeroes body count
470 and pointer480. CHero copy505DB0 adjusts bothsource/destination by90. Hence
object count500/base510/stride64 match the prior query under normal CHero-record
conditions. No live resolver result/type/count/entry or effective catalog seen.

Complete4897-instruction registration directCFG has no indirect jumps/external
direct noncall exits;6 definition/use dominations and no conflicting explicit
RBX/R12 writes checked.12selected ranges31469B/5601instructions include original
descriptor/name/callbacks, class/resolver fragment unions, registrar/constructor
and initialization leaves. Conditions: normally returning helpers, x64 ABI,
valid disjoint storage, no exception/reentry/later replacement/alias mutation.
Ordinary GNU objdump/WSL only; no REA native Evidence or target execution.

This supersedes the prior static field-name/layout gap conditionally; loaded
record identity, effective entries/XML ordering, map/mod overrides, historical
rules and purchase acceptance remain unproved. State-table references retained
privately are unqualified candidates, not writes/execution. Replay/draft pins
exact; no new stream decode, unit tests, broad corpus, hosted CI or peer review.
No production/conversion/replay/sync changes. Keep all work offline: no game,
Computer Use, network or remote publication; full upgrade/playback false.
Next bind state writes and the actual event110 consumer without guessed indices.


## Offline native talent state write and conditional consumer - 2026-10-27

Read docs/NATIVE_TALENT_STATE_WRITE_2026-10-27.md and its two dated native-talent
state-write receipts. B10720 admits through B0E870, copies the named entry's
Tier and writes the incoming uint32 at3677A30+(selector*32+Tier)*4 atB10934.
The selected B0E6E0 gate requires row[Tier]==FFFFFFFF plus other bitmap,
prior-selection and threshold checks. B0EC80 clears an occupied cell and
reassesses later choices. First-selector namespace, effective values and
simulation purchase/effects remain unbound; this is a selected static gate,
not a universal gameplay rule. Do not guess a15-to7 talent replacement.

Original observer2F73050/table26EC238 slot8 points toB58E70. Its selected
transformed switch suffix maps header3006E -> index96 -> byte26 -> B5F9A9,
which callsB612D0; that callback loads event+30 and conditionally callsB10720.
The99B/116B transformed tables differ from original PE at98/116bytes. Their
two original/transformed hashes and difference counts are retained. Whole
obfuscated dispatcher entry-to-suffix CFG and factory/dispatcher-to-callback
binding remain unproved. Do not promote the full27731B linear sweep (private
search aid with obfuscation/embedded data) to qualified instruction evidence.

Eight complete original RuntimeFunction/CHAININFO unions total3145B/807instr;
four required-edge reachability checks pass. Two conditional suffix windows
73B/15instr and39selected instruction checks are separate. Conditions include
normal helpers/x64 ABI, valid storage/cells, stable records/row, no exceptions,
reentry/concurrent writes/alias mutation, named CHero layout, image base and
pinned transformed table values. Wrapper20B9A50 calls the same writer and
references TalentTreeSetSelectedHeroTalentTree/inTalentTreeIndex error names.

The source BurnedFlesh/SunKingsFury collision in literal current Tier3 therefore
has a selected empty-cell gate consequence only if those entries, row and path
are effective and stable. No desync cause, live data, safe mapping or rule
equivalence established. Replay/draft pins exact; no fresh stream decode,
production/conversion/replay/sync change, native execution, unit tests, broad
corpus, hosted CI or peer review. Keep all work offline: no game, Computer Use,
network or publication; full upgrade/playback false. Next authenticate the
dispatcher prefix and effective selector/catalog/historical rule bindings.


## Offline observer user route and selected-page provenance - 2026-10-27

Read docs/NATIVE_OBSERVER_USER_ROUTE_2026-10-27.md and its two dated native-
observer-user-route receipts. Sequential13266B0 reads root890 into stack50,
then13267B9 stores its byte to event+29 after successful reads/nonnull object.
CallbackB612D0 reads that byte and callsA28B60, which computes encoded-base+
(uint8(input)+B0)*1A4. Filter202ED90 takes the first matching-tag DWORD item
with callback capacity1. A valid resolved object's byte44 is the first writer
selector; fallback uses event+2A. Native constructor sets29/2A initially16.
The row/object namespace, effective base/contents, tags and bitmask remain
unbound. Do not infer user==selector or user+1; intermediate dispatcher field
preservation and end-to-end event delivery remain unproved.

Fresh original-PE data transform reproduced2728pages/11173888B fromBA000 through
B62000, exactly equal to the pinned saved transformed prefix. Three selected
pages B58000/B5F000/B61000 also match a second local page-transform/FNV routine.
This authenticates those derived bytes under the explicit analyst model;
native bootstrap initial state/parameter selection/execution is NOT proved.
Original switch-table ciphertext still differs from transformed plaintext.

Five qualified ranges845B/231instr,34internal direct-branch targets and32
specific instruction/call checks pass. Complete prior frame/callback unions,
complete202ED90 record and only-RET straight-line leaves are separate from
the opaque dispatcher. Normal x64 ABI, valid disjoint storage, preserved
event29 and stable handles/objects remain conditions. REA readiness has no
open target/pending cleanup; configured IDA is not live-probed, no new native
engine session/database opened. Ordinary Python/GNU objdump/WSL evidence only.

Replay/draft hashes unchanged; no fresh stream decode, unit tests, broad
corpus, hosted CI, peer review, production/conversion/replay/sync change or
native execution. Keep all work offline: no game, Computer Use, network or
publication; full upgrade/playback false. Next bind dispatcher preservation,
the actual row/object/selector, effective catalog and historical41810 rules.


## Offline talent selector admission and pool initialization - 2026-10-27

Read docs/NATIVE_TALENT_SELECTOR_ADMISSION_2026-10-27.md and its two dated
native-talent-selector-admission receipts. Provider9D5080 compares CL with16
before reading its globals. Low-byte16..255 returns RAX0. B10720 requires the
nonnull edge after callB10755 to reach writeB10934, so the selected write
requires first-selector low-byte0..15. The256-case opcode guard model is
static Python data reasoning, NOT native execution or playback validation.

Allocator990AF0 and callbackB612D0 share pool slots34F02C8, count34F02C4 and
keys32C38B4/32C55D0, block16/stride2F0, handle slot-index shift22 and identity
DWORD+10. Allocator's next-slot limit is1023 and block allocation2F00 bytes.
Its selected constructor990020 installs table26A87F0 and initializes byte44=16.
That default cannot reach the selected write while preserved as its selector.
The native class name, field meaning and later effective assignment remain
unbound. Original table preceding QWORD700000005 supplies no conventional
MSVC COL binding; do not invent a Player/CUnit name from adjacent debug text.

Four complete original RuntimeFunction/CHAININFO unions2183B/504instr plus
provider code426B/106instr are qualified. Provider alignment2B and RVA table
64B/16targets are separate from instructions; every table target is a code
boundary and all106 expanded-switch nodes are reachable in the normal graph.
31specific byte/call/reference checks pass. Global mode>15 default return
initialization/validity is unproved; do not invent a safe fallback. This does
not affect the earlier input>=16 rejection, which precedes the mode read.

All selected bytes use pinned transformed text; original PE metadata supplies
extents. Normal helpers/x64 ABI, valid disjoint storage, stable identities and
no exception/reentry/concurrent/alias mutation remain conditions. The private
9D4E90 setter hypothesis was discarded after accessor-shaped decoding; raw
reference candidates are not accepted writes or semantic names.

Replay/draft pins unchanged; no actual selector/catalog capture, fresh stream
decode, production/conversion/replay/sync change, native execution, REA native
analysis, new unit tests, broad corpus, hosted CI or peer review. Keep all work
offline: no game, Computer Use, network or publication; full upgrade/playback
false. Next bind effective selector assignment/object namespace and target-
context/historical41810 talent definitions before any safe index migration.


## Offline unit-owner assignment and talent selector - 2026-10-27

Read docs/NATIVE_TALENT_OWNER_ASSIGNMENT_2026-10-27.md and its two dated
native-talent-owner-assignment receipts. Wrappers2055CE0/2055E00 bear original
error-context names UnitSetOwner/UnitSetOwnerPreserveUpkeep, resolve through
64BAD0, check unsigned second argument0..15 and tail9BC080 with that byte.
Resolver64BAD0 uses the callback's same pool slots/keys/stride/handle identity.
9BC530 writes the saved incoming owner byte to resolved unit+44; B612D0 reads
that same field for the first talent-writer selector. This is a selected
native owner-argument binding, not a replay user/tracker player namespace
mapping, live owner capture, native class RTTI or audited API export table.

Creation996D90 forwards its successful990AF0 result and creation-input pointer
to9BAEF0;9BB05A writes BYTE[creation_input+10]&1F to object+44 after earlier
helpers. Actual creation fields/replay sources and their values remain unbound.
The initializer code3784B is separate from two64B/16entry tables through the
original record end9BBE38; all32 targets are code boundaries. No embedded table
is treated as instructions. Four-digit counts/addresses follow the report.

Owner argument is saved at entryRSP+10, equal to RBP+248 under RBP=entryRSP-238.
Three pre-store pointer escapes target201A590. Its complete12B/5instr leaf
only reads the input byte and sets a disjoint target's low5 bits; source is
preserved under the storage conditions. A post-store escape to201CE30 remains
unproved readonly, but its normal CFG cannot revisit the selected store. Do
not assert final persistent state or absence of later/reentrant alias writes.

Eight ranges8089B/1933instr,128B separate switch data,54specific byte/call/ref
checks,8 definition/use/no-conflicting-register-write checks and4 required
wrapper edges pass. Original fragment unions, split code/data and both bounded
no-call leaves are explicit. Normal x64 ABI/helpers, valid disjoint storage,
stable handles/keys and no exception/reentry/concurrent/alias mutation apply.

This conditionally supersedes the unnamed field44 gap for these owner setter
and callback paths. Do not infer userid==owner, user+1, owner+1 or tracker-ID
equivalence. Keep original/R8/current and sync data unchanged. No fresh stream
decode, production/conversion change, unit tests, broad corpus, hosted CI, peer
review, native target execution or REA native analysis. Keep all work offline:
no game, Computer Use, network or publication; full upgrade/playback false.
Next bind owner to recorded player/setup/ownership data through an authentic
producer, then effective/historical41810 talent rules before a safe migration.


## Offline native owner to tracker record construction - 2026-10-27

Read docs/NATIVE_OWNER_TRACKER_RECORD_2026-10-27.md and its two dated
native-owner-tracker-record receipts. Direct call9BC21E binds the selected
owner mutation to factory1342E30. Its entryDL is saved inEBP and copied unchanged
at1342EDD to event object+38. The same saved owner is used by the selected
unit+44 store9BC530 and previously qualified talent selector. Event object+39
copies factoryR8B; caller selects saved unit+5E or owner according toR15B.
Do not assign that second byte an unproved native field name.

Factory header50003/table27BD320 match ID3 in reader135E4E0. Selected writer
132AC50 ->135E870 serializes the header low word using root898 then calls slot8
133FDF0, which passes root957 and object+30 through1A75E30 to1A75240. Reader
slot30=133F310 uses that same root/base with1A772C0. Original filename/atom
27BDEA0/393E240 and archive-open134F770 bind tracker substateCF0 to member
replay.tracker.events. The factory's virtual publisher+180 is not yet bound to
this persistent writer; constructor also requires unit41 bit0clear and virtual
slot298 nonzero. No actual event emission or owner snapshot is demonstrated.

Root957 declares ordered tags0..3/u32,u32,u4,u4, matching the pinned official
event3 SUnitOwnerChangeEvent shape. The generic field walker has not been
audited for per-field native offsets. Therefore owner ->event byte38 is bound
under conditions, but owner==named wire control/upkeep/player/user ID remains
UNPROVED. Do not infer user+1/owner+1, fabricate owner default16 semantics, or
perform a talent remap. Native handle split and pair of payload bytes are code
bindings; named wire fields remain a separate boundary.

13ranges7268B/1706instr,67byte/call/ref checks,4register-flow and2required-guard
checks pass. The 60B/15entry ID table is separate from code, all targets are
boundaries, and its TRANSFORMED bytes differ from original PE span. Original
metadata supplies extents; pinned derived code/tables are not a runtime capture.
Replay/draft pins and source/schema pins pass. Normal ABI/helpers, disjoint
storage, stable identity and no exception/reentry/alias/concurrent mutation are
conditions. No fresh replay decode, code/conversion/sync change, unit tests,
native execution, REA native-provider analysis, hosted CI or peer review.
Keep all work offline: no game, Computer Use, network or publication; full
upgrade/playback false. Next bind root957 runtime field layout and publication
sink, then actual ownership/setup and effective/historical41810 talent rules.


## Offline root957 named ownership fields - 2026-10-27

Read docs/NATIVE_TRACKER_OWNER_FIELDS_2026-10-27.md and its two dated
native-tracker-owner-fields receipts. Selected initializer1D08A0/constructor
1A77DB0 bind registry393EB80 to original program27C6960 and accessor27BECB0.
Descriptor1A6D070 uses table[tid+1] as relative QWORD index. Root957 index3433
selects27C57F8 with QWORDS12,0,4,8,9; getter1A6D670 takes the four offsets after
the first QWORD. Its first QWORD semantic role is not newly assigned.

Generic writer1A75240 STRUCT fields use payload offsets0/4/8/9 and tags0..3;
USER958..961 recurse transparently to scalar3/3/158/158. Original width entries
are4/1 bytes. With adapter event+30, event fields30/34/38/39 map respectively
to official event3 unitTagIndex/unitTagRecycle/controlPlayerId/upkeepPlayerId.
This conditionally closes the prior per-field memory/wire-name gap. Selected
factory1342E30 incomingDL is therefore the selected m_controlPlayerId value;
factoryR8B gives m_upkeepPlayerId. Normal initialization/stable registry/code,
storage/ABI/helper/identity and no alias/reentry/concurrent mutation are required.

Scalar leaf1A79110 reads the unsigned little-endian value unchanged. INT path
bounds-checks before1A75EF0 encoding, without adding a minimum/player offset.
Versioned positive encoding uses first low6 bits shifted1 and subsequent7-bit
groups. It does not numerically renumber the player. A data-only projection of
all256 ownership pairs0..15 with three uint32 pairs passed768 unchanged pinned
official VersionedDecoder class decodes with exact byte consumption. Two bounded
Python3 six byte primitives were supplied; native code was NOT executed.

18ranges4662B/1321instr,56byte/call/ref checks,6register-flow checks and3required
kind edges pass. Separate64B/16entry kind table uses pinned TRANSFORMED bytes,
differs from original PE span, and all targets are boundaries. Twelve original
fragment unions and six branch-closed no-call leaves are qualified. Original
PE/program/accessor, transformed text and replay/draft pins pass.

Actual owner/event emission, startup reach, constructor publication to file,
initial Born/Init producers/all callers, wire-user equivalence and later callback
value stability remain unproved. Do not infer user+1 or historical rules, rename
default16 semantics, or perform a guessed talent mapping. No fresh replay decode,
production/conversion/sync change, unit tests, native execution, REA provider,
hosted CI or peer review. Keep all work offline: no game, Computer Use, network
or publication; full upgrade/playback false. Next authenticate concrete publisher
and initial ownership/setup, then effective and historical41810 talent rules.


## Offline owner-event publisher to tracker writer - 2026-10-27

Read docs/NATIVE_TRACKER_PUBLISHER_2026-10-27.md and its two dated
native-tracker-publisher receipts. Initial global2F825F8 XOR50C23112 is null.
Qualified13297D0 status20020000 branch constructs object387C290 via13237D0,
XOR-encodes it and stores at1329907. Constructor installs primary27BC518,
clears enabled byte1BC and constructs container1D940. Startup/active mode and
later replacements remain unobserved; raw RIP candidates are not exhaustive
alias/write proof. Three original cells bind slot180->132FE70,288->133C5B0,
298->132B7F0. The latter8B leaf reads manager byte1BC.

Factory1342E30 uses that decoded manager and publishes through slot180.
Handler132FE70 preserves the event pointer, rechecks enabled state, then calls
132AC50 at132FEAB with manager+1E630 only if the previous atomic32 counter at
manager+1C0 was0. Its enabled normal path decrements the counter afterward.
Selected record-start133C5B0 opens container manager+1D940 via134E890 and sets
enabled1 at133C614 on zero result. Writer-mode134F04B calls134E510 for CF0;
1D940+CF0=1E630, the SAME tracker state used by the publisher. Tracker atom is
393E240/replay.tracker.events; downstream event/root957 writer binding retained.

This closes the conditional constructor-to-native-tracker-writer INVOCATION
gap, not successful serialization or on-disk persistence. Selected member
opener can store null writer at134E614 after allocation failure yet return the
earlier zero stream-open status at134E66F. Thus status0/enabled1 are insufficient
to prove usable state+1A8. Require successful allocation/non-null stable writer.
No allocation failure was observed or linked to past client exits. Ignored
encoder returns also prevent inferring successful serialization from invocation.

16ranges9439B/1972instr,54byte/call/ref checks,9register-flow and4required-guard
checks pass. Fourteen full original fragment unions/two no-call leaves and
three original vptr cells are qualified. Whole PE/transformed/replay/draft pins
pass; prior768-case synthetic codec receipt is retained, not rerun. No fresh
replay decode, native execution/REA provider, unit tests, broad corpus, CI or
peer review. Derived code is not an unchanged executable or live capture.

Selected initialization, retained global/vptr, same manager receiver, valid
disjoint storage, stable schema/identity, normal ABI/helpers and no exception/
reentry/concurrent/alias/later replacement are conditions. Writer allocation,
capacity/refill and success remain necessary. Actual events, active mode and
archive persistence unobserved. No user+1 or guessed talent mapping. Keep all
work offline: no game, Computer Use, network or publication; original/R8/current
and sync unchanged; full upgrade/playback false. Next initial Born/Init ownership,
actual context and effective/historical41810 talent rules; flush proof separate.


## Offline initial owner, Born/Init and recorded identities - 2026-10-27

Read docs/NATIVE_UNIT_INITIAL_OWNER_2026-10-27.md and its two dated
native-unit-initial-owner receipts. Initializer9BAEF0 stores creation-input
byte+10 &1F to unit+44 at9BB05A, then reloads that byte/mask and stores unit+5E
at9BB062. Under disjoint/stable input these selected early values are equal;
domain is0..31, not silently0..15. They are reads after earlier helpers, and
preservation until later publication is UNPROVED.

Within earlier gates, unit38 bit08 chooses Init call9BB9B7->1342A50 or Born
call9BB9C6->1342270 (afterA16B80). Both use the same initialized unit pointer.
Both producers later read unit44/5E into event250/251 without numeric changes.
RSP=entryRSP-2A8,RBP=entryRSP-1A8,record=RSP+20 bind RBP170/171 to these bytes.
Distinct roots933/970, original slots27C9F3C/54 and original offset tables
27C5630/27C58E0 bind tags3/4 to m_controlPlayerId/m_upkeepPlayerId, both scalar158
uint4, via payload offsets220/221. No whole type-name/payload codec claim.

Selected unit-key fields30/34 map to native unit+10 high10/low22 bits. Born's
reads are separated by helpers and require stable handle; Init uses one later
read. Own constructor/header IDs1/6 and adapters133FA70/133FD10 remain distinct.
Same decoded manager2F825F8/XOR50C23112/slot180 publisher is reused, with all
enabled/counter/nonnull-writer/output/persistence caveats. No native execution.

Fresh tracker decode: source/R8 each6614 events,2802Born,0Init,279OwnerChange;
current6181,2498Born,0Init,136OwnerChange. All observed owners0..15, all Born
control/upkeep pairs equal, all changes have prior birth keys, no duplicate
initial keys. R8 tracker equals original EXACTLY: only2 independent contents.
R8 uses41810 content grammar, not proof of98285/current playback. Init has ZERO
observed fixture coverage. Do not infer runtime liveness/pool/callback identity.

Initial owner IDs without player setup are source/R8 [0,11,12,15],current
[0,11,12]. Preserve them; do not infer user+1, assign meanings, drop15 or treat
its absence in this one current control as unsupported. Named setup identities
remain explicit mappings, not a universal owner namespace rule.

7ranges6079B/1431instr,55byte/call/ref checks,12register-flow and6required-edge
checks pass. Four64B/16entry TRANSFORMED RVA tables and3alignment bytes are
separate from code; all64 targets bound. Three original fragment intervals/
four no-call leaves qualified. PE/transformed/schema/accessor/replay/draft pins
pass. Fresh offline tracker decode is not native execution, full corpus, unit
tests, REA provider, hosted CI or peer review. Initial helper effects, actual
client objects/talent values and effective/historical41810 rules remain open.
Keep all work offline: no game, Computer Use, network or publication; original/
R8/current/sync unchanged; full upgrade/playback false. Next actual player/unit/
talent producer/consumer context, without guessed indices or player remapping.


## Offline selection producer and talent-unit context - 2026-10-27

Read docs/NATIVE_SELECTION_TALENT_CONTEXT_2026-10-27.md and its two dated
native-selection-talent-context receipts. Official28=SelectionDelta,29=ControlGroup
Update,30=SelectionSyncCheck. Selected header3001C/index14/selector7/caseB5F7B0
callsB61970 atB5F7BB. Existing originalvptr26643A0/methods/root-slot27BEB7C bind
payload303. Original layout303 is bank0/delta8; inner delta offsets0,4,30,F8.
Negative STRUCTtags are not equated with upstream tags; declaration-order and
matching shapes/consumer offsets support selected field names, not whole reader.

B61970 forwards user=event29,bank=event30,delta=event+38 toA286A0 after its gate.
Updater uses same encoded base asA28B60: bank<10 ->row(192+10*user+bank)*1A4;
bank>=10 ->row(176+user)*1A4, exactly talent lookup row. Valid user0..15/bank0..15
address model96active/160stored cases passes; not target execution. A283F0/A27B50
snapshot-hook effects not fully closed. Same-base/user/field stability required.

202DBC0 applies removals/additions then at202DD3A writes row2 from delta byte0
(subgroupIndex) if below row1, else0. B612D0 reads this DYNAMIC byte2 into query
tagR9 and capacity1 intoR8, then202ED90 returns first matching DWORD handle from
row4+4*i with tags row84+i. Offset2 is NOT literal tag2. API error-context names
UnitIsSelected/UnitGroupSelected use same A28B60 valid-user row branch; export
registration/alternate player-row semantics are not universally asserted.

Exact actor still needs effective link resolution:5E1B70 reads context3388B18,
table+2A0,count90,entriesA0,uint16 index, output reference0 on null slot/out-of-range.
202D910 uses201A490/ref gate,capacity32,definition word40 and993DA0 predicate;
descriptor may include unit index>>22 or3FF. Effective inputs NOT captured,
whole subgroup/order/mask-memory model not reconstructed. No guessed XML flag,
native RTTI class, fixed hero list, hero-name/nearest-time association or owner.

Fresh tracker ranges source index0..254/recycle1..235,current0..97/1..193 fit
selected native domains; each has10PlayerSpawned events with only PlayerID int
key and no explicit unit/tag/handle key. Fresh game frames source/R8 each104257,
current144708; selection deltas158/158/37 ALL bank10; subgroupIndex1 occurs5/5/0,
others0; talent events70each. ControlGroupUpdate and SelectionSyncCheck both0
in all files. Added unitrefs92/92/24,11distinct links each. No actor reconstruction
or source/current simulation equivalence follows. R8 tracker duplicate retained.

13ranges3326B/821instr,54byte/call/ref,8register-flow and3required-edge checks pass.
Eleven full original fragment unions/two leaves; separate23B conditional arm,
99/116B TRANSFORMED tables not full opaque-dispatch proof. PE/transformed/schema/
accessor/replay/draft pins pass. No production/conversion/sync change, unit tests,
full corpus, hosted CI, peer review, REA provider/native execution. All work stays
offline: no game, Computer Use, network or publication; full upgrade/playback false.
Next exact effective link/definition/predicate inputs or existing captures before
unit/owner attribution; historical41810 rules and native playback remain required.


## Offline selection definition inputs - 2026-10-27

Read docs/NATIVE_SELECTION_DEFINITION_INPUTS_2026-10-27.md and its dated
native-selection-definition-inputs evidence/validation receipts. First lookup
5E1B70 uses context3388B18/table+2A0/count90/entriesA0. Second201A490 uses
WORD[first definition+40] orFFFF, SAME table but DIFFERENT count38/entries48.
Slot low-bit branch calls1608180(slot-1,0), then rereads array/slot. Body not
audited. Non-null object required; selected R9B0 rejects object byte0 bit0.
201A5A0 writes(ptr&~1F)|(flags&1F); selected callers use flags16. Failure output
16 masks to null. Null first definition selectsFFFF, not universal rejection.

993DA0 forwards same definition reference, resolves with allow0/flags16, then
writes(BYTE[object+DD]>>5)&1 and returns output-slot pointer. No local null
guard before read. Earlier202D910 resolution nonzero gate only suffices under
stable definition/table/object and coherent normal helpers/ABI. Predicate1
selects handle>>22 descriptor, else3FF; definition40 is another descriptor key.
Do not name a CUnit/XML flag/class or infer effective data from hero name.

5ranges1149B/289instr;3new functions411B/111instr plus2previous ranges.
70selected checks/10nonvolatile flows/3required edges and entry-RDX handoff pass.
Actual first/second arrays, definition40, object byte0/DD values NOT captured.
Full subgroup/order/mask/snapshot model, actor/owner and historical41810 rules
still open. PE/transformed/replay/draft pins rechecked. No fresh game/tracker
decode, production/conversion/sync change, tests/CI/peer review, REA native
provider or target execution. Keep all work offline; full upgrade/playback false.


## Offline subgroup initialization and recorded talent context - 2026-10-27

Read docs/NATIVE_SELECTION_SUBGROUP_CONTEXT_2026-10-27.md and its two dated
native-selection-subgroup-context receipts. Fresh full game reads original/R8/
control: ten wire users0..9,7talents each, ALL70 have a prior same-user selection.
Each first selection bank10/index0/None adds1unit/1group(count1). None does NOT
clear unknown prior state. Latest selection before ALL70 has index0: contexts
source/R8 None+1=53,ZeroIndices+1=11,Mask+0=6;control64/0/6. Not cumulative row
reconstruction; five earlier index1 events still matter. No guessed actor/owner.

A28C90 allocates24180 bytes;352rows*1A4, ranges0..15/16..175/176..191/192..351.
Active loop startsbase120C0 and calls202D680 sixteen times; matchesA28B60 for
all16users. A28370 nested16x10 builds stored ranges. Row ctor directWORD[row]0
andBYTE[row+2]0 occur BEFORE helpers202D3C0/1A2B6C0, whose full memory effects
are not audited. Same encoded base published; null allocation publishes null.
A29420 calls1A24B90 on decoded base then publishes encoded null. No actual init/
reset execution or retained empty row at first event is captured/established.

202DA17 calls202E600(row,descriptor,&index). Unsigned lexicographic order:
descriptor byte4 priority DESC,word0 definition40 ASC,byte5 intraPriority DESC,
word2 conditional unitIndex/3FF DESC. AL1 only all4equal at stopping index;
otherwiseAL0 and insertion/end index. Empty groupcount yields index0/AL0 without
reading incoming descriptor. Preserve effective definition/predicate dependencies.

7ranges1610B/375instr (5new876B/201instr),98selected checks,7nonvolatile flows,
2required edges/4unsigned flag paths pass. Workspace-only hidden/ignored dump
filename search found0; no global absence claim or repeated historical route.
Actual effective tables, init retention, cumulative mask/order/snapshot state,
selected unit/owner and historical41810 rules remain open. No production/replay/
sync change, unit tests/CI/peer review, REA provider/native execution. Keep all
work offline; full upgrade/playback false. Next exact init/helper preservation
and effective inputs before attributing talent actors or changing conversion.


## Offline selection initializer memory effects - 2026-10-27

Read docs/NATIVE_SELECTION_INITIALIZER_MEMORY_2026-10-27.md and dated evidence/
validation. 202D3C0..202D673 is691B/98instr no-call/stack leaf:96stores,32x8B
descriptors, DWORD+0=03FF0100,WORD+4=0,BYTE+6=0,byte7untouched. LastwrittenFE,
all within supplied256B. Full row ctor's LATER zero fill overwrites defaults.

1A2B6C0 original extent ends1A2B850, but only204B prefix through1A2B78C is
qualified for selected zero-fill sizes80/100/24180 hex. Remaining196B include
unqualified data/short-size path. Do not use whole linear exploratory decode
as full code. Size<=16 branch excluded by actual selected operands. Feature
3B5934C bit2(17..128)/bit1(>128) choosesSSE or qualified16B REP tail1A2B6A0.
DFclear and validR11 from prefix required; tail preservesRDI via disjoint stack.
96operand-derived interval cases (3sizes*16alignments*2routes) exact-cover each
buffer with no outside output stores, aligned SSE stores aligned. Not native
execution/emulation or a proof for arbitrary sizes/short path.

Helper footprints now preserve row0..2 directzero stores under normal returns.
With allocationfill/loops, all352rows normalinit ends count/group/index0,
items4..83zero,tags84..A3=20,descriptorsA4..1A3zero,padbyte3zero. Expected420B
row hash is SYNTHETIC, not runtime capture. Active176..191 bind priorgetter.
Actual init occurrence/retention, later snapshot/reset/dispatch effects and
effective catalog/actor values still open. Do not treat empty spec as live row.

7ranges1545B/293instr (3new911B/155instr),73selected checks,96descriptor stores
and96fill interval cases pass. PE/transformed/replay/draft hashes rechecked.
No production/replay/sync change, freshdecode/tests/CI/peer review, REA provider,
native execution or emulation. Keep all work offline; full upgrade/playback
false. Next cumulative removal-mask/state semantics and effective definitions
before talent actor/owner attribution; historical41810 and playback still needed.


## Offline removal masks and conditional talent units - 2026-10-27

Read docs/NATIVE_SELECTION_REMOVAL_CONTEXT_2026-10-27.md and dated receipts.
Native reader1A713D0->1A70A00,kind3/tableindex2->1A70B7B->1A704C0->1A71400.
Original type321 slot10->1359C10 storescount/returnspayload8;choice313 slot18
->135BFF0 tag1/zero count/data/returnchoice4. Delta discriminator4/count8/data10.
Observed masks only1..3bits; successful buffered short path writes decoded
integer into low bits of one byte. Consumer202DC8A tests bit(i&7),byte(i>>3).
120width0..3*offset0..7*allpattern cases agree with pinned Python bit-buffer.
Not a universal longer-array/refill/error or historical-native proof.

202DBC0 None=no removal;Mask reverse min(count,bits);OneIndices reverse supplied
list (do NOT silently sort/deduplicate);ZeroIndices reverse row/tail keep-list.
Observed OneIndices0;all8source/R8 ZeroIndices lists EMPTY. Source masks71:
len1/value1=45,len2/value2=23,len2/value3=1,len3/value5=1,len3/value6=1;current13
alllen1/value1. Remove202EAA0 compacts groups/tags/items;1A2B250 overlapping-copy
contract still explicit. After gates202D910 inserts unique numericuint32 sorted.

CONDITIONAL model: qualified normalemptyinit, no other mutations, validgroups,
ordinarycopy, EACH addition passes catalog/reference gates (NOT authenticated).
Then ALL70talents per source/R8/control have exactly1item;0duplicate/capacity
skips. Latest subgroup0 plus valid1item group suffices without guessed key or
predicate values. Not actual client actor/owner, accepted links or playback.
Existing source18/target22 packing reused, no new conversion. Exact index/recycle
join to strict-prior tracker owner + same-loop alternatives + explicit setup:
all70/case have prior birth/owner,0ambiguous,0control-vs-setup mismatches.
Source/R8 normalized contexts equal;tracker contents only2independent.
2source/R8 candidates areVehicleDragon by EXACT birthkey, not hero/time match.
47source/R8 and36current purchases follow prior trackerdeath records; do NOT
treat trackerdeath as native pool destruction/absence or discard keys for it.

12ranges5185B/1453instr,94selected checks,16switchtargets,120shortmaskmodels pass.
Reader code ends1A7137E;2alignment bytes and64B transformed table separate.
Fresh fullgame/tracker reads,pins pass;public aggregates only, privatekeys retained.
No prod/replay/sync change, tests/CI/peer review, REA provider/native execution,
emulation, game/CU/network/publication. Keep offline;full upgrade/playback false.
Next effective insertion gate/unit identity for expected contexts, then actual
historical41810 rules/native playback. No safe talent remap follows yet.


## Offline Unit catalog creation and insertion gates - 2026-10-27

Read docs/NATIVE_UNIT_CATALOG_GATES_2026-10-27.md and dated gate receipts.
Full31E890..31EF7E ctor loops92indices; manager=context+8+8*i. Index83 isUnit:
originalname row2F32350/literal264D860("Unit",4B),descriptorrow2F33A08/literal
2652230("GameData/UnitData.xml",21B). Same index83 manager=context+2A0 matches
5E1B70/201A490. 31EB61->1609450 receives descriptorrow; resultstoredcontext588,
reloadedtoUnitmanager30 understable-slot/helperconditions. Callee/full actual
IO/load/merge/effective input identity NOT audited. Do not treat path as load.
Conditional15B window3216C0..CF callsctor/copiesreturnthroughRBX/global3388B18;
wholecaller/init occurrence unproved. Global is virtual/non-file-backed.

Creation asks110B manager,2000B pointer arrays. Direct count38/90=0, reserved
fields40/98=400(1024), ptrs48/A0. ZeroRSI iteration invariant: firstnormalinner
loop exitszero; all outer backedges crossXORESI reset; no RSI kill beforestores.
Null allocation can publish null. Scope directcreation/pre-firstpublication,
NOT count0 at ctor return/replaytime; later helper/populationeffects open.
Logical acceptance usescount90/38, NOT reserve98/40. Managerheader0101 is not
resolved definitionobject byte0. Actual entries/null/tag/object gates required.

Inherited pinned linkdomains source/R8:11each36..827(all<1024);current11links
109..1242(5>=1024).33static count0 cases failfirstlookup despitecapacity. Not
observed runtime failure or olddesync/exit cause; control values are not runtime
growth proof and initialreservation MUST NOT become permanentformatbound.
Prior70singleton contexts/case remainCONDITIONAL: actual catalogue gates still
unproven. No defaultentry/acceptance flag, guessedID or conversion introduced.

5ranges2826B/675instr(newctor1774B/410instr),68selectedchecks,2regflows,
RSIresetcutset/92slotmodels/2metadata rows&literals/33counterexamples pass.
Separatepublicationwindow15B/3instr. REAstatusonly:targetnone,cleanupnone,
IDAavailable/unselected,Ghidraunsupported12.0.4;noimport/analysis/targetexecute.
LocalconfiguredIPC probes possible; noexternalnetworktask. Python/WSLobjdump
native evidence. Replay/draft pins pass; no freshdecode/tests/CI/peerreview,
prod/replay/sync change or publication. Keepoffline; fullupgrade/playbackfalse.
Next populatedUnitmanager+samecontext588/manager30 input/merge identity,
logical counts and real entries; historical41810/native playback still needed.


## Offline Unit descriptor producer and nullable backing - 2026-10-27

Read docs/NATIVE_UNIT_DESCRIPTOR_BACKING_2026-10-27.md and dated receipts.
31E946->16083B0 initializes E=root+28;31E9DB stores root at context2E8.
[E]=original142F2F988, DWORD[E+10]=0. Mutable global contents unobserved.
Unit83 call31EB61->1609450 receives XML descriptor/R8D0/E; inherited result
context588->manager30, managercontext2A0. No actual loaded membership follows.

Full1609450 producer: selected optionalRDI0 proceeds after1EFA550 for either
boolean. That helper body/actual file or parse semantics remain unaudited.
16095AA->16092D0(E+8,key); nonzero cache hit returns existing descriptor,
bypasses backend/ctor and does not refresh+28. Cache receiver+8=E+10 zero
returnsnull without comparison calls. Not observed cache state at index83.

Miss160962B->1EF9F80 exact15Btail addsRDX120, R8D0->2A7B10. Fullbackend
defaultsR14zero; receiver+8 count0 skips loop, returnsnull under normalhelper/
stable receiver conditions. Initial global address is not live empty data.
Null backend + successful190 allocation:1609668 R14=stillzeroRBX; fiftharg
callerRSP20 -> calleeentryRSP28 -> calleeRBP40 (3pushes). Full16081E0 ctor
stores fiftharg atdescriptor28 withoutnullrejection, optional0 at20, returns
inputallocation under explicit boundedhelper/noalias/ABI/normalreturn contracts.
Cache/list helpers' fullmemoryeffects still conditions; no actual execution.

Nonnull descriptor/path alone insufficient for loaded Unit/accepted links.
Do NOT invent universal +28nonnull gate or infer all entries absent fromnull:
inheritance/merge/managerpopulation notclosed. No prior desync/exit diagnosis.
6ranges4247B1039instr (5fullPDataunions+1leaf,new2473B629instr), separate
tail15B3instr,86checks/5flows/6paths/fifthargidentity/10relationmodels pass.
Actual Unit cache/backend/manager values and old41810 rules remain missing.
Replay/draft pins preserved; no freshdecode/prod/conversion/replay/sync change,
tests/CI/peerreview, REAprovider/import/nativeexecution/emulation, game/CU/
network/publication. Keepoffline; fullupgrade/playback false.


## Offline catalog context lifetime and lazy slot replacement - 2026-10-27

Read docs/NATIVE_CATALOG_CONTEXT_LAZY_ENTRY_2026-10-27.md and dated receipts.
Full321370..321707 replaces prior15B caller window. Successful F20 allocation
calls31E890, returnRBX published to3388B18 AND3388B20; derived3364AF0=context0,
3364AE8=context5D8,3364AD0=context5E0. No postconstructor helpercalls here.
Not actual init or populated counts. Full321FE0..3222FE restores savedcontext,
refreshes aliases, calls6C4140(0), RELOADS active, ifnonnull calls31F720 then
1A24B90(pointer,F20), directzeroactive/aliases BEFORE furtherexternalhelpers.
Do not infer samepointer after6C4140 or zeros atfunctionreturn. Savedglobal
has no directclear here, not allcallees/program. Both selected7B RIP candidate
refs to3388B20 qualified; heuristic inventory is NOT exhaustive.

201A490 selected Unit lookup still count38/table48; taggedslot calls
1608180(slot-1,0), then reloads OWN manager/table/index. Full93B wrapper:
RDX0->1607B10(P) returnsO; nonzeroRDX suppliesO. Calls27F6D0(P,4,0), unclosed.
M=QWORD[O+68], i=WORD[O+2],j=DWORD[O+8], A=QWORD[M+48],B=QWORD[M+78].
ONLY ifA[i]==(P|1), A[i]=O; EVERY normalpath B[j]=O. Plaincompare/branch/store,
notatomicCAS. Onlydirectnonstackstores those2; no directcount38/90write.
Externalhelper count/tableeffects remainconditions. Caller ignoresreturnreg.
Objectowner/index/table equalcallerrequest NOT authenticated; no actual
replacement, invaliddata diagnosis or acceptance follows fromcallalone.

Full1607B10..160817C (1644B510instr) returns pointer from1600BC0(base=[P+8]),
savedonceRSP68 then2normalRAXdefinitions. Fullbytes/CFG and returnidentity
qualified; fulltemplate/mask expansionsemantics, producerbody,payloadorigin,
O+68/+2/+8 values NOT. Do not infer owner/index from caller or staticmetadata.
5fullranges3668B993instr(new3454B934instr),82checks/5flows/returnorigin and
slotstorepaths pass. Actual encoded payload+producedfields+owner/requested
tables or authentic mergedcatalog/IDassignment needed; more typedgetters or
XMLname alone won't close gap. Historical41810 rules/playback stillrequired.
No prod/conversion/replay/sync change, tests/CI/peerreview, provider/import/
nativeexecution/emulation/game/CU/network/publication. Replay/draftpinspass.
Keepoffline; fullupgrade/playback false.
