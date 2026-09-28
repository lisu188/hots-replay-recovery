# Independently verified protocol 96477 checkpoint

Date: 2026-09-28. This is an experimental protocol conversion, not certified in-game playback.

## Completed and pushed

The successful GitHub Actions run is `36469342880`, using code commit `768d2bfc499ccc9f5d49257622b165cb8379293d` and Blizzard/heroprotocol commit `9af3ea7150f1a8acb53464c92519a9bbcc7a3594`.

| Target protocol | Published commit | Binary size |
| --- | --- | ---: |
| 44256 | b03c609c4ae5e457a033b47b28e25ecde6486e98 | 670435 bytes |
| 57547 | b3b5e15a3cc136e2803fe1d405f78cab9586cf2d | 670431 bytes |
| 96477 | 161e3d2b5be3e1b139b3a5d045bcc7469a57602e | 670387 bytes |

Each target was migrated directly from the preserved original 41810 replay to avoid accumulating intermediate conversion errors. Each successful checkpoint was immediately committed and pushed to main.

SHA-256 of the 96477 binary:

`1fd94e209a4fd28f2f3582d7901db891c5bcb0333af06efd6391d96ff8da3205`

## Validation performed

- 16 unit/regression tests passed; zero failures and zero skips in CI.
- Local schemas for 41810, 43905 and 44256 equal the pinned official Blizzard schemas.
- The official Blizzard decoder read every generated game, message and tracker event and matched the converter's results.
- All three checkpoints retain 104257 game events, 155 message events and 6614 tracker events. No events were dropped.
- mpyq and native StormLib independently read all 14 archive members and returned the expected bytes.
- Rebuilt MPQ v4 header/table MD5, archive sizes and non-overlapping ranges validated.
- Available per-member CRC32/MD5 validated. The original listfile's omitted MD5 slot is explicitly recorded; its CRC32 and known original content digest are independently checked.
- Base64 parts reconstruct the exact replay bytes and match the SHA-256 sidecars.
- The downloaded CI archive SHA-256 was checked before extraction. The Git bundle was cloned and passed `git bundle verify`; it contains complete history through checkpoint commit 161e3d2.

Target 96477 has 4569 changed game events and zero changed message/tracker events. It has 4793 semantic audit entries. Added fields, removed empty legacy fields, the dialog-mouse transformation, target version fields and control-vector representation changes are explicitly recorded in `checkpoints/96477/semantic-audit.jsonl` and `game.changes.jsonl`.

## Storage

Git contains only text Base64 parts for replay binaries, plus JSON/JSONL, SHA-256 sidecars, code and documentation. The existing OneDrive folder `HotS Replay Upgrade - TEN_GREYMANE` now contains all three generated protocol checkpoints and the verified Git bundle through 161e3d2. `progress.json` records the actual state. The full CI archive includes logs, reports, binary outputs and the bundle.

## Target client evidence

A game log read from the user's OneDrive confirms that their installation ran Heroes of the Storm **2.55.17.98025**, executable Base98025 and data build B98025 on **2026-09-19**. Sanitized relevant facts are recorded in `references/client-98025.json`. This is observed installation evidence, not an assertion that it remains the latest global release.

## What is not yet proven

No HotS executable was run against any generated checkpoint. In particular, 96477 is the highest independently validated protocol output, not a confirmed upgrade to the user's 98025 engine.

The source dataBuildNum, root key, version tuple and opaque synchronization/resumable/battlelobby members remain original. The newer compatibility-hash field currently carries the source hash bytes, explicitly marked unverified. Control-vector narrowing preserves a documented representation but does not establish equivalent engine catalog behavior. Ability identifiers, flags, talents and map/hero simulation rules may require further mapping.

The next engineering boundary is authentic build-98025 replay metadata and schema verification, followed by real client loading and deterministic playback/desynchronization checks. Merely replacing the build number or disabling integrity checks is not completion.
