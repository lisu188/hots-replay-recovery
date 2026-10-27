# Native talent index transport and a selected array query

The current client transports the selected talent index as one unsigned32-bit
value, without a name lookup in the selected constructor. A selected sender
passes the same DWORD to an array query and to that constructor. The query
checks a runtime count and copies a64-byte array entry, but its failure can
still reach event construction. It must not be treated as a universal playback
acceptance gate.

This binds a concrete code path behind the earlier talent observations. It
does not yet bind the queried array to the effective `TalentTreeArray`, prove
XML document order, or authorize a historical index rewrite.

See `observations/native-talent-index-route-2026-10-27.json` and its validation
receipt for exact code/data pins, complete selected fragment unions and limits.
Addresses below are RVAs; structure offsets are stated separately.

## Index transport

Constructor1351460 sets header3006E and primary method table26A77D0. Its selected
read/write slots+20/+28 point to94B300/94B260. Both pass object+30, root slot
27BEC5C and native context14393EB80 to the previously bound serializer helpers.
The pinned native schema closure564->565->3 is one STRUCT field, a USER wrapper
and an unsigned32-bit integer. Its physical graph corresponds to the upstream
`SHeroTalentTreeSelectedEvent.m_index`; this does not invent native field names.

Factory94B560's nonnull allocation path installs the same header/table and
stores the incoming ECX directly as a DWORD at object+30. It then tail-calls
8418D0, which forwards the object to13340E0 using the selected global dispatcher
reference. No name translation or talent semantics are established in this
construction path. Allocation failure and dispatcher execution are outside
the described successful-construction claim.

In sender8C0EF0, the DWORD at its second argument+1C is supplied to B0F1F0 at
8C0F62 and to factory94B560 at8C0FCE. The sender's full selected body is485 bytes
across seven RuntimeFunction records joined by original CHAININFO. Partial
unwind fragments do not cover its cleanup and alternate branches.

After B0F1F0 returns, `test al,al` at8C0F69 and `je` at8C0F6B send a failed query
to8C0FC6. Following that path through its normally returning helper reaches
the factory call. On a successful query, another lookup and comparison can
skip construction for an equal value. Neither path proves how the dispatcher
or replay playback will accept, reject or execute a selection.

## The bounded query

B0F1F0 calls9D5080 with its first byte argument and a zero second argument. On
a nonnull return it supplies returned-object+50, the original unsigned index,
and the output pointer to B0F160. The semantic identity of that first selector
and returned object remains unbound here; it is not promoted to a replay user
or effective CHero merely from surrounding context.

B0F160 obtains a tagged value through201E580 and clears its low five bits. On
the selected normal path it requires:

- a nonnull resulting pointer;
- unsigned `index < DWORD[resolved + 0x500]`.

It then computes:

```text
entry = QWORD[resolved + 0x510] + uint64(index) * 64
```

The index is zero based relative to this runtime array. No runtime array count,
base or entry was captured. Copy helper50B800 receives that entry and the output
pointer; its explicit instructions copy entry+8 to output+8. Subsequent cleanup
and helper behavior still require normal ABI, valid disjoint storage and no
unobserved alias mutation.

On the sender's successful-query path, output+8 is used as the second selector
of B0F720. That complete39-byte leaf checks the low byte of its first argument
against16 and its unsigned second argument against32. It reads the DWORD at:

```text
0x3677A30 + (first_selector * 32 + second_selector) * 4
```

Its checked failure result is FFFFFFFF. Calling the second selector a talent
tier, or the first selector a particular player namespace, would require a
separate binding. These bounds do not validate the entire game event.

## Field-name bridge still missing

A separately checked metadata window references the exact `TalentTreeArray`
literal at2BC5958. Call51115E supplies R9D=470 to1601160. The query instead reads
at resolved offsets500/510. The registration parameter's meaning and any
required object adjustment have not been authenticated. They must not be
equated by subtracting offsets or assuming a common record base.

The owner descriptor reference at2BC5320 is opaque data, not a literal name
string. No owner class identity is assigned from it. The two selected metadata
windows total511 bytes/92 instructions; they are not a complete registration
function or an effective catalog snapshot. Native array order, XML append/
inheritance behavior, map/mod overrides and historical rules remain separate.

The selected `TalentChosen` interned-label reference in1D96540 compares a record
field in a statistics writer. It supplies no purchase-index data flow and is
excluded from the talent execution claim. Its label alone cannot identify the
native producer of an executed purchase.

## Validation and conversion boundary

Ten selected ranges total1242 bytes/338 instructions. Original PE method slots,
header stores, scalar transport, array bounds/stride, complete selected unwind
fragment unions and direct non-call branch targets are checked against pinned
transformed text. The query-failure path to event construction is checked
separately. An initial overlong leaf window and a linear sweep containing an
embedded jump table are excluded. Signed PE identity and transformed text
identity remain separate; this is ordinary GNU objdump analysis under WSL,
not REA/IDA/Ghidra Evidence or native execution.

Source/R8/current replay and unused launcher draft pins are rechecked. Their
event streams were not freshly decoded in this milestone. No production code,
unit tests, conversion recipe, replay, synchronization data or version metadata
changed. Broad corpus, hosted CI and independent peer review were not performed.

Keep all work offline. Full upgrade/playback remain false. The next useful
binding is the metadata field/queried array relationship and the actual event
consumer's selection rules. No15->7 rewrite, missing-name substitution or
general playback acceptance follows from the bounded query.
