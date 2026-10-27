# Original41810 to native R8 game migration audit

`audit_native_game_fidelity.py` now checks the complete original-to-R8 game-event
migration against the native value codec. It reconstructs the entire existing
R8 game member from original41810 values and an explicit description of the
existing recipe. All104,257 events agree, and the native value writer reproduces
the exact1,148,436-byte R8 member. No unexplained payload differences were found.

This is recipe accounting, not proof that the recipe's assumptions preserve
historical game behavior. The audit exposes a noninjective command-flag mapping
that must remain visible before any full-upgrade claim.

The latest human instruction remains **Keep all work offline**. No network,
Computer Use, game, remote publication, new replay or synchronization write
occurred. Reconstruction bytes existed in RAM and are not returned by the API.
Original/R8 file identity, size, modification time and full SHA-256 remain
unchanged. The existing R8 still declares98285.

## Whole-stream accounting

The independent old side uses the pinned Blizzard41810 schema and decoder.
The candidate side uses `native_game_events.py`, profile
`game-events-98348-observed22`, with no upstream payload fallback. Pinned
protocol96477 names project the already-bound native positional fields to
common names; they do not supply missing values or prove native RTTI names.
The schemas are read again as AST literals to avoid relying on mutable module
tables. Whole-member SHA-256 pins restrict the audit to the exact original and
R8 game streams.

Every event retains its order, time delta, userid and numeric ID. All payload
differences are accounted for by the following existing rules:

| Existing recipe operation | Checked count |
| --- | ---: |
| User-options build/base-build41810 to98285 | 20 fields across10 events |
| Add assumed-absent command `m_vector=None` | 4,558 |
| Experimental command-flag replacements | 3,247 |
| Unit-tag references checked | 15,346 |
| Unit-tag values repacked from18 to22 recycle bits | 15,301 |
| Old MouseButton to MouseEvent, assuming zero modifier flags | 1 |

The unit-tag rule preserves recorded index and recycle components and sentinel
values. It does not authenticate current runtime instance allocation. Source
command targets, abilities, sequences, points, camera values, text and every
other field remain untouched by this recipe. Strict comparison with every
native-decoded R8 payload and byte-exact native reserialization check that no
additional change slipped into the actual member.

The actual sources are fixed by their existing complete replay SHA-256 pins:

- Original41810: `e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824`.
- R8: `4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19`.

The raw game member pins are respectively
`ea69dd77edd02f3ed2c42a2def1faab6dc4d0eb46da291c44f76bfb49a65eed6`
and `31df2ab80eeeb56bc543ea0744f75d4d2ec6a5c337b1f38f04ef90d169dab2f0`.
Upstream schemas/decoder and native-codec dependencies retain their separate
source pins in the receipt. No raw player text or complete events are exported.

## Flag collision and the remaining semantic boundary

The existing R7 rule, inherited by R8, produces this collision:

| Original flags | R8 flags | Commands | Existing operation |
| --- | --- | ---: | --- |
| `0x100100` | `0x80100` | 606 | Experimental bit-deletion mapping |
| `0x80100` | `0x80100` | 16 | Left unchanged because its predicted value was absent from the two reviewed references |

Thus **622 commands share R8 flags `0x80100` while originating from two distinct
flag values**. The flags alone have no unique inverse. Recovering their original
distinction requires the preserved source or per-event audit; the source is
still available and unchanged. This is an observed property of the existing
recipe, not a new flag edit or proof that the two historical meanings were
different. Other event fields may matter, and their semantic role is unproved.

The16-command rule, original/current flag-bit meanings, absent command vectors
and zero mouse modifier assumption remain unauthenticated as historical
semantics. The documented unobserved hypothesis value `0x40100` has not been
enabled or written. This audit does not identify the cause of a runtime desync.
It establishes exactly what R8 changed and which semantic questions remain.

## API and validation

```python
from audit_native_game_fidelity import audit_game_fidelity

report = audit_game_fidelity(original_game_member, R8_game_member)
assert report['recipe_accounting_passed']
assert not report['assumptions_authenticated_as_historical_semantics']
```

The API returns aggregate facts, change counts and numeric command-flag pairs.
It requires the project's pinned Blizzard/heroprotocol dependency. It rejects
different inputs, schema/decoder pins, extra/missing projected fields, changed
event mapping, unexplained native values or unequal reconstructed member bytes.
It never returns an upgraded replay or a semantic-compatibility approval.

Eight new focused tests check unit-tag overflow/sentinels/component preservation,
the flag collision, source immutability, explicit mouse/build assumptions,
strict projection and exact input admission. The neighboring16 native-codec
tests also pass. The new CI gate uses already-restored original/R8 fixtures and
asserts both exact reconstruction and the explicit622-command collision. Its
Python block parses locally; no hosted CI or full local corpus run is claimed.

Receipts:

- `observations/native-game-fidelity-2026-10-27.json`
- `observations/native-game-fidelity-differences-2026-10-27.json`
- `observations/native-game-fidelity-local-validation-2026-10-27.json`

Full upgrade and current-client playback remain false. Missing lobby/player
state, historical catalog/ability rules, ownership and deterministic
synchronization are separate outstanding requirements. This stage changes no
conversion rule and creates no successor replay checkpoint.
