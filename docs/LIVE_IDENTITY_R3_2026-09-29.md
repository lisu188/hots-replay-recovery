# Native R3: match the client actually launched at 08:11

## New observation

The user's screenshot selects `TEN_GREYMANE_client98297_STARTUP_R2_EXPERIMENTAL` and shows `Old 2.57.0.98297`. The watch buttons look inactive. This screenshot is not evidence of successful playback or of a new R2 crash.

The newer OneDrive Graphics log, local time **2026-09-29 08:11:46.680**, identifies **2.57.0.98285**, executable Base98285 and data B98285. It has ordinary `-sso=1 -launch -uid heroes` parameters and Battle.net as the grandparent process. This is a new ordinary client launch, not the earlier replay-switch process at 06:30. The 06:28 live launch really was 98297, but it is no longer the newest observed launch. The logs do not establish why the launched version changed or prove a global Blizzard rollback.

The allowlisted observation is `observations/live-client-2026-09-29-081146.json`. Its source log SHA-256 is `737b3fefc164d72d608b9f22b5f04232933e213a147e3baa65b228d417dda20e`. Raw paths, account names and session identifiers are not published. The screenshot's Old label is consistent with a version mismatch, but the exact internal UI predicate and the inactive-button cause have not been established.

## Deliverable

`TEN_GREYMANE_client98285_NATIVE_R3_EXPERIMENTAL.StormReplay`

- SHA-256: `20a11a37fb365a17511ad27a8f7d7ebafd11c69f630794108f9d92b9675406b5`.
- Size: 1228709 bytes.
- Public checkpoint: `client-checkpoints/98285-native-r3/`.
- Publication commit: `2caa8e3c681b6f32b3f7b3c2c93964fc37a14051`.
- Actual client playback, removal of the Old label and resolution of the crash: **not yet validated**.

This is not the previously crashed 98285 candidate. R3 combines the client identity of the original 98285 Braxis reference with the native MPQ-v4 format and lobby initialization hypothesis introduced in R2.

The original private Braxis replay was re-inspected locally in full using the preserved pinned Blizzard schema 96477. Its SHA-256 and complete reference profile exactly match the previously committed profile. The original has root `b5114c16bd78f1844ab9fe97cbd9c305` and a sixteen-byte zero replay compatibility hash. R3 copies this observed identity rather than substituting the different root/hash from the 98297 build configuration. A zero hash is an observed field value, not a proven bypass of the engine's compatibility checks.

R3 retains HET/BET tables, 16384-byte raw chunks, the original Dragon Shire match and R2's `m_ammId=50001` hypothesis. The R2 lobby bytes are unchanged. Only client identity in the header and player-version records is changed relative to R2. The raw game stream differs from R2 in **20 bytes**, and exactly matches the preserved 98285 command stream's SHA-256. There are 24 recorded metadata changes. Messages, tracker, map identifiers, commands and opaque replay data are preserved; legacy simulation compatibility remains unresolved.

## Validation

- 21 new unit tests passed locally, with no skips.
- CI **36531011897**, tested code commit `4b8d1eac889aed427f7b458a7a8379627d66d54c`, passed **96 tests**, no failures or skips.
- Native StormLib wrote the archive and read all 14 members; independent mpyq extraction agreed.
- Pinned official schema 96477 decoded and re-encoded the header, lobby, details and every observed event stream exactly.
- Counts remain 104257 game, 155 message and 6614 tracker events.
- Two independent CI generations are byte-identical and match the locally generated candidate.
- All 22 Base64 parts reconstruct the same file.
- CI uses the existing public reference profile, not the private original donor bytes.

`repair_live_identity.py` validates the observed version against the known donor. `latest_observation` selects by timestamp rather than the greatest numeric build, rejects contradictory same-time observations and separates an ordinary Battle.net launch from a replay-switch launch. Synthetic regression tests cover a newer launch with a lower build number.

## Next client check

Open **NATIVE_R3**, not the first 98285 experiment or 98297 STARTUP_R2. Record whether the Old label is gone, whether Watch Solo is available and whether the map and match clock actually start. Any later crash must be correlated with this exact filename and the new process build; the old 06:30 crash cannot be reused as proof that R3 failed.

The candidate has been saved under a distinct filename in the user's OneDrive Multiplayer folder. Originals and prior experiments are unchanged. The dated backup preserves the successful CI Git bundle through the publication commit, plus this session's later documentation and progress snapshot. Private raw crash memory and the original Braxis match are not added to public Git.
