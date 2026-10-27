# Native owner-event publication to the tracker stream writer

The owner-change constructor's virtual publication call now has a concrete
selected receiver, handler and writer invocation. With the initial manager
table retained, it synchronously forwards the event pointer to `132AC50` for
the same tracker substate that the record-start path opens. This closes the
selected constructor-to-stream-writer **invocation** gap. Successful numeric
serialization, archive flush and actual on-disk persistence remain unobserved.

## Receiver and initial dispatch

The original global at `2F825F8` contains `50C23112`; XOR with the factory's
key initially yields null. A bounded RIP-relative MOV/LEA recognizer found
1,584 raw candidate matches, including overlapping encodings. Its store
candidate at `1329907` was qualified inside complete function `13297D0`.
This scan is not exhaustive alias/write coverage.

After the selected status comparison with `20020000`, `13297D0` takes object
address `387C290`, calls constructor `13237D0`, XOR-encodes that pointer with
`50C23112`, and stores it at `2F825F8`. The constructor installs primary table
`27BC518`, initializes its enabled byte `+1BC` to zero, and constructs the
container at `+1D940`. These are selected initialization-code bindings; actual
startup reach, mode and later object/table replacement are not observed.

Three exact original table cells provide the selected callbacks:

| Slot | Target | Selected role |
| --- | --- | --- |
| `180` | `132FE70` | Owner-event publication handler |
| `288` | `133C5B0` | Record-start callback |
| `298` | `132B7F0` | Read enabled byte at receiver `+1BC` |

The owner-event factory `1342E30` decodes the same global and, after its
previously documented unit and enabled gates, calls slot `180` with its stack
event record. Under the same valid receiver and retained table, that call
selects `132FE70`. The record remains live during this synchronous call path.

## Publication gates and shared state

`132FE70` saves entry `RDX` as the event pointer in `RDI` and receiver `RCX`
in `RBX`. It calls enabled slot `298` again. A zero result skips the writer.
Otherwise it performs atomic32-bit increment of receiver `+1C0` and calls the
writer only when the previous counter value was zero. The old value returned
by XADD is incremented and compared with1. Other entries skip the write, and
the normally returning enabled path decrements the counter afterward.

At `132FEAB`, arguments are:

```text
RCX = manager + 1E630
RDX = the unchanged incoming event pointer
call 132AC50
```

The record-start callback `133C5B0` calls `134E7F0`, then `134E890`, with
manager `+1D940`. On the selected zero return from `134E890`, it writes1 to
manager `+1BC` at `133C614`. The writer-mode member call at `134F04B` passes
container `+CF0` and `R9B=1` to `134E510`, using the atom-derived tracker name.
The identity arithmetic is exact:

```text
manager + 1D940 + CF0 = manager + 1E630
```

Original filename `replay.tracker.events` at `27BDEA0` is interned into atom
`393E240`. The selected stream-opening path builds its name from that atom
and opens the tracker substate. It creates the typed writer and stores the
pointer at tracker-state `+1A8`. Name/string helpers are ordinary-return and
name-preservation conditions; archive finalization is not audited here.

The previously qualified downstream route is reused and byte-checked:
`132AC50 -> 135E870 -> table slot8=133FDF0 -> 1A75E30 -> 1A75240`.
It supplies root957 and event `+30` to the generic writer. The prior named
field proof still maps event `+38/+39` to `m_controlPlayerId/m_upkeepPlayerId`
without numeric renumbering. No user-ID equivalence is inferred.

## Status and allocation caveat

The member helper saves the stream-opening result in `ESI`. After a zero
result it attempts a 296-byte (`0x128`) typed-writer allocation. If that allocation
returns null, `134E614` stores null at state `+1A8`, yet `134E66F` returns the
earlier stream-opening status. Thus **status0 and enabled byte1 do not prove
that a usable writer exists**. The successful route requires a nonnull,
stable writer as an explicit condition. No actual allocation failure was
observed, and this is not attributed to any earlier client exit.

The selected native writer also invokes encoders without using every returned
status as a success gate. Invoking the writer is therefore not proof that a
whole event was successfully serialized. Sufficient output capacity or a
successful refill, plus the prior numeric-writer success conditions, remain
necessary. Nothing here demonstrates that memory/stream output was flushed
into a persistent replay archive.

## Validation and limits

Sixteen qualified ranges total **9,439 bytes / 1,972 instructions**. Fourteen
complete original RuntimeFunction/CHAININFO unions and two bounded no-call
leaves supply the extents; no table bytes are treated as instructions.
All54 selected byte/call/reference checks, nine nonvolatile-register
definition/use checks and four required guard edges pass. Three exact original
vptr cells bind the selected virtual dispatch. The null-allocation branch
reaches the earlier-status return without the nonnull writer store.

Whole original PE and transformed text hashes were freshly rechecked, together
with original/R8/current replay and unused-launcher pins. The earlier owner
field/encoding receipt is pinned unchanged; its768 synthetic decoder cases are
retained as earlier evidence and were not rerun. This milestone adds local
static analysis, not unit tests, a full corpus run, hosted CI or peer review.

Code comes from the pinned transformed-text artifact; original PE metadata and
data supply extents, pointer cells and initial global bytes. Derived code is
not an unchanged signed executable or a live capture. No native execution or
REA native-provider analysis was performed. The REA skill's evidence and
unsupported-provider boundaries were followed using ordinary shell tools.

The conditional route requires selected initialization, retained vptr/global,
the same receiver in record-start and publication, live enabled/nonreentrant
state, successful writer allocation, stable schema/object/handles, valid
disjoint storage and ordinary x64 ABI/helpers. Exception, reentry/concurrent
or alias mutation, later replacement and failed output paths are not covered.
Actual event emission, active mode, serialization success and archive
persistence remain unobserved. Initial Born/Init ownership producers and
historical41810/effective talent rules remain separate gaps.

All work stays offline. No game, Battle.net, Computer Use, network, remote
refresh or publication occurred. Production conversion, original/R8/current
replays and sync data are unchanged. Full upgrade and playback remain false.
Next authenticate initial ownership/setup production and actual context before
any safe player or talent migration; archive flush is a separate proof step.

Addresses, numeric offsets and status codes above are hexadecimal; descriptive
byte counts and the stated atomic counter values are decimal. The allocation
literal `0x128` is shown explicitly.
