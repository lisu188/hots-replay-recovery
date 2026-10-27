# Native event-ID dispatcher and selected command payload

Native enum 138 is now tied to a concrete typed reader/writer pair and allocation
table in the installed 98348 analysis image. Its116-entry table has 90 active
entries, exactly matching the enum's 90 tags. The selected ID 27 object tables lead
to native payload root 291. That root's declared physical graph matches the
pinned Blizzard 96477 `SCmdEvent` payload graph.

An offline model using the bound native payload graph read **4,558 command
payloads from unchanged R8** and **26,899 from the genuine 98348 control**. All
31,457 payloads matched the upstream decoder's values and bit spans; none
violated the checked native metadata scalar, enum or array constraints. This
check found no declared physical-layout mismatch in those R8 command payloads.
It does not establish their gameplay semantics or solve a replay desync.

## Typed ID and dispatch binding

The [binding observation](../observations/native-game-event-138-dispatch-binding-2026-10-27.json)
uses RVAs relative to image base `0x140000000`. Code addresses and member/vtable offsets below are hexadecimal; event/type IDs and counts are decimal:

| Location | Selected observation |
| --- | --- |
| `.rdata` slot `27C9FAC` | Original PE DWORD is 138. It follows the known delta-type slot `27C9FA8`. |
| Reader `1352350`, load `1352374` | Supplies that type index, context VA `14393EB80`, a local result address and the stream to helper `1A713D0` at `135238A`. |
| `1352397..13523B6` | Reads the local result, rejects unsigned values above 115, then dispatches through the 116-u32-RVA table at `1353A78`. |
| Writer wrapper `1354850` | Reads WORD `[entry argument2+10]`, passes its local u32 representation with type 138/context `14393EB80` to `1A6F5E0`, then invokes object vtable slot `20`. |
| Reader common path `1353A04..1353A1B` | Passes the allocated pointer through helper `1351AC0`, loads the pointer from the output cell, then invokes its primary vtable slot `28`. |

All 116 table entries are decoded instruction starts. The 90 nondefault entries
exactly equal the authenticated native enum tags; the 26 holes select default
`1353A52`. The selected code `[1352350,1353A78)` is 5928 bytes / 1309 instructions.
The separate 464-byte table `[1353A78,1353C48)` is not counted as instructions.
All selected direct noncall branch targets stay within the decoded code. This
is a selected normal-flow check, not a proof of every callback, exception path
or engine execution.

The original `.rdata` inventory found 16 aligned DWORD values equal to 138. Four
raw RIP patterns referred to one of those slots. Decoding qualifies two genuine
loads; the other two raw matches start inside their REX-prefixed instructions.
This search covers the inventoried aligned data and selected RIP opcode forms,
not every possible way a type index could be supplied by code.

## Selected payload tables and shapes

| Numeric ID | Name in pinned Blizzard 96477 table | Constructed primary vptr RVA | Native root | Upstream root |
| --- | --- | --- | ---: | ---: |
|23|`NNet.Game.SLoadGameDoneEvent`|`26652D0`|274|80|
|25|`NNet.Game.SCommandManagerResetEvent`|`2657BD8`|287|86|
|27|`NNet.Game.SCmdEvent`|`2657C78`|291|100|

Both selected virtual methods for each table supply the same payload type slot
and native context: slot 20 calls `1A6F5E0`, and slot 28 calls `1A713D0`. The command
read method at `6D20D0` supplies object `+30` as its payload destination. Native
root 291 has seven declared members. The selected normalized graphs for all three
roots match their upstream payload graphs.

The [50-type closure](../observations/native-game-payload-type-closure-2026-10-27.json)
contains enum 138 and the three payload roots with all their transitive children.
It belongs to the 1192-record native context `14393EB80`, separately from the
8330-record Battlenet registry. Native type/field names remain unauthenticated;
the names above are explicit upstream wire-ID correspondences, not recovered
native RTTI names.

The pointer helper stores its saved entry RDX through saved entry RCX at
`1351AF6`, after two conditional virtual callbacks. This analysis retains normal
calling-convention/valid-object assumptions. It does not establish every alias,
callback effect, runtime vptr or object lifetime. The table bindings describe
the selected constructed tables and their observed methods, rather than a live
receiver observation.

## Actual payload comparison and scope

The [actual comparison](../observations/native-game-payloads-actual-comparison-2026-10-27.json)
traversed 104,257 R8 events and 144,708 current-control events. It substituted a
native-metadata-driven payload reader only for selected IDs 23, 25 and 27. IDs 23 and 25
were absent in both recordings, so their validation here is a declared-graph
comparison only. The observed payload counts all belong to ID 27:

| Input | Command payloads | Payload bits | First/last recorded command loop |
| --- | ---: | ---: | --- |
| Partial R8, declared 98285 |4558|760152|61 /19526|
| Genuine 98348 control |26899|4030668|656 /19356|

The native model visited 704,255 nodes. It checked actual scalar/enum membership
and array bounds without clamping or rewriting values. No raw field values were
saved in the observation. Frame delta/user-ID fields and unrelated payloads
still use pinned upstream 96477 definitions. Both models use Blizzard's pinned
bit reader. This is not an independent native bit-reader implementation,
all-native whole-stream decoder, native archive-filename binding, or runtime
acceptance proof.

The declared-graph comparison erases USER wrappers, keeps STRUCT member order
and CHOICE tags, and compares physical integer minimum/bit width. It does not
equate native enum membership/maxima with upstream validation policy. STRING
or unknown kinds are not silently treated as BLOB. All three selected physical
graphs match under those explicit rules; the actual probe separately checks
the encountered metadata constraints.

## Provenance, verification and remaining work

The source 98348 PE is 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Code decoding uses the analyst-derived transformed patch, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
The native program is 13,744 bytes, SHA-256
`245aba71f1702e6bae480924df478c8479978e54c383dff4757eb40863932b2f`.
Unaltered original PE text and runtime memory are not claimed.

Ordinary local GNU objdump was used, with no REA Evidence claim or new IDA/Ghidra
import. Across the dispatcher, writer wrapper, six payload methods and pointer
helper, **6374 selected code bytes / 1422 instructions** matched the source patch
exactly. Selected table/branch, pointer, type-slot, graph and actual-payload
assertions passed. There was no independent peer review or full local unit
corpus run in this observational stage.

All work remained offline under the latest human instruction. No game launch,
Computer Use, new network call, remote-state refresh, GitHub push or OneDrive
upload occurred. Original/R8 files and synchronization data remain unchanged.
No new decoder policy, guessed field value, replay checkpoint or flag rewrite
is introduced. The persistent full-upgrade objective is incomplete.

The next static boundary is the containing archive/frame reader and its native
envelope, followed by other observed payload types. Current command layout
alone does not authenticate historical resources, catalog identities, object
allocation, command-flag meaning or deterministic engine state. Native playback
and the first actual mismatch frame/comparison remain unobserved in this stage.
