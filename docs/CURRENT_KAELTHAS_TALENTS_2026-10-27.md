# Current Kaelthas definitions constrain the talent migration

The exact cached Kaelthas XML whose digest matches the frozen98348 extraction
contains21 literal `CHero.TalentTreeArray` entries. `SunKingsFury` is still in
that tree, at Tier3/Column2. `KaelthasGravityCrush` and `GenericArcanePower`,
both recorded in the original replay, are absent from this particular tree.
This is a scoped definition check, not a removed-talent or global absence claim.

The new evidence refines the earlier source/current replay comparison. It
does not authorize preserving every original index, replacing indices by
matching names, or assigning new behavior to a missing historical talent.

| Original recorded purchase | Original index | Literal position in current XML, zero based | Current literal Tier / Column |
| --- | ---: | ---: | --- |
| KaelthasGravityCrush | 7 | absent | absent |
| KaelthasLivingBombSunKingsFury | 15 | 7 | 3 / 2 |
| GenericArcanePower | 20 | absent | absent |

For context, the same current tree places `KaelthasLivingBombIgnite` at document
position15, Tier6/Column2, and `KaelthasMasteryFlamethrower` at position20,
Tier7/Column4. All seven Kaelthas choices in the previously decoded98348 control
have recorded indices equal to their corresponding zero-based document
positions. This is corroboration for seven observations in that control;
general native index semantics and effective loaded catalog order are unproved.
The public report labels document position separately from native index.

## A name-only mapping also has an unresolved tier conflict

The original's two Kaelthas players made14 recorded purchases with10 distinct
index/name pairs. A fresh original41810 decode reproduces all70 earlier talent
associations. Restricting it to Kaelthas gives:

- two purchases whose names are absent from this literal current tree;
- two `SunKingsFury` purchases whose old index differs from its current document
  position;
- ten purchases whose index/name pair matches a current document position.

One source player purchased both `KaelthasFlamestrikeBurnedFlesh` and
`KaelthasLivingBombSunKingsFury`. Both names belong to literal current Tier3.
Consequently a name-only lookup places two historical purchases in the same
current tier for that player. The pinned global `CHero` default separately
declares Tier3/Level7 and Tier6/Level16. Neither the source purchase ordinal nor
the current default is used to invent a historical tier definition.

This exposes a dependency on actual talent rules. It does not prove that a
current client rejected a purchase, that multiple purchases in a tier are
universally forbidden, that a recorded command caused a desync, or that the
two names retain their historical mechanics.

## Exact inputs and validation

The Kaelthas body is276044 bytes, SHA-256
`39cf6954288e32edd73dfed13f82e45ab5f944a54f9f3fa9adaf2aacc7ffc13b`.
Its complete bytes match the pinned file inventory in
`observations/collection-license-current-98348.json` (SHA-256
`c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22`).
The source body and matching global herodata body are already cached; no
network refresh or new CASC extraction occurred. The frozen extraction's
version-log/hdp.info binding is preserved as provenance, not a fresh extraction
or live client observation.

ElementTree and a separate Expat parser agree on all21 literal talent entries
and all seven default tier declarations. The Kaelthas body's only `<?...?>`
marker is its XML declaration. Selected `CTalent` declaration summaries retain
literal Face/Abil fields, child counts and explicitly labeled serialized-tree
digests. Those digests are not hashes of original byte spans or complete
mechanical definitions. File length/SHA-256 pins for source/R8/current and the
unused launcher drafts are rechecked.

See `observations/current-kaelthas-talent-definitions-2026-10-27.json` and its
validation receipt. These are two file-local literal definitions and scoped
replay observations. Inheritance, defaults, include/load order, mod overrides,
tracker-Hero to effective CHero identity and native index/acceptance semantics
remain unresolved. The current replay is Lost Cavern; the original is Dragon
Shire. No cross-map effective catalog or historical-rule equivalence follows.

This milestone changes no production code, conversion recipe, replay,
synchronization value or version metadata. New unit tests, broad corpus,
hosted CI, independent peer review and native client execution are not claimed.
The earlier12 auditor tests remain the prior milestone's evidence; this
milestone adds source checks and independent parsing of the actual XML files.

Keep all work offline. Full upgrade and playback remain false. The next
conversion boundary is the native talent index/selection rule and authentic
effective target/historical definitions, especially the missing names and the
conditional tier conflict. A guessed15-to7 rewrite cannot establish fidelity.
