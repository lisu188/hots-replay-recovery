# Checkpoint 43905

Status: protocol migration generated and round-trip validated; client playback not yet validated.

## Why 43905

Build 43905 is a useful compatibility checkpoint because the historical HotsApi tooling reports it as its minimum supported replay build, and it sits immediately after the small protocol changes already analyzed from the 41810 source.

## Semantic changes from 41810

The Git projection confirms that only intended semantic fields changed:

1. Header:
   - `m_version.m_build`: 41810 -> 43905
   - `m_version.m_baseBuild`: 41810 -> 43905
   - `m_dataBuildNum`: 41810 -> 43905
2. Init data:
   - adds `m_ammId: null` to game options because the 43905 protocol added this optional field.
3. Game events:
   - exactly 10 `SUserOptionsEvent` rows update `m_baseBuildNum` and `m_buildNum` from 41810 to 43905.
4. No gameplay command payload, position, target, selection, talent, tracker event or message event changes semantically.

The 4558 `SCmdEvent` records are compatible with the build-43905 24-bit `m_cmdFlags`; no source event uses the bit removed after build 42590.

## Binary implementation

The converter patches the existing MPQ rather than rebuilding it from scratch, preserving every unknown/opaque replay file and every original MPQ offset.

Changed blocks:

- `replay.initData`: re-encoded using the 43905 bitpacked schema and compressed with zlib.
- `replay.game.events`: re-encoded using the 43905 bitpacked schema and compressed with BZip2.
- MPQ encrypted block table: updated only for the new archived sizes.
- MPQ user-data replay header: replaced in-place; encoded length remains 119 bytes.

The original file allocation has sufficient room for both changed blocks, so all subsequent MPQ blocks and tables stay at the original locations.

Generated replay SHA-256:

`31fb7fb755b174588fa54a93ef50ebaac9b37103101c60fade4b37e54dadd048`

Generated file size remains `635140` bytes because the original MPQ layout and allocation are retained.

## Validation

The generated binary was reopened through the MPQ parser and decoded with the target 43905 protocol.

Validated:

- header equality against intended migrated header
- initData equality against intended migrated initData
- all 104257 game events equality against intended migrated game events
- game event count unchanged
- message and tracker streams remain unchanged

A complete semantic export is stored in `decoded/43905/` for Git diff review.

## Remaining blockers before calling this playable

This checkpoint deliberately does not fake information that is not yet known:

- `ngdpRootKey` still points to the original 41810 game data.
- `fixedFileHash` still points to the original 41810 data.
- major/minor/revision version fields still retain the source values until an authentic replay from build 43905 is used as metadata reference.
- `replay.sync.events`, `replay.server.battlelobby`, `replay.resumable.events` and other opaque streams are byte-for-byte source data.

Therefore this checkpoint proves protocol-level conversion and a valid MPQ/replay structure. It does not yet prove that a build-43905 HotS executable can deterministically run the match with 43905 game data.
