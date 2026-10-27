# Native tracker ownership fields and numeric encoding

The previously qualified event3 constructor copies its incoming owner byte to
event object `+38`. The generic serializer now binds that byte to the named
wire field **`m_controlPlayerId`**, under the selected factory/serializer and
normally initialized context conditions. Object `+39` corresponds to
`m_upkeepPlayerId`. Both values are serialized numerically unchanged; the
selected paths introduce no player-number adjustment. No actual replay event
emission, live owner value or persistent publication is demonstrated.

## Native field layout

Initializer `1D08A0` supplies context `393EB80`, program `27C6960` of length
`35B0`, accessor table `27BECB0` and `F95` QWORDS to `1A77DB0`. The constructor
stores the program at context `+8` and accessor table at context `+18`.
Original PE program bytes equal the whole pinned 13,744-byte stripped program.
This authenticates the selected initializer's arguments; startup reach and
the live registry contents remain unobserved.

Descriptor `1A6D070` selects accessor data using
`tableBase + 8 * QWORD[tableBase + 8*(typeID+1)]` for a nonzero index.
For root957, original slot `27C0AA0` contains relative index3433, selecting
original record `27C57F8`. Its five QWORDS are **12, 0, 4, 8, 9**. The first
QWORD is retained without assigning it a new semantic role. The STRUCT getter
`1A6D670` takes field offsets from the following QWORDS.

| Tag | Native child / scalar | Payload offset | Event object offset | Named wire field |
| --- | --- | --- | --- | --- |
| 0 | USER958 / uint32 type3 | `0` | `30` | `m_unitTagIndex` |
| 1 | USER959 / uint32 type3 | `4` | `34` | `m_unitTagRecycle` |
| 2 | USER960 / uint4 type158 | `8` | `38` | `m_controlPlayerId` |
| 3 | USER961 / uint4 type158 | `9` | `39` | `m_upkeepPlayerId` |

Addresses and offsets in this report are hexadecimal; type IDs, counts and
relative indices are decimal unless shown as code offsets. Original type3 and
type158 accessor entries supply scalar widths4 and1 bytes respectively. USER
entries958..961 have zero accessor indices; the USER serializer recursively
uses each declared child with the **same input pointer**.

The STRUCT serializer `1A75240` uses the root957 declaration's implicit tags
0..3, child types958..961 and field count4. It obtains each native offset through
`1A6D670`, adds it to the input payload pointer and recursively writes the child.
The previously qualified adapter supplies event object `+30` as that pointer.
Pinned official event3 has the same tags and scalar declarations, providing
the field names in the table. This supersedes the previous checkpoint's
per-field offset gap for this selected payload and serializer path.

## Numeric value preservation

The INT path passes its accessor width and payload pointer to leaf `1A79110`.
For the unsigned scalar declarations it zero-initializes the result and assembles
the little-endian input bytes. It checks the extracted value against the
declaration's bounds, then passes the value directly to `1A75EF0`. No declared
minimum or player index offset is added. For the two ownership fields, the
declared range is0..15 and width1 byte.

`1A75EF0` encodes a nonnegative integer with first byte `(value & 63) << 1`,
sign bit0, then successive seven-bit groups and continuation bit128. Therefore
the larger encoded byte value is an encoding detail, not a different player
identifier. The successful selected path decodes back to the original value.
Output exhaustion or unsuccessful refill is outside that success condition.

The factory connection remains the previously audited `9BC21E -> 1342E30`:
its selected saved owner byte reaches event `+38`, and the same input is used
by the selected unit `+44` store. This establishes that incoming owner argument
as the selected `m_controlPlayerId` value. It does not prove that a later talent
callback observes the same value after arbitrary subsequent state changes.
Factory `R8B` similarly reaches `m_upkeepPlayerId`; the caller selects saved
unit `+5E` or the incoming owner according to its previously documented predicate.

## Validation and remaining scope

Eighteen newly qualified ranges total **4,662 bytes / 1,321 instructions**.
Twelve original RuntimeFunction/CHAININFO unions supply code extents, with the
generic writer's64-byte switch table separated from instructions. Six leaves
have no RuntimeFunction record and include every branch-reachable RET path.
All16 transformed kind-table targets are instruction boundaries. The table
differs from the corresponding original PE span; derived table bytes are not
presented as unchanged original bytes or as a runtime capture.

All56 selected byte/call/reference checks, six register definition/use checks
and three required kind-dispatch edges pass. Original accessor records and
metadata declarations were freshly checked, as were whole PE/transformed-text
and source/R8/current replay and unused-launcher pins.

A bounded **data-only projection** used the audited offsets, scalar extraction
and positive integer encoding. All256 control/upkeep pairs0..15 were combined
with three uint32 pairs: `(0,0)`, `(1,4194303)`, `(4294967295,4294967295)`.
The unchanged pinned official VersionedDecoder class algorithms decoded all768
payloads to the expected named values and consumed the exact bytes. Four pinned
class ASTs were loaded with two bounded Python3 byte primitives for the absent
six dependency. This is a synthetic compatibility check, **not native code
execution, a fresh replay decode, or current-client playback**.

The earlier conditions remain: normally initialized and stable registry,
original accessor/program bindings, selected transformed code/tables, ordinary
x64 ABI and helper returns, valid disjoint storage, stable identity, and no
exception/reentry/alias/concurrent mutation. The constructor's virtual publisher
has not been bound to the persistent file writer. Initial unit Born/Init
producers and all owner callers are not included. No live state is captured.

Do not infer `userId == owner`, `userId + 1`, a universal player namespace,
or historical41810 rules from this bridge. No safe talent remap is established.
The next offline boundary is the concrete publication sink and initial
ownership/setup producers, followed by actual context and effective/historical
talent rules. The original replay, R8, current control and sync bytes remain
unchanged. No production conversion or unit tests changed, and no hosted CI,
independent peer review, REA native-provider analysis, game, Computer Use,
network or publication occurred. Full upgrade and playback remain false.
