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
