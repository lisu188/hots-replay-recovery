# Unit catalog binding and selection insertion gates

The selected lookup's context slot `+2A0` is now bound to catalog index 83,
the original literal **Unit**, and the original descriptor
**GameData/UnitData.xml**. The constructor reserves pointer arrays but writes
their logical entry counts to zero during creation. Its reserved space is
therefore insufficient evidence for accepting the replay's unit links.
The prior conditional singleton model remains conditional; no effective
catalog, runtime unit, safe migration or playback result is established.

## Exact context and metadata relationship

Complete original function `31E890..31EF7E` constructs a context and iterates
over 92 catalog positions. The manager slot address is:

```text
context + 8 + 8*catalog_index
```

At index 83 this is `context+2A0`, exactly the slot read by `5E1B70` and
`201A490`. The loop writes the catalog index to the new manager's word `+2`.
The original name-table row at `2F32350` points to the four-byte literal Unit
at `264D860`. The original descriptor row at `2F33A08` points to the
21-byte literal GameData/UnitData.xml at `2652230`. Row and literal hashes
are recorded separately. These names are original binary metadata, not
analyst labels inferred from a hero name.

The descriptor call at `31EB61 -> 1609450` receives the corresponding
24-byte descriptor row. Its result is stored at the parallel context slot:

```text
context + 8 + 8*catalog_index + 2E8
index 83: context+588
```

The newly allocated Unit manager reloads this same slot and stores its value
at manager `+30`, subject to stable-slot and ordinary-helper conditions.
The receiver of the descriptor call is `QWORD[context+2E8]+28`, with R8D=0.
The called body and a complete effective resource-load operation are not
audited here. The pointer relationship and XML descriptor are not evidence
that a particular XML content set was loaded, merged or assigned link IDs.

The selected constructor returns its incoming context pointer in RAX.
A separate byte-qualified 15-byte caller window at `3216C0..3216CF` calls
the constructor, copies RAX through RBX, and writes the same pointer to
global `3388B18`. This is a conditional call/return/publication relationship,
not a complete caller CFG or proof that this initialization ran.
That global is in a PE virtual section without source-file-backed bytes;
reading the static image or an IDA zero-filled area cannot capture its
actual live pointer or populated tables.

## Logical counts and reservation

For each non-null new catalog-manager allocation, the constructor requests
`110` bytes, writes the header and allocates pointer storage through calls
requesting `2000` bytes. It uses these distinct fields:

| Purpose | First unit-link lookup | Second definition lookup |
| --- | --- | --- |
| logical count directly initialized | `+90 = 0` | `+38 = 0` |
| initial reserved-slot field | `+98 = 400` | `+40 = 400` |
| pointer-array field | `+A0` | `+48` |
| requested pointer storage | `2000` bytes | `2000` bytes |

Here `400` is 1024 slots and `2000` is 8192 bytes, matching eight-byte
pointer entries. The selected consumers compare against the logical count,
not the reserved-slot field:

```text
5E1B70:  uint16(unitLink) < DWORD[manager+90]
201A490: uint16(definitionKey) < DWORD[manager+38]
```

The latter then reads a real slot and applies its null/tagged-slot/object
gates. `202D910` rejects a zero masked resolved reference. The constructor's
manager header word `0101` is not substituted for the independently resolved
definition object's byte-0 gate.

The zero count is scoped to the direct creation stores before first manager
publication. The first iteration has RSI=0 from the initial zero/normal
three-count-loop exit; all outer backedge paths cross one of three explicit
XOR ESI resets before the next creation stores. Complete code and the
nonvolatile-register contract support that iteration invariant. The
allocation-failure branch can instead publish a null manager.

No claim is made that counts remain zero at constructor return or at a
replay event. Helpers after publication and later population are not fully
closed. Conversely, neither a successful allocation, the reserve value,
nor the Unit/XML name proves a populated count or valid entries.

## Recorded link values and static counterexample

The previously pinned complete stream audit supplies these distinct link
domains; that audit is inherited, not rerun in this constructor stage:

| File | Distinct links | Range | Below initial 1024 reservation | At/above it |
| --- | ---: | --- | ---: | ---: |
| Original 41810 | 11 | 36..827 | 11 | 0 |
| R8 partial | 11 | 36..827 | 11 | 0 |
| Current 98348 control | 11 | 109..1242 | 6 | 5 |

All 33 values fail the first lookup's bound in the modeled creation state
where logical count is zero. This gives a concrete counterexample to
acceptance based only on being below reserved capacity. It does not assert
that an actual replay queried this state, or diagnose the prior desync or
client exit. The five recorded control values above the initial reservation
also must not be rejected using that reservation as a permanent format limit;
they are recorded data, not captured proof of a runtime growth operation.

The expected singleton candidates and exact tracker owner joins from the
prior checkpoint therefore remain useful expected contexts. Their success
does not establish this independent catalog/reference acceptance condition.
There is no conversion, guessed fallback, default entry or acceptance flag
added to bypass it.

## Verification and remaining boundary

Five qualified ranges total **2,826 bytes / 675 instructions**: four complete
original RuntimeFunction/CHAININFO unions and one branch-closed no-call leaf.
The newly decoded constructor accounts for 1774 bytes / 410 instructions;
the lookup/assignment/insertion ranges were already qualified. The separate
15-byte publication window contains three instructions. All 68 selected
instruction/call/reference checks, two register-flow checks, the RSI-reset
cutset, 92 catalog-slot address cases, two original metadata rows/literals
and 33 zero-count counterexample cases pass. Original PE and transformed
text authorities remain separate.

REA status was checked without opening a target or starting analysis. It
reported no active target and no pending cleanup. IDA is available as a
provider but not selected; this does not prove a live IDA bridge or target
identity. Ghidra 12.0.4 is outside this REA provider's accepted 12.1 line.
No installation, new IDA/Ghidra import, target launch or debugger attach was
performed. Provider status discovery may probe local configured IPC; no
external-network task was requested. Native evidence here still comes from
Python and GNU objdump under WSL, not REA native-provider analysis.

The exact next data requirement is the populated Unit manager in the same
relevant context, including the descriptor result at context `+588` / manager
`+30`, the loaded input/merge identity, logical counts and entry/reference
states. The static path string or an unrelated control catalog cannot
substitute for that instance. Historical 41810 rules and successful native
application/playback remain separate requirements.

Original/R8/current replay and unused launcher-draft hashes were checked
again and remain unchanged. No game/tracker decode, production conversion
change, replay/sync write, unit tests, full corpus, hosted CI or independent
peer review occurred in this stage. All work stays offline with no game,
Battle.net, Computer Use, external-network request, remote refresh or
publication. Full upgrade/playback remains false.

Addresses, offsets, allocation sizes and reservation literals are hexadecimal.
Catalog indices, slot/event counts and link-value ranges in prose are decimal.
