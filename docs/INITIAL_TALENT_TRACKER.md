# Opening Greymane and Kael'thas talent awards

TEN's first talent selection occurs at loop 86. The source selects index 3 for tracker player 6. Two genuine 98348 controls link Greymane selector 2 to the first-tier Viciousness award. In the pinned target CHero tree, zero-based position 2 is tier 1, column 3, and the referenced CTalent is GreymaneInnerBeastViciousness. The target GameLib uses the player's active tier and selected column, and writes the selected row's catalog link to the PurchaseName field. The separate source index 3 would select a different target talent.

The verifier reads the earlier signed input projection and selects only first purchases that have an independently supported translated selector, an opening player/hero identity, and an available first tier. Signed startup contains the matching PlayerSpawned and LevelUp information. This produces the following three rows.

| Original input ordinal | Original tracker ordinal | Award loop | Player | Target selector | Derived target identifier |
| --- | --- | --- | --- | --- | --- |
| 427 | 243 | 87 | 6 | 2 | GreymaneInnerBeastViciousness |
| 1536 | 250 | 355 | 7 | 2 | KaelthasManaAddict |
| 6214 | 464 | 1217 | 4 | 2 | KaelthasManaAddict |

The upstream translation used historical choice evidence to identify the intended purchase. Here the translated selector addresses the target hero catalog directly. The generator withholds all recorded PurchaseName fields until comparison. It assumes ordinary target selection acceptance, unchanged introductory talent-tier availability and a one-loop interval between selection and award. The signed map modifies only the Kael'thas quest target count in these opening CTalent definitions. Hero talent layouts are unaffected.

Across the pinned 24 current native recordings, six first purchases by the two scoped heroes were available for direct testing. All six predicted payloads matched every byte of the actual tracker frame at the physical delta. Two recordings witnessed Greymane selector 2, and two witnessed Kael'thas selector 2. The others tested column 1. The three TEN projections also match the historical physical frames when encoded with their true preceding tracker timestamps. The combined sparse three-row member is 302 bytes, SHA-256 641010b8498a0e4faf25ab206cc6df3f41aa7d85b13db22a2ec5fcbb8288e91b. Sixteen later translated selections depend on unresolved earlier awards and are outside this result.

The same check reopened MercCapture (SHA-256 `54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a`) and checked each map-authored game-data XML member for relevant hero-tree and talent overrides. Both map packages produce identical 302-byte tracker streams from the pinned opening state and translated inputs.

Run `initial_talent_tracker.py PRIVATE_MANIFEST GENNDATA_XML KAELTHASDATA_XML GAMELIB_GALAXY SIGNED_ANNOUNCER_OR_MERCCAPTURE_MAP SIGNED_GAME_INPUT_DIRECTORY PRIOR_SIGNED_TRACKER_PREFIX --output NEW_PRIVATE_FILE` using the published repository modules and protocol dependencies. The previous signed prefix is pinned at SHA-256 1073a5bdbffca7d6c50fd4ffe7dcedfe150ea4d2ba4152b4db7b04b357259d86. Generation reads the saved files offline and preserves the original replay.
