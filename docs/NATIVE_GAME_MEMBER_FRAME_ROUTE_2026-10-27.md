# Native game-member route and frame envelopes

Local static analysis now connects `replay.game.events` to the sequential
game-event reader in the installed 98348 binary. A metadata-driven model checks
every frame envelope in R8 and one current control. This narrows the remaining
game-stream work to other payload bindings and native bit-reader behavior;
historical conversion and playback remain unproved.

The user's latest instruction is **Keep all work offline**. This stage used
local files and the already installed GNU objdump 2.42 through WSL. It made no
network requests, launched no game, used no Computer Use, and published nothing
remotely. The configured IDA sessions belong to another target and were left
alone. No REA Evidence or fresh IDA result is claimed.

## Static route

Source authority is the original 53,573,840-byte PE, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Decoded instructions come from the separate analyst-transformed text patch,
36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
This patch is not unchanged signed PE text or a runtime capture.

All addresses below are RVAs unless explicitly identified as VAs.

| Link | Selected evidence |
| --- | --- |
| Exact filename | Original `.rdata` at `27BDE40`: `replay.game.events` and its NUL terminator |
| String initializer | `1D02B0` passes that string to `280150` with destination `393EA20` |
| Member-selection path | `134F770` constructs the name view from `393EA20/24/28`, then calls `2F32C0` at `134F864` for the game state at entry object + `498`, stream + `8` |
| Successful selection/allocation | `134F89E` calls constructor `134B8F0` with the same stream address; `134F8A8` stores its result at game state + `1A0` |
| Reader object | Constructor stores its incoming stream pointer at reader + `20`, after the base bit-reader initialization |
| Shared caller | `1330CC0` calls `134F770` with object + `50C58`, then `13266B0` with object + `510F0`; `50C58 + 498 = 510F0` |
| Sequential frame reader | `13266B0` uses game state + `1A0`, reads native root 50, then 890, then calls ID/payload reader `1352350` |
| Sequential frame writer | `132A9B0` writes roots 50 and 890, then calls ID/payload writer `1354850` |

These are conditional static data-flow bindings: normal calling convention,
valid objects/callbacks, completed string initialization, successful member
selection and allocation. No live object identity or callback lifetime was
observed. The full archive implementation was not audited here.

The sequential reader spans four original RuntimeFunction records. Three have
CHAININFO pointing to entry record `[13266B0,13266DA)`. The verified union is
`[13266B0,132684E)`: 414 bytes, 119 instructions, with all direct noncall branch
targets at decoded instruction starts. This avoids treating the first
fragment `[13266DA,1326840)` as a whole function. Seven selected, nonoverlapping
code ranges total 2,481 bytes and 600 instructions, each checked against the
pinned transformed text. Failed exploratory clipping at `2F3380` is excluded;
the final attach helper uses its exact original record ending at `2F33B2`.

A separate reader `135EB50` and writer `135F070` serialize a counted event
container, with a four-byte count preceding the frames. They have different
owners and are not the sequential member reader above. Do not prepend their
count to the raw `replay.game.events` member.

## Frame types and actual checks

Original DWORD slots `27C9FA8` and `27C9F28` supply roots **50** and **890**.
The previously bound ID reader/writer supplies root **138**. All use native
context VA `14393EB80`, the stripped 1,192-record program, not the separate
Battlenet registry. The complete closure of these roots is 12 records.

- Root 50 is a two-bit CHOICE, tags 0..3, carrying unsigned 6/14/22/32-bit
  delta values. The writer selects tags at `40`, `4000`, and `400000` thresholds.
- Root 890 is a one-field STRUCT; its child 891 has five physical bits and a
  declared allowed range of 0..16. Value 16 was observed; no additional player
  semantics are inferred.
- Root 138 is the seven-bit event enum with 90 admitted tags.

The three declared physical graphs match pinned Blizzard protocol96477 after
erasing USER aliases. Native bounds and enum membership are checked separately;
physical equality does not equate their acceptance policies.

| Read-only case | Event frames | Frame bits compared and inverted in RAM | ID27 command payloads |
| --- | ---: | ---: | ---: |
| R8 partial, still declares 98285 | 104,257 | 2,085,148 | 4,558 |
| Current 98348 control | 144,708 | 2,894,160 | 26,899 |
| Total | **248,965** | **4,979,308** | **31,457** |

Every frame's delta choice/value, userid, event ID and exact bit positions
matched the pinned upstream decoder. An independently implemented local bit
cursor was used for the model. Inverting the observed frame fields in RAM
preserved whole-member byte identity, including untouched payload/padding
bytes. There were zero checked native metadata violations or nonminimal delta
tags under the selected writer thresholds. Only delta tags 0 and 1 occurred;
tags 2 and 3 have static graph evidence without actual-case coverage.

The model also freshly checked the previously bound ID27 payloads. IDs23/25
were absent. **Every other payload still uses upstream96477**, even on the
model side. Thus this is not a complete native game-stream decoder. The local
cursor follows the bit convention established by pinned Blizzard source; the
native machine-code bit reader has not independently authenticated that
convention. Native execution, deterministic historical semantics and current
client playback remain separate requirements.

R8 and the current control retained file identity, size, modification time and
SHA-256 across the probe. Original/R8 hashes are rechecked in the final local
checkpoint. No replay, archive member or synchronization value was written.
The latest replay remains the existing R8; both full-upgrade flags remain false.

Receipts:

- `observations/native-game-member-frame-route-2026-10-27.json`
- `observations/native-game-frame-type-closure-2026-10-27.json`
- `observations/native-game-frame-actual-comparison-2026-10-27.json`

The private reproducible drivers, bounded objdump outputs and readback checks
remain in the existing workspace. Raw native code and replay contents are not
included in this source milestone. No full local regression corpus or peer
review was run for these documentation/evidence changes; the focused checks
above are the validation performed.
