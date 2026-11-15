# Current98348 canonical hero attributes, 2026-11-15

The same finite 61 NGS objects now have canonical hero-entry-code coverage from
`replay.attributes.events`. The earlier English `replay.details` label screen
alone did not establish locale-independent selection. The new member question
adds a selector without changing the earlier report or assuming its labels'
locale.

All 61 attributes members decode completely: 35,502 fixed records, including
610 namespace 999 / attribute 4002 records, exactly 10 per object. The official
Blizzard attributes function and a separate struct parser agree. `Abat` occurs
once, on the same already selected object whose retained tracker records
`AbathurHeroicAbilityUltimateEvolution`. No additional candidate or tracker was
acquired, and no Monstrosity spawn or numeric UnitLink was recovered.

The acquisition reused each object's prior size and strong ETag. All 366 new
HTTP 206 ranges supplied If-Match, including their initial request; retained
range bodies match exact lengths and digests. The 151,710 additional response
bytes bring this cohort's partial total to 332,228 bytes. All 488 retained-source
pins were independently checked. Reconstructing the MPQ directories and stored
blocks from those responses, then bounded bzip2 decompression, reproduced all
61 raw members. Whole replay hashes and playback remain unverified.

The pinned native graph separates `Battlenet::Attribute::Entry.m_code` from its
visual/localized fields. The code path is Entry 227 -> USER 228 -> FOURCC 188,
named `Battlenet::Attribute::EntryCode`. The separate visual chain contains
229/212 and OPTIONAL 213 -> 216 -> LocalizedString 198. One existing positive
98348 control and one negative control were independently re-read. The positive
has one `Abat` attribute, one full initData hero identifier, one initial
`HeroAbathur`, and one explicit slot.userId -> SPlayerSetupEvent.playerId ->
control/upkeep join. The negative has zero corresponding records. This is a
bounded recorded association; no scope + 1 formula, universal owner mapping,
native caster identity or effective catalog index follows.

The [aggregate observation](../observations/current98348-canonical-attributes-2026-11-15.json)
omits raw scopes, per-player rows and raw member/transport paths. The byte-exact
[sanitized bridge receipt](../observations/current98348-canonical-hero-bridge-2026-11-15.json)
and [independent review](../observations/current98348-canonical-attributes-peer-review-2026-11-15.json)
retain source digests and validation limits. Raw attributes, stored blocks,
transport responses, player/owner joins and bit spans stay private under work.
The copied review's publication-scope note describes the original work report;
the aggregate here implements that omission.

Malformed, missing or unsupported attribute carriers remain unresolved. The
canonical selector adds no old/current ability assignment, missing player-field
value, historical rule or synchronization replacement. The current Monstrosity
catalog/ability gap remains. Native control and same-session catalog diagnostics
remain a separate authorized workstream; this milestone makes no new runtime or
completed TEN_GREYMANE conversion claim.
