# Dragon Shire opening announcer

In TEN_GREYMANE, original game-event ordinal 33 (zero-based) is event 46 at loop 68, three loops after the previous game event. The reporting replay user is 1, tracker player 2. The original sound word is 0x003a0c7b. Nine other players independently identify this as the word omitted by player 1 from their ten opening sound-offset reports. Player 1 subsequently reports that word at loop 119. This identifies a recipient-specific handle inside the original recording. Its target slot and generation remain unknown.

## Producer evidence

The regular 98348 countdown uses the opening-gates timer at 34 seconds remaining to enqueue GetReadyForBattle for ten hero players and observer player 0. The target library maps that event to the HeroSelect voice field. Each available sound plays for a singleton player group. The initiated-event listener takes the same sound object and waits for its end outside Arena and Attack/Defend modes. Overrides, disabled announcements, incomplete introductions, pending queue timers, assigned announcers and absent catalog entries can change this path. The common word in the cohort matches the expected non-recipient behavior of an observer-only sound. The replay supplies no catalog IDs with event 46.

The class-15 native producer emits event 46 with the sound object's own 32-bit handle. Its pending check requires a live request and an eligible unreported bit. After the preceding mode and client gates, a missing local playback pointer branches directly to emission. An active playback object uses playback-state and offset checks. Thus a client outside a singleton recipient group can report immediately if it has no local playback, while a recipient can report later. The precise first target word would also require the actual shared handle-pool state.

The five exact 41810 archives and 24 exact 98348 archives are pinned as build/SHA pairs. Among the four old recordings with offsets in the measurement window, the first offset arrived two loops after the gates-minus-34s threshold. One old recording lacks offsets through gates plus 1,024 loops. In all 24 current recordings the first offset arrived one or two loops after the threshold. In three complete legacy patterns and 19 complete current patterns every recipient later reported its exact previously missing word. These give 30/30 old and 190/190 current recipients. All old and 189 current reports were strictly later than the recipient's full first ten offset events, with one current tie on the same loop. Timing alone does not uniquely identify an asset.

The enUS default LadyofThorns_HeroSelect00 recording has 124,641 samples at 44,100 Hz, or 45.22 game loops. The separately named Observer asset has 133,688 samples, or 48.50 loops. The regular field lookup has no Observer suffix on this path. Stock Dragon Shire controls marked NoAnnouncerPack or LadyofThorns in their lobby contained 29 matching recipients in the complete patterns. Their lags from the final initial report to the first own report were 47 loops (5), 48 (21), 49 (2) and 52 (1). TEN's ten lags ranged from 46 to 50 loops. Neither a player's audio locale nor an exact offset from playback start is encoded in this comparison.

## Map correction

The original map and the SharedBeaconReset and SignedBeaconReset derivatives call the two legacy announcer setters after InitializeStormMod. In 98348 these setters fill the historical global pack and selected index. The active sound player reads a separate per-player loot announcer record. Stock Dragon Shire initializes that record in the same map-init phase with DataAnnouncerVOSetDefaultAnnouncerForPlayerGroup(PlayerGroupAll(), "LadyofThorns"). A player-assigned pack takes priority because the stock routine only loads the default when lv_announcerIsPlayerAssigned is false.

Each derivative adds the single stock line after the two historical setters, before map initialization returns. Stock's preceding cosmetic tribute initializer is outside this edit. The new call preserves already-assigned packs and fills eligible default entries. The new maps do not assume any TEN player chose a particular announcer. Both alternatives rebuilt byte-identically twice; all 69 other content members matched their respective parents, with all six native raw-table checks zero. The preferred signed-index map SHA-256 is 150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791. The alternate shared-marker map SHA-256 is bfe724300b1beadb4d9d76a34385a8adfd719b2346a43a9d1e1cb0a25d960ccc. Native compilation and playback remain untested.

## Reproduce

Use the repository Python modules and the pinned protocol dependencies on PYTHONPATH. The private manifest contains [path, SHA-256, build] triples. Licensed inputs and generated maps stay local.

```sh
python verify_first_sound_cohort.py PRIVATE_REPLAY_MANIFEST
python first_sound_timing.py PRIVATE_REPLAY_MANIFEST > first-sound-timing.json
python verify_dragon_announcer_producer.py SCRIPT_DIRECTORY CATALOG_DIRECTORY AUDIO_DIRECTORY first-sound-timing.json HEROES_98348_EXE PINNED_DECODED_TEXT
python dragon_announcer_default_map.py PARENT OUTPUT STOCK_DRAGON_MAP ORIGINAL_DRAGON_MAP --stormlib STORMLIB
python dragon_announcer_default_map.py PARENT OUTPUT STOCK_DRAGON_MAP ORIGINAL_DRAGON_MAP --stormlib STORMLIB --verify
```

The catalog directory contains the two named XML members; the audio directory contains the two pinned enUS Ogg files ending in their catalog asset names. The stock script directory includes the local member manifest used by the Dragon Shire camp analysis. The cohort digest covers sorted build/digest pairs and is invariant to path relocation. The individual replay verifier reads each whole archive by SHA. The producer-verification program checks the pinned catalog mapping, complete audio pages, native producer, local playback branch, and digest of the replay result.
