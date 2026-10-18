# Authenticated static arcade-section interpretation

The old block previously described as unknown447bits is part of the published
package's **howToPlaySections**. Two exact source package headers were fetched
from Blizzard's depot and SHA256-verified against the original battlelobby's
terminal s2mh handles. Their named numeric trees reconstruct the original
member bits exactly. This resolves the interpretation of that block without
retagging it, clearing data or copying another match's settings.

The primary named decoder is
[s2mdec at b48c60a697b12ae1dc8681a2d42ce313958ce94a](https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L571-L610).
Its [localization keys](https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L188-L206)
contain an optional color, table index and localized-string index. Its
[ArcadeInfo](https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L686-L716)
places howToPlaySections at numeric field4 under mapheader field19.
These names come from a community decoder; the separate authenticated bytes
and numeric equality establish their application to these source packages.

For the actual absent-color records, serialization is:

| Field | Bits |
|---|---:|
| Section-header array count |4|
| Header title: optional-color flag, table, string index |1+6+16=23|
| Header item start offset |32|
| Header list format |2|
| Header subtitle localization key |23|
| Localized-item array count |7|
| Each localized item |23|

Each observed section header therefore occupies80bits. Both authenticated old
groups contain3headers and9items. After their four-bit count, the body is
`3*80 +7 +9*23 =454bits`. The earlier reverse-engineered schema split those
same454bits into447+7. Its final7-bit scalar was not an independent item count.
Including the initial count, the entire section is458bits. No47-bit deletion
or3-to5 retag is justified or needed.

The two source header SHA256 values are
`b34d0f30dc3b9cf47694982106a04006a49ce43422e02f71ed18b33b7bfcc6c4`
and `9bdcdbb192244902f650020fa302951b0fd1f5487aad0096df01ddccd7b4acd2`.
For the original member, the complete section boundaries are210957..211415
and213546..214004. R8 retains identical numeric subtrees and section content
at the shifted positions. The private reconstruction uses the source bit
alignment, preserves every bit outside the selected section and requires
full-member byte equality.

The published third-party C# baseline calls this field ChoiceSection2 and skips
payloads for values0..4. A genuine count3 therefore becomes a false empty
choice under that implementation. Its case5 consumes400bits, matching
5*80-bit headers. The baseline DLL remains unchanged and its original failures
remain recorded. This finding distinguishes a third-party parser limitation
from evidence of a different engine serialization for this section.

The current observed Dragon Shire group contains5headers and1item, occupying
434bits including both counts; its other ArcadeInfo group is empty (11bits).
The verifier labels these as observed-array roundtrips unless the corresponding
exact current s2mh header was also acquired. Three current US package headers
were downloaded and verified, but all three headers containing the remaining
current package metadata returned404. The EU endpoint returned404 for all six
US header hashes. Those outcomes do not establish EU/US package equivalence.

All five original package identity pairs also equal the authenticated header's
`id,version` fields. All ModDependencies pairs equal its extraDependencies
`id,version` pairs. The zero dependency-version values are preserved; no
additional meaning for version0 is assumed. The original's five archiveHandle
packets match its dependency prefix. R8 matches four, while its old map header
refers to an archive absent from the updated prefix. The verifier reports that
remaining package-coherence mismatch explicitly.

The corrected endpoint comes from
[sc2reader at e10fc9344417d0aa9649e4ed8d6423e38f6af4c9](https://github.com/ggtracker/sc2reader/blob/e10fc9344417d0aa9649e4ed8d6423e38f6af4c9/sc2reader/utils.py):
`https://{region}-s2-depot.classic.blizzard.com/{sha256}.s2mh`.
The obsolete region.depot.battle.net host does not resolve in this observation.
Acquisition uses exact content addresses, bounded reads and SHA256 verification;
header bytes and publisher fields remain private, outside published artifacts.

The modules provide a static-section codec and a bounded generic versioned-wire
decoder. The verifier's only output is a new sanitized JSON report. It accepts
explicit raw member paths and a directory of already acquired exact headers.

Both metadata envelope profiles now use this same counted-array interpretation.
The CLI label `historical-fixed` remains compatible with older invocations; the
new output uses neutral static-arcade names and explicit section boundaries.
Nonempty auxiliary arcade arrays or tutorial links remain outside the observed
profile and are refused rather than decoded using an invented layout.

```powershell
python verify_authenticated_arcade_sections.py --case source legacy-10 historical-fixed ORIGINAL_MEMBER.bin PRIVATE_HEADER_DIRECTORY --output NEW_REPORT.json
python -m unittest test_battlelobby_arcade_sections -v
```

The frozen tests contain small static numeric fragments from the original and
a current member. They contain no players, publisher identity, localized text,
chat or synchronization data. Synthetic color and wire tests are labelled as
tests. Successful section verification does not establish complete battlelobby
compatibility, current catalog/ability/instance mappings or deterministic
playback. No replay, member or header is written and no game client is launched.
