# Protocol migration roadmap: 44256 -> 96477

Generated from direct comparisons against Blizzard/heroprotocol.

## Verified schema checkpoints

| Build | Meaningful change for this replay |
|---:|---|
| 44256 | Baseline after first full structural re-encode. SCmdEvent has 26-bit flags and optional m_vector. |
| 45815 | m_cmdFlags narrows 26 -> 25 bits; SPlayerAnnounceMessage gains m_announceLink. This replay has no SPlayerAnnounceMessage and its command flags fit in 24 bits. |
| 49582 | Replay header field changes from m_fixedFileHash to m_replayCompatibilityHash. Lobby slot schema removes m_licenses. Type IDs shift. |
| 51978 | User/lobby data gains banner, spray, announcer pack and voice line fields. Selection delta representation is compacted. Tracker gains hero banned/picked/swapped events. |
| 52561 | Lobby slots gain hero mastery tiers. |
| 55929 | SGameUserLeaveEvent m_leaveReason widens from 4 to 5 bits. |
| 57547 | Dialog MouseButton value becomes MouseEvent {m_button, m_metaKeyFlags}. This replay contains exactly one old MouseButton event with value 1; map to button=1, metaKeyFlags=0. |
| 59279 | m_allowedControls shrinks from 8-bit length to 4-bit length. Old replay has value (255, all ones), meaning all controls allowed; map semantically to (15, all ones). m_maxControls changes from 8-bit to 4-bit representation. |
| 59837 | m_cmdFlags widens 26 -> 27 bits. |
| 61718 | Lobby slot gains m_hasVoiceSilencePenalty. |
| 62548 | m_cmdFlags narrows 27 -> 26 bits. Source values remain in range. |
| 65579 | Legacy m_artifacts field disappears from lobby slots. |
| 66977 | Lobby slot gains m_isBlizzardStaff. |
| 68406 | Adds SDynamicButtonSwapEvent and shifts later type IDs. |
| 69947 | Lobby slot gains m_hasActiveBoost. |
| 85027 | Game description gains m_isRandomTestValue and m_disabledHeroList; type IDs shift. |
| 96477 | Same normalized protocol schema as 85027. |

## Verified source-data limits

- SCmdEvent count: 4558.
- Maximum source m_cmdFlags observed: 2,097,408.
- Source never uses the removed high flag bit at earlier narrowing points.
- SelectionDelta source uses at most:
  - subgroup index: 1
  - subgroup count: 2
  - added unit tags: 2
  - mask length: 3
- Dialog-control events: 313 total.
  - 312 have None eventData.
  - 1 has old MouseButton value 1.
- Source replay has no SPlayerAnnounceMessage events.

## Header compatibility caveat

Starting at build 49582, the replay header uses m_replayCompatibilityHash instead of m_fixedFileHash.

The semantic/event protocol can be transcoded through 96477, but a real HotS client may still reject or desync unless the correct build-specific game-data identifiers are supplied:

- m_ngdpRootKey
- m_dataBuildNum
- m_replayCompatibilityHash

Do not mark a replay as playback-valid merely because encode/decode round-trip succeeds.

## Validation rule

At every generated checkpoint:

1. Encode all changed streams with the target protocol.
2. Decode the generated MPQ with the same target protocol.
3. Compare event count and semantic values.
4. Preserve untouched MPQ members byte-for-byte.
5. Record SHA-256.
6. Commit/push immediately.
7. Save the binary checkpoint and Git bundle to OneDrive.
