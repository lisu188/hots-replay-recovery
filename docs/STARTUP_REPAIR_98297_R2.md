# TEN_GREYMANE startup repair R2: client 98297

Date: 2026-09-29.

User request: repair TEN_GREYMANE so that it opens in the currently installed client. Preserve the original, publish progress frequently to GitHub and keep a OneDrive checkpoint.

## New deliverable

`TEN_GREYMANE_client98297_STARTUP_R2_EXPERIMENTAL.StormReplay`

- Declared version: **2.57.0.98297**.
- SHA-256: `4c6adf30e2c5fc9440c46b2c614c09fc6d3d5d6ef4b4f57f68aaf9a92bbe4915`.
- Size: **1228711 bytes**.
- Public checkpoint: `client-checkpoints/98297-startup-r2/`.
- Publication commit: `fdbfb3f1973ab20dd533173de25c541b7e061f97`.
- Status: **structurally validated; awaiting actual client playback**.

This is a new TEN_GREYMANE attempt, not the Braxis control. The previous 98285 candidate remains recorded as client-crashed. No original replay or existing candidate was overwritten.

## Three changes

### Installed-client identity

The live-launch Graphics log from 06:28:13 on 29 September explicitly identifies executable version 2.57.0.98297, data build B98297 and code revision 668643. The following crash came from a separate 98285 process launched by that 98297 client. It was not a launch of the original 2016 build.

The installed `.build.info` supplied build key `d170b1ad65ebcde3f4252e3088b0c102`. CI downloaded the corresponding Blizzard configuration from:

`https://eu.cdn.blizzard.com/tpr/Hero-Live-a/config/d1/70/d170b1ad65ebcde3f4252e3088b0c102`

Its exact 1201 bytes match that MD5 key. SHA-256 is `3eb13724907500bd614ff977af2a818e6acc420d11bcd95ff2e91736680db447`. The file is preserved as `references/build-98297.config` and contains:

- `build-name = B98297`
- `root = 4cf56214095f863b31776277c55a8fbf`
- `build-replay-hash = 417671b923a5ca0bad0f5bec63c2a68e`

R2 uses those root/hash values and updates header build/base/data numbers plus ten player-version records to 98297. These are configuration-derived values; no original 98297 replay has been inspected. This removes the explicit 98285 target from the converted replay, but does not prove that the client will avoid every offline replay transition.

### Lobby initialization hypothesis

The migrated lobby had `m_amm = true` but `m_ammId = null`. The original user-provided 98285 Braxis reference has `m_ammId = 50001`, and all fifteen other game-option values match the migrated lobby exactly. R2 supplies that observed ID and changes no other game option.

This is a specific initialization repair hypothesis, not proof that the missing ID caused the null-pointer crash. The crash log has no resolved function names identifying the missing object.

### Native MPQ-v4 update

The prior custom writer removed HET/BET tables and raw-chunk protection while rebuilding classic tables. R2 instead edits a copy of the immutable 41810 archive through native StormLib. It retains **HET, BET and the original 16384-byte raw-chunk setting**, updates the native tables and preserves the replay user-data allocation. The original-format control has not yet been tested by the user, so the earlier container transformation has not been proven to be the crash cause.

Only `replay.initData` and `replay.game.events` are replaced inside the archive. Player commands, timing, Dragon Shire map/dependency identifiers, messages, tracker and other replay member payloads are preserved. The JSONL audit records **26 metadata changes** relative to the prior 98285 candidate.

## Verification completed

- CI run **36526607713** completed successfully at code commit `b840de2117e743f11f05d520604e927a488fc1b1`.
- **75 tests passed**, no failures or skips: 17 startup tests plus the existing 58 reference/binding/reproduction/diagnostic/control tests.
- Native StormLib wrote the candidate and read all **14 archive members**. All expected payloads matched.
- The independent mpyq reader matched those payloads.
- Pinned Blizzard schema 96477 decoded the complete header, lobby, details and event streams; re-encoding matched the observed payloads.
- Event counts remain **104257 game, 155 message, 6614 tracker**. Message/tracker bytes are unchanged.
- Two native generations in CI are byte-identical. Two separate local generations are also byte-identical and match the CI candidate SHA-256.
- All **22 Base64 parts** reconstruct the same binary.
- Local execution used the exact native libraries saved by CI; the 17 startup tests also passed locally without skips.

The first workflow attempt failed while copying a native library from an assumed path. Installed package paths are now discovered rather than guessed. A subsequent generation hit the published mpyq runtime's missing `close()` method; cleanup now closes its file handle. These failed runs are not counted as successful candidate verification.

## Remaining limits

No HotS executable has loaded or played R2 in this environment. The exact full 98297 schema has not been established; successful observed-payload validation uses the official pinned 96477 schema. Old map dependencies, opaque synchronization members, numerical gameplay catalogs and 2016 simulation rules remain unresolved compatibility risks. Copying valid metadata does not independently port those rules.

The bounded depot probe failed to resolve the tested depot hosts. It did not establish that map dependency files are globally unavailable. No unverified map dependency was transplanted from Braxis.

The immediate next client test is the new **98297 STARTUP_R2** TEN_GREYMANE file. If it fails, preserve the new executable build, exact replay filename, game loop and crash signature to distinguish it from the known 98285 failure.

## Preservation

R2 was uploaded under its distinct name to the existing OneDrive project folder and the user's Multiplayer replay folder. Raw donor contents, private crash memory, account details and local absolute paths were not added to public Git. The source-history bundle generated by the successful CI includes the complete history through the R2 publication commit; later session/progress documents are preserved separately in the dated delivery package.
