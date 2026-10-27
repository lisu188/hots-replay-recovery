# Native98348 game-event codec for the observed payload set

`native_game_events.py` now decodes and serializes the complete
`replay.game.events` members from R8 and one current control without an upstream
payload fallback. The pinned profile supports the 22 payload IDs observed
across those recordings, using a complete 191-type native closure. This replaces
the prior stage's upstream decoding of non-command payloads for these cases.
It does not establish historical simulation compatibility or current playback.

The latest human instruction remains **Keep all work offline**. This stage used
the original installed PE, the existing transformed-text patch, local objdump
through WSL, Python and Git. No network, Computer Use, game, remote publication,
new replay/archive member or synchronization write occurred. Encoded members
and the synthetic mutation existed only in RAM. Existing launcher drafts and
the original/R8 checkpoints remain untouched.

## API and contracts

```python
from native_game_events import iter_game_events, encode_game_events

canonical = encode_game_events(
    decoded.event for decoded in iter_game_events(member_bytes))
assert canonical == member_bytes  # Check explicitly for each source.
```

The only profile is `game-events-98348-observed22`. `iter_game_events` yields a
`DecodedGameEvent` containing a `GameEvent`, observed delta tag, frame start,
payload end, aligned end and discarded-padding counters. Consume the iterator
to exhaustion to validate a whole member. A `GameEvent` supplies delta, userid,
numeric event ID and anonymous payload. STRUCT/ARRAY values are tuples, STRING
values are bytes, BIT_ARRAY is `(length, pattern)`, and CHOICE uses `Choice`.
Representations suppress payload values; diagnostics contain fixed reasons,
type IDs and positions. Native field names and memory layouts are not inferred.

The encoder chooses the native writer's minimal delta tag and zeroes alignment
padding. Readers accept and count discarded nonzero padding and nonminimal
delta encodings. Thus canonical writing need not preserve arbitrary source
bytes. There is no source-preserving API and no retained-source shortcut.

The facade pins its schema and the existing native STRING sequence validator,
executes exactly the checked validator buffer, limits input/output to 4 MiB,
and bounds event/node/depth/array work. It checks exact value types, native
integer/count bounds, enum and CHOICE membership, string byte/sequence limits,
and shape. An admitted enum ID without a bound payload is an explicit error.
The other 68 native payload IDs are not enabled by guessing or upstream fallback.

## Native binding and physical types

