# R4 mod-data mismatch: diagnosis and dependency audit

Date: 2026-09-29.

## What the user actually observed

The latest screenshot reports: `The mod data loaded does not match the mod data which was originally used to play this game.` It does not show a filename. The separately refreshed OneDrive `Variables.txt`, modified at 07:12:48 UTC, records `TEN_GREYMANE_client98285_CONTROLS_R4_EXPERIMENTAL.StormReplay` as the last replay. The ordinary Battle.net launch log at 09:12:00.656 local time identifies executable and data build 98285. Together these observations associate this rejection with the R4 test without reusing the unrelated 06:30 crash.

This is not successful playback. The more specific error directs investigation to mod-data consistency; it does not prove which internal check rejected the file, that every earlier problem is fixed, or that the mask change alone caused the different message. No new crash was established by the screenshot or the searched logs.

## Measured replay expectations

| File | Declared build | Map | Map checksum | Mod checksum | Dependencies |
|---|---:|---|---:|---:|---:|
| Immutable TEN_GREYMANE | 41810 | Dragon Shire | 759447839 | 3522231966 | 5 |
| CONTROLS_R4 | 98285 | Dragon Shire | 759447839 | 3522231966 | 5 |
| Private original Braxis reference | 98285 | Braxis Holdout | 1716172187 | 3849009070 | 8 |
| Private original 2024-11-05 Dragon Shire | 93054 | Dragon Shire | 4181095002 | 1605882721 | 6 |
| Private original 2024-11-05 Battlefield of Eternity | 93054 | Battlefield of Eternity | 3195662605 | 2230041899 | 7 |

These are the values serialized in `m_mapFileSyncChecksum` and `m_modFileSyncChecksum`, not independently computed engine checksums of the currently loaded files. Full observed header, details, initData and game/message/tracker payload decode/re-encode completed for all five inputs. The source uses preserved schema 41810; the later files use pinned Blizzard schema 96477. This is observed-payload validation, not proof of the complete 98285 schema.

The R4 dependency list and battlelobby prefix remain identical to the 2016 original. Changing client identity and lobby masks did not port the underlying map and game data.

The two genuine build-93054 replays have different mod checksums despite sharing a client build. This disproves treating the checksum as one universal constant per build. The comparison does not isolate map name as the only cause: dependency sets and match configuration can also differ. Therefore copying Braxis's checksum into Dragon Shire is not an evidence-backed repair. Likewise the 2024 Dragon Shire reference is not current-build data.

## Implemented in this session

`mod_data_audit.py` now decodes the structured dependency prefix of `replay.server.battlelobby`: bounded path and aligned 40-byte handle arrays. It requires a byte-exact prefix round-trip and checks ordered agreement with both `replay.initData` and `replay.details`. For source and R4 the prefix is 861 bytes. The remaining battlelobby tail is explicitly opaque and has not been transcoded.

The exported profile contains only replay/schema digests, map/build identity, dependency handles, relative cache paths, expected checksums and stream hashes. It omits player identities and absolute private paths.

The comparison rejects wrong-map, wrong-dimension, wrong-version, wrong-data-build and wrong-root references as prerequisites for further work. A filename heuristic flags known experiment names; it is not cryptographic authentication of a donor. Passing these guards never approves a checksum transplant or claims simulation compatibility.

CLI examples:

```sh
python mod_data_audit.py inspect current-dragon.StormReplay --schema-build 96477 --expected-build 98285 --output work/current-dragon-profile.json
python mod_data_audit.py compare work/r4-profile.json work/current-dragon-profile.json --output work/dependency-comparison.json
```

## Validation and publication

- 19 new tests plus 12 existing dependency-audit tests passed locally: 31 passed, no failures or skips.
- GitHub Actions run `36536707581` completed successfully at code commit `0da20dad7899c16cb36f663efa4ab491abde8af8`, also with 31 passed and no skips.
- CI uses Blizzard/heroprotocol pinned at `9af3ea7150f1a8acb53464c92519a9bbcc7a3594` and audits the hash-bound public R4 input. It receives no private donor bytes.
- Downloaded CI code hashes match the local code; its R4 data profile matches local measurements except the filename-based experiment marker, because CI restored the input under the neutral name `r4.StormReplay`.
- Three actual private references were inspected locally and independently re-inspected to match the saved profiles. Their raw files are not published.
- The verified CI Git bundle contains complete source history through the tested commit. Later observation, documentation and progress snapshots are included separately in the dated backup package.

## Remaining requirement

No R5 replay was generated in this session: an arbitrary checksum replacement would conceal a discrepancy rather than establish compatible game data.

The next concrete input is an original Dragon Shire replay recorded by the currently running client, or an equivalent verified map/dependency extraction plus a reproducible engine checksum calculation. A custom Dragon Shire game with bots can provide a useful same-map sample, but its game-mode dependencies must still be compared; it is not automatically an interchangeable Quick Match reference. The sampled OneDrive results did not contain a Dragon Shire replay from build 98285. This does not claim an exhaustive search of every local or cloud file.

A current same-map reference enables further dependency and synchronization investigation. It does not guarantee that the preserved 2016 commands, numeric ability catalogs and changed game rules will simulate identically. Actual client opening and complete playback remain unvalidated.
