# TEN_GREYMANE — Dragon Shire R5

Date: 2026-09-29

The new file is an experimental same-map metadata migration, not a confirmed playable replay.

## Inputs and observations

The user supplied a fresh Dragon Shire replay after the prior R4 file failed with:

> The mod data loaded does not match the mod data which was originally used to play this game.

The new reference was saved at 10:18:01 on 29 September 2026. Its SHA-256 is `5a7b05f4a75bc229dbbd74e6cc09e3b411129fc731874cfaa9217432fb85e7dc` and its size is 124915 bytes. Its header, lobby, details and every observed event were decoded and re-encoded. The observed version, base build and data build are all 98285. The latest fetched ordinary-launch Graphics log, 09:58:51, independently identifies 2.57.0.98285. No version retargeting is performed by R5.

The reference is a custom game. Its matchmaking, competitive and matchmaking-ID options differ from the recorded TEN_GREYMANE options. Those three options, its players, bots, random seeds and events are not copied. The user's word "done" establishes that the requested reference is available, not an independent tool observation of playback.

## R5 changes

R5 starts from the hash-bound, immutable CONTROLS_R4 file. It replaces three member payloads and records five semantic audit entries:

- `replay.initData`: map checksum `2D44411F` to `34D3C979`, mod checksum `D1F0FE9E` to `87ACFB98`, and five cache handles to the six from the same-map reference.
- `replay.details`: the duplicated cache-handle list is made identical.
- `replay.server.battlelobby`: only the fully parsed dependency prefix is rewritten. The prefix grows from 861 to 1033 bytes. The remaining 40885 bytes are preserved exactly, with SHA-256 `1d67f38df429887986187ae2594085ec70d4080a1fd7e4249cac83c3137e1b60`.

Both the original and fresh dependency prefixes re-encode exactly. Paths are derived from the original cache root and the observed handles, not copied from private donor account paths. The first four dependency handles are unchanged; the old final Dragon Shire handle is replaced by the two handles observed in the current reference.

The replay header is unchanged. All gameplay, message, tracker and opaque event-stream bytes are unchanged from R4: 104257 game events, 155 messages and 6614 tracker events. Native StormLib preserves HET/BET tables and the 16384-byte raw-chunk setting. Available native CRC/MD5 checks and independent mpyq extraction were checked.

## Artifact

`TEN_GREYMANE_client98285_DRAGON_R5_EXPERIMENTAL.StormReplay`

SHA-256: `f5eac2c4de55db9cc834c97825ac89d5fc0bb4807a2b216ba5ca7fbc63e45f11`

Size: 1255308 bytes. Base64 parts: 23.

## Validation and implementation correction

The genuine custom-game reference has an existing zero-length message stream. The old MPQ reader reported all zero-storage members as missing. The reader now distinguishes an allocated empty member from an absent member and rejects nonempty entries without storage.

The first R5 CI run, 36544073444, passed all new R5 tests but failed one older binding integration test: mpyq returned `None` for an existing empty `replay.sync.history` while the corrected reader returned `b''`. This failure was not suppressed. The binding comparison now normalizes only an independently proven allocated zero-length member; missing members, failed decompression and truncated contents are rejected. Nine extra tests cover this guard. The replay artifact itself was not changed by that validation correction.

Locally, 33 initial new tests passed, then nine new independent-reader guard tests and the seven existing binding tests passed in completed runs. The corrected CI run **36544856084** at code commit `644560b5510ad47fdeed16c6c00e4b3ed989ddc6` completed successfully: **166 tests passed, no failures or skips**. Both independent CI generations match the local R5 SHA-256. The downloaded CI candidate and all 23 Base64 parts reconstruct the identical file. The publication commit is `e9978bb24aea4d55b69c356628138658019bb254`.

## Remaining limitations

Updating recorded checksums and cache references does not embed or port the referenced mods. The original 2016 battlelobby remainder, opaque synchronization data, numeric ability/unit catalogs and simulation rules remain unconverted. The custom reference does not prove equivalence of every game-mode-dependent initialization value. Official schema 96477 covers the observed serialized payloads; it is not a proof of the complete 98285 schema.

No HotS executable was run in this validation environment. The mod-mismatch check passing, reaching the loading screen, and playing the complete match are three separate results that still require a client test.

## Persistence and next test

The candidate was uploaded under a distinct filename to the existing OneDrive project folder and the user's Multiplayer replay folder. Originals and previous candidates remain unchanged. Public Git receives the allowlisted reference observation, code, tests, generated reports and text Base64 parts, not the private original reference or crash memory.

Open the file ending in `DRAGON_R5`, record whether the mod-data error disappears and whether the match clock advances. Preserve any new error together with the exact filename. Do not infer a successful complete match from archive validation.

The CI Git bundle preserves the complete source history through the R5 artifact publication commit. Subsequent session documentation and delivery progress are included separately in the dated delivery package; the private donor replay and raw crash memory are excluded.
