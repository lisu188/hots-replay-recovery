# Remaining source unit-link gaps

The startup review and this follow-up are separate. Of the four selection
catalog fields before loop64, Greymane, FaerieDragon and Anubarak now have
same-map current98348 observations. Kaelthas has a current other-map candidate.
The old two null anchors therefore describe older reference coverage rather
than missing tracker identities or a failed current decoder registry.

The later full-match catalog comparison contains44 unambiguous observed
candidates and six unresolved types. A fresh original/R8 read confirms that the
three types with no current link observation are used in the source game:

| Recorded source type | Old link | Tracker occurrences | Classified catalog fields | First catalog-reference loop |
|---|---:|---|---:|---:|
| AbathurEvolvedMonstrosity |36|Six births, first6722; six deaths|191: five selection fields plus186 command-target/update fields|7190|
| NovaHoloCloneCloaked |207|Thirteen births, first2303; thirteen deaths|31 command-target/update fields|14589|
| TownCannonTowerL2Standalone |532|Six births at loop0; five later type changes to TownCannonTowerDead|140 command-target/update fields|3753|

All targeted lifecycle/reference statistics agree exactly between original41810
and R8 after accounting for their recorded packed-tag layouts18 and22. The game
and tracker streams in both files reencoded byte-exactly, and their semantic
payloads agreed with the pinned official Blizzard decoders:104257 game events
and6614 tracker events per file. No messages were read. Zero commands had any
of these three types as a uniquely selected context agreed under both removal
mask orientations. Their command-target references do not establish executing
casters or portable ability names.

The remaining three ambiguous types are a different issue. Source
TownCannonTowerL2 has407 classified fields at oldlink531, while
TownCannonTowerDead has two update-target fields at that same link, both at
loop6263. Twelve L2 units were born at loop0 and later changed recorded type to
Dead. The source also records standalone and L3 type changes to Dead.
Consequently, a global oldlink531 replacement cannot be selected merely from
one tracker name. This report does not retain the two fields' private unit-tag
lineages and cannot establish their exact earlier tower form. A source-chain
check of those two rows would be a distinct bounded follow-up. No collision is
collapsed and no alias or replacement is assigned.

Current donors containing Abathur or Nova do not prove the relevant summoned or
cloaked-clone state occurred with a usable catalog field. Likewise, the scoped
published Nova XML observation does not establish that every current package
lacks the old cloaked-clone name or that it maps to NovaHoloClone.

`inspect_source_gap_lifecycles.py` is a local research reproduction with explicit
paths and hashes. It reads original635140 bytes and R82438570 bytes once into
RAM, then rereads original for its final full SHA256 guard:3708850 disk bytes
in total, below4MiB. R8 has an unchanged size/mtime and RAM SHA256 after analysis;
there was no second full R8 disk-hash read. This distinction is retained in the
JSON report. No raw tags, positions, user IDs, players, complete events or private
objects are written. No client, PE, old header, dump, network or replay conversion
is involved.

The source usage establishes the significance and timing of each gap. It does
not supply a current target link, authenticate new live object allocation or
prove deterministic simulation equivalence.
