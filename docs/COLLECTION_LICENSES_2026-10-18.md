# Static collection license evidence for build 98348

The original and R8 battlelobby tails contain 263 variable-length UTF-8 asset
names. Both initial genuine current controls contain the same 5,418 fixed
eight-byte identifiers. The published catalog-only projection contains these
identifiers, their encoding and source-member digests; it contains no ownership
bytes, player identities or account data.

Fifteen revision-pinned public XML files provided a useful preliminary control:
all 1,418 distinct direct License values in that subset occur in the current
collection. This is an incomplete, game-version-unbound subset. ProductId and
License also have numeric collisions, and legacy asset names have changed.
Numeric overlap alone is not an authenticated old-name-to-current-ID mapping.

`collection_license_audit.py` records direct CReward license declarations and
CHero/CSkin/CMount reward references. It keeps ProductId and HyperlinkId separate,
and marks duplicate records, inheritance, templates, indexed array operations
and removals as unresolved. XML child ordinals are source locations, never
runtime catalog indices. The collector refuses DTD/entity declarations, bounds
input trees/files/XML/report sizes, and writes only a new JSON report outside
its input tree. It never writes a replay or copies an ownership matrix.

The GitHub workflow `.github/workflows/collection-licenses-98348.yml` uses the
previously reviewed HeroesDataParser 5.1.0 Linux executable with pinned SHA256
`d5db68a8659456c287df3ed65d64c4786a6501e8f1c638008c81032e90da9f9d`.
It requires the official Blizzard EU manifest and the extractor's version log
to agree on 2.57.0.98348 before extraction. The collector separately checks the
named version and live/PTR fields in extracted hdp.info. If the live target has
changed or the extracted metadata is missing or unsupported, it fails rather
than substituting data. Bulk extraction occurs in temporary GitHub runner
storage. Only measured identifiers, source-relative paths/digests and diagnostic
provenance are published; raw game XML is not uploaded.

The actual [run39156204685](https://github.com/lisu188/hots-replay-recovery/actions/runs/39156204685)
passed33 Linux tests, exact version checks, extraction and publication. It
extracted5739 total files; the collector examined5575 XML files plus hdp.info,
79,556,139 source bytes and10,199 tracked declarations. All5418 observed current
IDs have direct License candidates. One additional direct License is absent
from the observed list. The measured projection is version-bound98348 evidence,
with generator commit/run and source-file digests. Version/log agreement is
provenance evidence, not a digital signature or runtime proof.

For the263 legacy names,56 have one exact-name observed literal license
candidate each. Two of these declarations retain unresolved parents;54 have
no recorded unresolved declaration reason. Six exact-name records lack a direct
License and201 names have no exact current reward record, leaving207 without a
direct observed candidate. These are candidate relationships, not an applied
migration or established old-name equivalence. Duplicates, inherited/default
semantics, omission/ownership states and renames remain unresolved. The raw
collection availability bytes have not been changed.

Primary implementation sources:

- [HDP 5.1.0 extractor](https://github.com/HeroesToolChest/HeroesDataParser/blob/v5.1.0/HeroesDataParser/Infrastructure/Commands/CASCExtractCommands/CASCExtractService.cs)
- [Revision-pinned preliminary public data](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/tree/e3e57cb640f18002a4feebe3872cefe04072d814)
- [Official Blizzard live manifest](https://eu.patch.battle.net/hero/versions)

R8 remains the latest replay. Collection migration, all other format differences
and deterministic compatibility remain open until their own evidence exists.
