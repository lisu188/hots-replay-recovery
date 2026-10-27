# Native owner argument to tracker record construction

The selected current-client owner mutation now has an authentic event-record
producer: `9BC080` calls `1342E30` at `9BC21E`. The saved owner byte passed to
that factory is also the value written to unit offset `44` by `9BC530`, which
the previously qualified talent callback reads as its first selector. The
factory copies that byte unchanged to **event object offset `38`**. This closes
the selected owner-to-record construction edge under the conditions below.
It does not yet establish equality with a named wire player identifier.

## Selected data flow

| Stage | Checked binding |
| --- | --- |
| Mutation input | Entry `DL` saved at entry `RSP+10`; the frame equation makes this `RBP+248` |
| Call arguments | `9BC210` reads the saved owner into `EDX`; `9BC217` passes the unit in `RCX`; `9BC21E` directly calls `1342E30` |
| Factory value | `1342E47` saves entry `DL` in `EBP`; `1342EDD` copies `BPL` to factory `RSP+58`, equal to event object `+38` |
| Second byte | Entry `R8B` is saved in `ESI` and copied at `1342EE2` to event `+39`; the caller selects saved unit `+5E` or the saved owner according to `R15B` |
| Record identity | Header `50003` at object `+10`, primary table `27BD320`; the event-ID reader selects the same header and table for ID3 |
| Handle fields | Unit `DWORD+10 >> 22` goes to object `+30`; its low22 bits go to object `+34` |
| State writer | `132AC50` writes the delta using root50, then calls `135E870` |
| Event writer | `135E870` serializes the header low word using root898 and calls original table slot `+8` |
| Payload adapter | Slot `+8` is the leaf `133FDF0`; it passes root957 and event `+30` to `1A75E30`, which calls `1A75240` |
| Payload reader | The same table's slot `+30` is leaf `133F310`; it passes root957 and event `+30` to `1A772C0` |

Addresses and numeric offsets are hexadecimal unless explicitly described as
decimal. No addition or subtraction is introduced by the selected owner-byte
copy. This result applies to that copy; the generic field walker has not been
audited for the memory-field-to-wire-field relationship.

The constructor is conditional. Unit byte `41` bit0 must be clear, and virtual
call slot `298` must return a nonzero `AL`. Both required edges dominate the
selected owner store. It publishes the stack record through virtual slot `180`;
the concrete callee and its route to persistent tracker output remain unbound.
The record is not shown to have been emitted during actual gameplay.

## Member route and declared protocol

Original filename `replay.tracker.events` at `27BDEA0` is interned through
`280150` into global `393E240`. The complete archive-opening path `134F770`
passes that atom, archive owner `+8`, mode0 and destination container `+CF0` to
`134E510` at `134FB0C`. The container transfer `13252C0` calls `131CC20` for
the tracker substate. That transfer reads delta root50 and event/payload
through `135E4E0`, then sends selected records to `132AC50`. These selected
read/write paths do not by themselves bind the constructor's virtual publisher
to the file writer.

The original root slots are 898 for tracker IDs, 957 for this payload and50 for
the delta. The separately pinned stripped program declares root957 as ordered
tags0,1,2,3: two variable uint32 values followed by two variable unsigned values
with bounds0..15. The seven-record closure was freshly compared with the pinned
program, and the official protocol declaration was refreshed from its pinned
local source. Official ID3 is `NNet.Replay.Tracker.SUnitOwnerChangeEvent`, whose
ordered fields are `m_unitTagIndex`, `m_unitTagRecycle`, `m_controlPlayerId`,
and `m_upkeepPlayerId`. ID and ordered field shapes correspond. Native runtime
field offsets have not yet been tied to those individual named fields.

Consequently, **do not infer `userId == owner`, `userId + 1`, `owner + 1`, or
that event byte38 is already proven to serialize as `m_controlPlayerId`**.
The native owner default16 and the selected setter/selector bounds0..15 retain
their earlier documented scope. No neutral/unowned semantic label is added.

## Evidence and validation

Thirteen code ranges total **7,268 bytes / 1,706 instructions**. Original PE
RuntimeFunction/CHAININFO metadata qualifies eleven full unions, with the
reader's trailing data separated from its code. Two no-RuntimeFunction leaves
end at their direct tail jumps; following alignment is excluded. The tracker
ID table has15 entries /60 bytes, with all15 targets on instruction boundaries.
The table bytes come from the pinned transformed text and differ from the
same original PE span. They are not described as unchanged original PE data.

All67 selected byte/call/reference checks, four definition/use and nonvolatile
register-preservation checks, and two required constructor-edge checks pass.
Source PE and transformed text whole-file hashes were freshly rechecked. The
original/R8/current replay and unused launcher whole-file pins also pass.
This is local static validation; no new unit tests, full corpus, native target
execution, REA native-provider analysis, hosted CI or peer review was performed.

The native PE is53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
The transformed text is36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
It is a derived code artifact, not an unchanged signed PE or runtime capture.
The two dated observation files retain exact range and check receipts without
publishing the replay or executable.

Normal x64 ABI and normally returning helpers/virtual calls, valid disjoint
object/input/stack storage, stable handles/keys and selected tables, and no
exception/reentry/concurrent/alias mutation remain conditions. Final persistent
unit state, actual owner values and a full purchase/dispatch execution remain
unproved. The earlier post-store alias caveat is retained.

All work remains offline. No game, Battle.net, Computer Use, network, remote
refresh or publication occurred. Production conversion, replay and sync data
are unchanged. Full upgrade and playback remain false. The next bounded step
is to audit the root957 generic field layout and constructor publication sink,
then connect actual ownership/setup values and effective/historical41810 talent
rules before any safe migration.
