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
