# Dragon Shire mercenary capture

MercCapture is a 2,197,794-byte derivative of SignedAnnouncer. Two independent StormLib builds produced SHA-256 `54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a`. MapScript.galaxy has SHA-256 `38bde241c87da5760d7cfa7341e19613d063f51f11458ebcfd361e572fc18059`. All 69 other content members matched the parent byte for byte.

The team-owned camp beacon precedes the capture statistic by one loop. All 13 TEN captures and 26 captures in three held-out build-41810 replays returned the beacon to neutral 16 loops after the statistic. All 246 captures in 14 retail recordings took 48 loops. MercCapture routes only the two mercenary team branches of the ownership callback through SignedAnnouncer’s existing signed-index capture worker. The stock startup call still waits 48 loops. The callback registers on the existing trigger slot at the original registration point.

At the capture loop the icon transfer, flag transfer and capture statistic occupy three adjacent tracker frames in that order. All 41 captures in five historical recordings kept personal owners off the flags until the next capture of the same camp or match end. All 260 captures in 15 retail recordings assigned the sconce to one personal owner exactly eight loops after the statistic. Every capture had a complete eight-loop observation window. The physical flag evidence and the reset evidence use different cohorts.

The retail credit routine chooses a player with RandomInt, records the capturing player, then requests a cosmetic banner. The overlay preserves that draw, bookkeeping, reward logic, half-second wait and both actor messages. At resume it skips only the delayed UnitSetOwner for one of the five authored flag objects when createTextTag is false. The two other stock MapMechanics callers request text tags. Other units and text-tag-producing calls follow the ordinary path.

The map uses the stock banner trigger slot if a scoped call acquires it first. If another caller has already installed the stock worker, ordinary requests can still use it. The first legacy request in that case allocates one additional trigger. Replay ownership records do not establish who acquired that slot first, which historical player earned the credit or the state of the historical random generator.

The compiled test takes both actual team callbacks into the signed worker and suspends each on a separate stack. Both beacons return to neutral at +16; a simultaneously outstanding ordinary startup request returns at +48, with one shared capture handle. Further tests cover the no-action, unknown-index and neutral branches, empty and populated credit groups, banner resumption at +8, ordinary units, text tags and the prebound fallback. The test uses extracted Galaxy routines translated by inclusion in a C harness with mocked engine services. Native Galaxy compilation and match playback remain unverified.

```sh
python build_merc_capture_map.py SIGNED_MAP GAMELIB MAPMECHANICS capture-reset-holdouts.json merc-flag-capture-observations.json shared_beacon_harness.c merc_capture_harness.c NEW_OUTPUT --stormlib STORMLIB
python merc_capture_tracker.py ORIGINAL_TEN NEW_OUTPUT MAPMECHANICS --private-dir NEW_PRIVATE_DIRECTORY
```

The tracker adapter derives ten fixed opening generations from the candidate and maps the 13 source capture statistics to 39 ownership frames. The dynamic camp icons require a separately verified target allocation. The 39 projected payloads match the original physical bytes at their enclosing deltas. The sparse output is 821 bytes.