The source PE is 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Selected instruction bytes match the separate 36,581,376-byte analyst-transformed
patch, SHA-256 `3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
The patch is not unchanged signed PE text or runtime evidence.

The previously qualified reader `1352350` dispatches to constructed objects'
primary vtable slot `28`; writer `1354850` uses slot `20`. For all 22 cases,
the constructed primary vptr was followed to both methods. Ten constructors
are separate linear leaf routines; the other cases construct inline. All 44
payload methods are exactly 43 bytes/10 instructions. Each supplies one root
from the original PE and context VA `14393EB80` to `1A713D0` or `1A6F5E0`.
The wrappers preserve the fifth/context argument; the selected sequential frame
route supplies zero. The graph uses declaration-order STRUCT fields.

These are conditional static bindings, assuming successful allocation, normal
calling convention, valid callbacks and initialized metadata. Runtime vptr
identity, lifetime, accessor aliases and native execution remain unobserved.
The methods total 1,892 bytes/440 instructions; selected leaf constructors add
611 bytes/150 instructions. The prior dispatch code/table and archive/frame
route are retained as separate evidence. No new REA Evidence or IDA run is claimed.

| Event ID | Native payload root | Event ID | Native payload root |
| ---: | ---: | ---: | ---: |
| 5 | 243 | 55 | 409 |
| 7 | 225 | 56 | 425 |
| 27 | 291 | 62 | 486 |
| 28 | 303 | 64 | 490 |
| 32 | 349 | 66 | 492 |
| 36 | 360 | 98 | 523 |
| 39 | 374 | 101 | 532 |
| 46 | 441 | 103 | 547 |
| 47 | 444 | 104 | 551 |
| 48 | 448 | 105 | 555 |
| 49 | 450 | 110 | 564 |

Frame roots remain 50/890/138. All payload and frame references close over 191
records and 11 kinds. All 22 physical payload graphs agree with pinned Blizzard
protocol96477 after the authenticated STRING rule and BIT_ARRAY spelling are
handled explicitly. An initial conservative comparison left four such shapes
uninterpreted; those were not proven wire-format mismatches.

For STRING, the same-context descriptor getter `1A6D310` adds two to the encoded
byte-count width and multiplies its maximum by four. Aligned bytes additionally
must satisfy the native non-NUL Unicode-scalar sequence grammar and the original
character-count bounds. Pinned prior static evidence authenticates that rule;
this stage does not silently equate native STRING policy with upstream `_blob`.
BIT_ARRAY retains its native count bounds separately from upstream bit width.

## Actual integration and independent writer check

| Read-only case | Whole game member | Events | Compared native value nodes |
| --- | ---: | ---: | ---: |
| Existing R8, still declares98285 | 1,148,436 bytes | 104,257 | 1,878,960 |
| Current98348 control | 1,916,341 bytes | 144,708 | 2,566,894 |
| Total | | **248,965** | **4,445,854** |

Every frame and payload value and exact event bit span agrees with the pinned
upstream decoder. The model side imports no upstream decoder or payload schema.
Both complete members encode from their supplied values byte-for-byte. Both
observe 20 payload IDs, with a union of22, and all11 supported kinds. All observed
native bounds/membership/string checks passed. All discarded padding was zero;
only delta tags0/1 occurred in the recordings. Synthetic tests cover tags2/3.

A separate current-control mutation changes the first ID110 single-u32 payload
by XOR1 in RAM. Exactly one bit changes, inside that payload. The pinned upstream
decoder independently compares all144,708 events: the intended value changes,
all other values and event bit positions remain identical. This is a synthetic
writer check, not a proposed gameplay edit. Neither bytes nor raw values are saved.

Sixteen focused unit tests pass, covering known wire vectors, all delta width
boundaries, native userid16/17, enum holes, unbound admitted IDs, truncation,
canonical padding, NULL/CHOICE/BIT_ARRAY domains, UTF8/NUL/sequence limits,
oversize strings before scanning, exact types, fixed profiles and work budgets.
The existing offline workflow discovers these tests and now includes whole
current-control native game-member reproduction. Its edited Python block parses;
the workflow has not run for this local-only commit. No full local regression
corpus or independent peer review is claimed.

## Original41810 boundary

The original game member is **not identical to R8**: 1,146,911 bytes, SHA-256
`ea69dd77edd02f3ed2c42a2def1faab6dc4d0eb46da291c44f76bfb49a65eed6`.
R8 has 1,148,436 bytes, SHA-256
`31df2ab80eeeb56bc543ea0744f75d4d2ec6a5c337b1f38f04ef90d169dab2f0`.
Their first different byte is at offset37. Do not inherit R8's result for the
unmodified original or count an extra original traversal as passed.

Direct application of the new profile accepts23 model frames before reporting
an unbound ID at bit4420. Independent comparison with the locally pinned
official41810 schema shows the earlier cause: **zero-based event22, ID28
SSelectionDeltaEvent**, beginning at bit4312. The old payload ends at4438 and
aligns to4440; the current-layout model ends at4387 and aligns to4392. The first22
frames have equal values and positions. The SelectionDelta graphs contain
multiple old nine-bit counts/indices where the current native graph uses five
or six bits. The later apparent unknown ID follows this misalignment; it is not
evidence of an authentic unsupported historical event.

This diagnoses a concrete old/current wire boundary. Existing R8 already has a
different game member that passes the current model. It does not certify that
all old values, catalogs, abilities, resource ownership, missing ClientInfo fields
or deterministic synchronization were migrated correctly. Original/R8/control
identities and hashes remain unchanged. The latest replay remains R8 and both
full-upgrade flags remain false.

Machine receipts are the five dated `observations/native-game-*` files for
observed payload bindings, whole members, RAM mutation, original boundary and
focused tests. The schema itself is `native_game_events_schema_98348.json`.
