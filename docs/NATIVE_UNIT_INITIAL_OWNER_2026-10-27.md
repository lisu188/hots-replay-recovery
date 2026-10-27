# Initial unit ownership, Born/Init producers and recorded identifiers

Both selected native unit-creation event producers read the same owner fields
used by the previously qualified setter/talent-selector paths. `SUnitBornEvent`
and `SUnitInitEvent` copy unit `+44` to named `m_controlPlayerId` and unit `+5E`
to `m_upkeepPlayerId`, without numeric adjustment. Their unit key comes from
unit handle `DWORD+10`. This is a conditional static bridge; actual client
objects and later talent-callback values remain unobserved.

## Construction and branch selection

Initializer `9BAEF0` reads `BYTE[creation_input+10] & 1F` at `9BB052/057` and
stores it to unit `+44` at `9BB05A`. It reloads the same source byte, masks it
again, and writes unit `+5E` at `9BB062`. Under disjoint unit/input storage and
a stable input across those few instructions, both selected stores receive the
same value. Earlier helpers already ran; this is not an entry-time snapshot.
This assignment admits0..31 and must not be silently narrowed to0..15.

Later in that same initializer, within earlier gates, unit `+38` bit08 selects
the producer:

| Bit08 | Call site | Target | Header/event ID |
| --- | --- | --- | --- |
| Set | `9BB9B7` | `1342A50` | `50006` / UnitInit6 |
| Clear | `9BB9C6` | `1342270` | `50001` / UnitBorn1 |

Both calls pass the same initialized unit pointer. The Born branch first
calls helper `A16B80`. The effect of that helper and other intervening helpers
on owner fields is not closed. Therefore the bridge does **not** assert that
the early creation byte remains unchanged until the later event. Each producer
reads the unit fields at its own load time.

## Exact payload fields and unit identity

Born and Init keep distinct native payload roots933 and970, respectively.
Their original root slots are `27C9F3C` and `27C9F54`. Each declares seven
ordered tags0..6. Their separate original offset tables `27C5630` and
`27C58E0` contain QWORDS `552,0,4,8,544,545,546,547` in decimal. Only the
field offsets after the first QWORD are used here; no new semantic role is
assigned to that first value.

| Named field | Payload offset | Event object offset | Native source |
| --- | --- | --- | --- |
| `m_unitTagIndex` | `0` | `30` | Unit handle upper10 bits |
| `m_unitTagRecycle` | `4` | `34` | Unit handle lower22 bits |
| `m_controlPlayerId` | `220` | `250` | Byte at unit `+44` |
| `m_upkeepPlayerId` | `221` | `251` | Byte at unit `+5E` |

Both original vptr slot8 adapters (`133FA70`, `133FD10`) pass their own root
and event `+30` to the previously qualified generic writer. The owner fields
are transparent USER wrappers of unsigned type158, range0..15, width1 byte.
The selected native scalar declarations match the corresponding official
tracker fields. Unit key fields are USER wrappers of unsigned32-bit type3.
This names those four scalar fields; it does not prove the whole payload
codec or the unit-type-name field's semantics.

The producers use a stack record at `RSP+20`. Their frame equations put
`RBP+170/+171` at event `+250/+251`, exactly the metadata offsets. Direct byte
copies preserve the values read from unit `+44/+5E`; there is no four-bit
truncation or player-number addition/subtraction in the producer. The generic
serializer's declared0..15 bounds remain a separate check from the initializer's
five-bit input mask.

The unit-key formula is:

```text
m_unitTagIndex   = DWORD[unit+10] >> 22
m_unitTagRecycle = DWORD[unit+10] & 3FFFFF
```

Born reads the high part earlier than the low part, with helpers between the
reads. A stable handle is required to treat them as one key. Init recomputes
both from one later read. Both producers also require unit `+41` bit0 clear
and the decoded manager's enabled callback. They publish through the previously
qualified manager slot180, retaining all nonnull-writer, counter, output-capacity
and persistence qualifications from that checkpoint.

## Fresh bounded tracker observations

The original, R8 and current-control tracker members were freshly decompressed
and decoded, with whole replay and tracker hashes checked and exact byte
consumption. No names, unit keys or raw replay members are published here.
Only numeric aggregate identities are retained.

| File | Tracker events | Born | Init | OwnerChange | Initial owner IDs without player setup |
| --- | ---: | ---: | ---: | ---: | --- |
| Original41810 | 6,614 | 2,802 | 0 | 279 | 0,11,12,15 |
| R8 partial | 6,614 | 2,802 | 0 | 279 | 0,11,12,15 |
| Current98348 control | 6,181 | 2,498 | 0 | 136 | 0,11,12 |

R8's tracker bytes equal the original exactly, so these are **two independent
tracker contents**, not three independent observations. R8 was decoded with
the original41810 content grammar because of that byte equality; this does
not validate its declared98285 container or current-client playback. The
current control uses the already pinned official96477 declaration for its
tracker contents. Offline decoding does not establish current-client execution.

Every Born/Init/OwnerChange owner value in these files is within0..15. All
observed Born control/upkeep pairs are equal. Every OwnerChange unit key had
a preceding Born/Init record, and no initial key was duplicated. This checks
those finite recorded associations, not runtime pool identity, current liveness
at every change, or subsequent talent callback selection.

The observed owner namespace contains IDs without a `SPlayerSetupEvent` player
entry. Do not infer a universal owner-to-human-player mapping or `user+1`,
drop those IDs, assign them an unproved semantic role, or infer that source
ID15 is unsupported merely because it is absent from this current control.
Neither independent tracker contains Init6, so the Init branch has static
evidence only and **no observed fixture coverage** here.

## Verification and remaining work

Seven qualified code ranges total **6,079 bytes / 1,431 instructions**. Three
original RuntimeFunction/CHAININFO intervals supply code extents with four
64-byte RVA tables and three alignment bytes kept separate. Four no-call
leaves cover two record constructors and two writer adapters. All64 switch
targets are instruction boundaries. Derived table bytes are pinned transformed
text, not described as unchanged original PE data or runtime captures.

All55 selected byte/call/reference checks,12 nonvolatile-register definition/use
checks and six required branch edges pass. Original PE, transformed text,
schema/accessor records and original/R8/current/unused-launcher pins pass.
Pinned unchanged official decoder class algorithms were loaded with two bounded
Python3 six byte primitives; the tracked local MPQ reader was verified against
HEAD and hashed. This adds fresh offline tracker decoding and static evidence,
not native execution, a full corpus, new unit tests, hosted CI or peer review.

Ordinary x64 ABI/helper returns, valid disjoint storage, stable schema/global/
vptr/unit identity and no uncontrolled exception/reentry/concurrent/alias change
remain conditions. Valid decoded link/name context and successful serializer
paths are required. Initial store equality is scoped to those stores; neither
value persistence across intervening helpers nor an actual live owner snapshot
is proved. Full unit-type-name behavior, actual talent-callback unit/owner
selection, effective/historical41810 talent rules, successful stream output and
archive flush remain separate work.

All work remains offline. No game, Battle.net, Computer Use, network, remote
refresh or publication occurred. Production conversion, replay and sync bytes
are unchanged. Full upgrade/playback remains false. Next bind the relevant
player/unit/talent context through its actual producer/consumer path, preserving
explicit setup mappings and the non-setup owner IDs before any migration.

Addresses and offsets above are hexadecimal. Type IDs, event IDs, table QWORDS,
counts, numeric domains and bit counts are decimal unless explicitly shown as
hexadecimal masks or header literals.
