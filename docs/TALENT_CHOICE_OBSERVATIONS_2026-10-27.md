# Recorded talent choices expose an unresolved migration assumption

R8 preserves all70 recorded talent-selection indices from the original41810
replay. Its tracker member is also byte-identical to the original, including
the historical `TalentChosen` labels. These facts establish preservation of
recorded data, not how a current client would execute those selections.

For the shared hero `HeroKaelthas`, two numeric indices have different recorded
purchase names in the pinned98348 control. The original is Dragon Shire; the
current control is Lost Cavern. Their map/mod contexts differ, so this does not
isolate the effect of the client build or establish a replacement index.

| HeroKaelthas index | Original41810 purchase name | Current98348 control purchase name |
| ---: | --- | --- |
| 2 | KaelthasManaAddict | KaelthasManaAddict |
| 6 | KaelthasFlamestrikeBurnedFlesh | KaelthasFlamestrikeBurnedFlesh |
| 9 | KaelthasHeroicAbilityPhoenix | KaelthasHeroicAbilityPhoenix |
| 15 | KaelthasLivingBombSunKingsFury | KaelthasLivingBombIgnite |
| 20 | GenericArcanePower | KaelthasMasteryFlamethrower |

See `observations/talent-choice-observations-2026-10-27.json` and
`observations/talent-choice-validation-2026-10-27.json` for file/member pins,
aggregate observations, decoder scope and validation limits. No raw replay,
player identity, player-index association or purchase timeline is projected.

## Association and decoder scope

New `talent_choice_audit.audit_talent_choices` consumes already decoded named
game/tracker events. A selection's user must have an explicit, earlier-or-equal
`SPlayerSetupEvent` player mapping and a stable `PlayerSpawned.Hero` identifier
recorded by selection time. A `TalentChosen` purchase is paired only when it
has the same player ID and occurs exactly one loop after the selection, with
unique keys on both sides. Ambiguous selections/purchases remain unpaired.
Conflicting setup/hero records and duplicate tracker stat keys are rejected.
Unmapped users and missing prior hero records are counted separately.

All70 selections in each of the three recordings have one such unique pair:
210 pairs checked. The adjacent tested offsets -2,-1,0,+2 have zero single
purchase candidates in these files. This is an observed fixed-offset relation,
not a protocol-wide causality definition. No user+1, nearest-time, JSON-array
order, talent tier or purchase ordinal is used to infer an index mapping.

The whole original game member has104257 events decoded with pinned upstream
41810. R8's104257 and the current control's144708 game events use the existing
native observed22-payload codec; named projection uses the pinned96477 physical
graph. Tracker streams use pinned upstream41810/96477 respectively, with6614
and6181 events. R8 reuses the exactly preserved original tracker bytes. Complete
details/initData members are separately decoded through aligned EOF to bind the
recorded map and sync metadata. Upstream decoding is not native execution.

The public auditor returns aggregate hero/index/purchase-name counts. It does
not decode an archive or authenticate input provenance; callers must retain
their own file/build/schema pins. `compare_observed_names` compares only the
name sets at shared hero/index keys and never selects a replacement index.

## Validation and conversion boundary

Twelve focused unit tests pass, including ambiguous event keys, explicit
nonconsecutive user/player mapping, wrong-player purchases, future setup/hero
records, missing heroes, duplicate stat keys, integer bounds, invalid payloads,
input preservation and rejection of nearest-time pairing. Actual replay
aggregates agree with the separately written exploratory per-event pairing
routine. The entire R8 set of70 selection values and historical tracker
associations equals the source. Source/R8/control file length, SHA-256 and stat
identity are rechecked. Existing launcher drafts retain their prior hashes.

The complete offline regression workflow discovers root `test_*.py` modules;
the new test module is eligible for its next run. Hosted CI, the broad local
corpus, independent peer review and client playback were not performed here.

These differing names invalidate treating a same-hero numeric index as an
unqualified cross-recording identity. They do not prove that a talent was
removed, that equal names have equal mechanics, that these selections cause a
desync, or that current Lost Cavern indices apply to Dragon Shire. R8's preserved
tracker names must not be described as current-client execution results.

No conversion rule, replay, synchronization value or version metadata changed.
Keep the current offline instruction: no game, Computer Use, network or remote
publication. Full replay upgrade and playback remain unproved. The next useful
talent boundary is authentic target-context talent definitions and source-rule
equivalence; do not guess a mapping from this sparse observation table.
