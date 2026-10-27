# Exact definition inputs for selected-unit subgroup construction

The selection insertion predicate is now a concrete native data dependency:
`993DA0` writes bit 5 of byte `+DD` from a second resolved object. It does not
identify that object from a hero name or from the serialized unit link alone.
The current path has two different indexed arrays in the context table.
This closes the selected predicate-body gap while leaving the actual table,
definition and object values unobserved.

## The two lookups

The previously qualified `5E1B70` reads global context `3388B18`, takes its
table pointer at `+2A0`, and looks up the subgroup's uint16 unit link using
count `+90` and entry array `+A0`. It writes an output reference; a null table
slot or out-of-range input writes zero. A valid context remains a prerequisite.
The function returns the output-slot pointer, not the definition as RAX.

`201A490` performs a second lookup. It reads WORD `+40` from that definition,
or selects `FFFF` when the first definition reference is null. It takes the
same context/table route but uses **count `+38` and entry array `+48`**, with
eight-byte entries. These arrays are distinct from the first lookup's arrays.
No equality between the wire unit link and the second-stage index is assumed.

After checking the uint16 index against the second count, the helper reads
the slot. If its low bit is set, it calls `1608180(slot-1, 0)`, then reloads
the entry-array pointer and the slot. That called body and all lifetime or
initialization effects are not audited here. A non-null resulting object is
required. With the selected caller argument R9B=0, object byte 0 bit 0 must
also be clear; a set bit takes the failure branch.

For an accepted object, `201A5A0` increments DWORD `object+78` by `100`, releases
an earlier output reference as required by its branches, and writes:

```text
output_QWORD = (resolved_object & ~0x1f) | (flags_byte & 0x1f)
```

The two selected callers initialize an output QWORD and flags byte to `10`.
On the rejected/out-of-range/null-object path, `201A490` writes only the low
five flag bits, hence `10` for those callers and a masked pointer of zero.
The release helper `1607630` is an external dependency; its whole body and
universal lifetime behavior are not established by these selected operands.

A null first definition is not universally rejected: it chooses index
`FFFF`, which could resolve if the actual second count, slot and gates
permit it. No count or default-slot value is invented for the effective table.

## The selected predicate and insertion gate

`993DA0` preserves its incoming definition-reference pointer in RDX up to
its call to `201A490`. It uses allow argument 0 and flags 16, reads the masked
resolved pointer from its output slot and computes:

```text
predicate_output = (BYTE[resolved_object + 0xdd] >> 5) & 1
RAX = address_of_predicate_output
```

There is no explicit masked-null check before this byte read in `993DA0`.
The selected caller `202D910` first resolves the same definition reference
and requires its masked output pointer to be nonzero before reaching the
predicate call. Treating that earlier gate as sufficient requires a stable
definition, table and object, coherent helper returns, and the ordinary ABI;
it is not proof of a safe result for arbitrary input or intervening changes.

The prior insertion code uses this byte to choose the descriptor component:
unit handle `>>22` when it is 1, otherwise sentinel `3FF`. The other descriptor
key is the first definition's WORD `+40`, with the earlier `FFFF` fallback.
No native class, XML flag name or historical meaning is assigned to byte
`+DD` bit 5. Full subgroup ordering, removal-mask memory representation,
snapshot effects and the actual first selected handle remain outside this
checkpoint.

## Evidence and limits

Five byte-qualified ranges total **1,149 bytes / 289 instructions**. Four
complete original RuntimeFunction/CHAININFO unions and one branch-closed
no-call leaf provide their extents. Three newly decoded complete functions
account for 411 bytes / 111 instructions; the insertion and first lookup
ranges were already qualified by the prior selection-context checkpoint.
All 70 selected instruction/call/reference checks, 10 nonvolatile-register
definition/use checks and three required control-flow edges pass. The entry
RDX handoff into the predicate's resolver is separately checked for no prior
call or explicit RDX-family write.

The pinned original PE and transformed text are separately identified in the
JSON receipt. Decoding used Python and GNU objdump under WSL; it did not use a
REA native provider, load an IDA target, or execute client code. The raw native
images and whole replays are not included in this source checkpoint. The
original, R8 and current control replay hashes and unused launcher-draft
hashes were checked again; their contents are unchanged. Game/tracker decoding,
unit tests, a full corpus, hosted CI and independent peer review were not
repeated for this selected dependency audit.

The exact missing effective data is now:

- first-stage count/entries at table `+90/+A0`;
- first definition WORD `+40`;
- second-stage count/entries at table `+38/+48`, including tagged-slot state;
- the accepted object's byte 0 gate and byte `+DD` bit 5.

These values have not been captured. The result does not reconstruct a talent
purchase's actor or owner, establish a safe talent-index migration, change a
conversion, or prove event application, synchronization or playback.
Historical build 41810 rules remain a separate missing authority.

All work stays offline: no game, Battle.net, Computer Use, network, remote
refresh or publication. Full upgrade/playback remains false. Next use existing
authenticated captures or exact producers for the listed data, with no guessed
hero, catalog flag, owner remapping, or replacement of sync values.

Addresses and memory offsets, including `10`, `40`, `78`, `90`, `A0`, `DD`,
`100` and `FFFF`, are hexadecimal; counts and flag/bit values in prose are
decimal. The formulas use explicit hexadecimal literals.
