# Additional current replay evidence

Six additional public NGS replays were acquired within a 12 MiB limit; their
actual total is 7,247,399 bytes. All six declare executable/base/data build
98348, use root `c3b3c8bc82e3a5a62e550fdde9a40c28`, and pass the observed core
stream round-trips against the exact pinned Blizzard 96477 schema. Raw donor
replays and player/chat contents stay outside Git.

| Map | Shared unit types with the Dragon controls | Equal link sets | Different link sets |
|---|---:|---:|---:|
| Sky Temple |36|36|0|
| Battlefield of Eternity |28|28|0|
| Volskaya Foundry |35|35|0|
| Tomb of the Spider Queen |36|36|0|
| Towers of Doom |20|20|0|
| Infernal Shrines |28|28|0|

These are 183 comparisons spanning 75 distinct shared unit names. All six
recordings share the first four base dependency handles with the Dragon cohort,
but their other dependency lists and mod checksums differ. Agreement for those
observed types does not establish independence of every catalog entry from the
map or additional mods.

The combined observation has 42 unambiguous candidate pairs. Nine were absent
from the earlier Dragon-only proposal:

| Unit | Source link | Observed other-map link |
|---|---:|---:|
| AbathurLocustBombardStrain |33|488|
| AbathurLocustNest |37|498|
| AbathurLocustNormal |32|487|
| AbathurSymbiote |302|438|
| AbathurToxicNest |35|496|
| HeroAbathur |60|493|
| HeroKaelthas |827|632|
| HeroTyrande |84|850|
| TownGateL3BLURBRVisionBlocked |513|278|

These nine remain provisional other-map observations. The earlier 33-pair
Dragon-only proposal is unchanged, and no replay or migration eligibility was
modified. Nova, its clones, Abathur's evolved monstrosity, the remaining tower
observations and the existing tower aliases still require further evidence.

The public index is the NGS read-only reported-matches endpoint, queried with
`POST {"season":22}`. Its 451,821-byte response has SHA256
`51cea7d89c0afe887a31c6bc549c0a35b740e997c4d8e8d195b3eef8c602610c`.
The dated observation retains each exact public object URL, replay digest,
profile/inventory digests and the dependency contexts. Filename dates alone are
not used as build evidence.

# Remaining format and package findings

The opaque-player-field investigation tested 289 complete field/representation
groups against 14 actual replays. None of the 146 groups with varying values
identified a matching slice in the opaque blocks. Constant matches failed the
wrong-player and wrong-match controls. The adjacent known Toon identifier
provided a positive control: 146/146 correct comparisons, 0/1384 wrong-player
comparisons. This rejects the tested direct representations; it does not prove
that the block lacks smaller fields, derived values or other encodings. No
174-to-198-bit embedding or inserted default was established.

All 591 local s2mh headers passed their filename SHA256 and wire checks. They
include EU packages for the six current s2ma payload digests, but leave 936
possible version combinations under an explicitly unproven interpretation of
dependency version zero. Exact current US headers are still missing. Payload
equality for Standard Data redirects does not establish the installed mod build,
and a depot SHA256 cannot be truncated into a CASC content or encoding key.
No regional header substitution was performed.

Nineteen inspected public XML snippets now match the exact 98348 extraction
inventory byte for byte. Their literal hits for old Stitches/Uther names are
visual model references, while the explicit progression-conversion table maps
currencies and loot chests. None supplies a reward/entitlement alias for the
unresolved collection names. A broader exact-build XML scan remains separate
work; absence in this bounded subset is not a global absence claim.

R8 remains the latest replay. Unit-instance allocation, ability links, historical
rules and synchronization semantics remain unresolved. No HotS client was
launched and no current-client playback outcome is asserted.
