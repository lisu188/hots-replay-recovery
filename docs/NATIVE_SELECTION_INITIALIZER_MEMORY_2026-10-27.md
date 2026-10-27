# Selection initialization memory effects

The selected normal-return initialization route now establishes an empty
active selection row under explicit allocation, ABI and stability conditions.
The helper-memory gap in the prior subgroup checkpoint is closed for the
three zero-fill sizes used by this route. This is a static composition result,
not a capture of a running client or proof of the row at a replay event.

## Descriptor helper

`202D3C0..202D673` is a branch-closed, no-call leaf of 691 bytes / 98
instructions. It performs 96 stores, three per descriptor at eight-byte stride:

```text
for i in 0..31:
    DWORD[base + 8*i + 0] = 0x03ff0100
    WORD [base + 8*i + 4] = 0
    BYTE [base + 8*i + 6] = 0
RAX = base
```

The last written byte is offset `FE`; byte 7 of each descriptor is untouched.
There are no calls or stack accesses. Every output store is within the
256-byte descriptor region supplied by `202D680` at `row+A4`, and cannot
overwrite the row counts or active subgroup at offsets 0..2 under disjoint
storage. The immediate `03ff0100` is a raw descriptor default, not an invented
unit-link identity, class or catalog rule.

The complete row constructor subsequently fills all 256 descriptor bytes
with zero. Thus these early defaults must not be copied as the final
descriptor array of a newly initialized allocation-backed row.

## Selected zero-fill paths

The relevant function at `1A2B6C0` has an original RuntimeFunction extent
ending at `1A2B850`. The qualified **204-byte prefix** ends at `1A2B78C`.
It contains the paths for the selected sizes; the remaining 196 bytes,
including inline data and the short-size path, are outside this proof.
The prior whole-function linear exploratory decode crossed that data and
was not admitted as a complete instruction stream.

The selected calls pass zero and one of three lengths:

| Call | Destination | Length, decimal |
| --- | --- | ---: |
| allocation initialization | allocation base | 147,840 (`24180`) |
| row item reset | `row+4` | 128 (`80`) |
| row descriptor reset | `row+A4` | 256 (`100`) |

All exceed 16, so the conditional branch to `1A2B7D0` is excluded by the
checked call operands. The feature word at `3B5934C` selects between SSE and
the separately qualified tail `1A2B6A0..1A2B6B0`: bit 2 for lengths 17..128
and bit 1 for larger lengths. The actual feature value need not be captured
for a result that holds for either selected route.

The tail preserves RDI with a stack save/restore and uses `rep stosb` for
exactly the supplied count, with AL=0 and DF clear as required by the ordinary
Windows x64 ABI. It returns the original destination from R11, initialized
by the main prefix. This is a qualified tail-entry contract, not a claim
about direct calls into that helper with arbitrary R11.

On the SSE route, 128-byte calls use eight 16-byte stores. Larger calls first
write a 16-byte head, align forward within that head, process 128-byte blocks,
then 16-byte blocks and a final overlapping vector when needed. The checked
instructions generate zero vectors. Aligned stores use aligned addresses.
The stores may overlap but remain inside the requested output interval.

An operand-derived interval calculation covers all three selected sizes,
all 16 possible destination residues modulo 16, and both SSE/REP routes:
**96 cases**. Each has the exact requested interval as its write union and
no output store outside it. These are arithmetic coverage cases, not CPU
emulation, native target execution, or a general proof for all fill sizes.
The REP route's disjoint stack save is explicitly outside the output buffer.

## Composed row result

The complete byte-qualified `202D680` constructor first clears WORD `[row]`
and BYTE `[row+2]`. Its descriptor helper and both zero-fill calls preserve
those bytes by their now-qualified output footprints. Its other direct
stores stay within the row, and its saved row pointer is preserved by these
selected callees under the Windows x64 register contract.

Using the prior whole-allocation zero fill and row construction loops, the
final static representation of each of the 352 rows has:

- unit count, subgroup count and active subgroup index equal to zero;
- 128 item bytes at `+4..+83` equal to zero;
- 32 per-item tag bytes at `+84..+A3` equal to `20`;
- 256 descriptor bytes at `+A4..+1A3` equal to zero;
- padding byte 3 still zero from the initial allocation fill.

This 420-byte expected representation is synthetic, derived from checked
stores and call order. Its SHA-256 is recorded in the JSON receipt; it is
not a client memory dump. The previously qualified active rows at indices
176..191 are among these initialized rows and match the talent getter's
address formula for all 16 user indices.

The selected constructor, allocator and helper routines now suffice for
the normal-return empty-row result under the stated conditions. An actual
constructor call, later snapshot/helper mutations, reset/reallocation,
the opaque dispatch route and effective catalog state at a purchase are
still not observed or universally closed by this result.

## Evidence and limits

Seven qualified ranges total **1,545 bytes / 293 instructions**: four complete
original RuntimeFunction/CHAININFO unions, two branch-closed no-call leaves,
and the selected 204-byte conditional fill prefix. Three newly qualified
ranges account for 911 bytes / 155 instructions; other code extents were
already qualified in the prior checkpoint. All 73 selected instruction,
call and feature-reference checks pass. Every descriptor store and the
96 selected fill intervals are separately enumerated and checked.

The original PE, transformed text, original/R8/current replay and unused
launcher-draft hashes were checked. Original and transformed code authorities
remain separate. Python and GNU objdump under WSL supplied the evidence;
no REA native provider, client execution or CPU emulation occurred. No game
or tracker decode, production conversion change, unit tests, full corpus,
hosted CI or independent peer review was performed for this helper audit.

The proof requires a valid writable allocation of the requested extent,
non-overlapping caller stack/globals/metadata, stable code and pointers,
ordinary x64 ABI including DF clear and SSE2, normal returns, and no address
wrap, faults, exceptions, reentry or concurrent/alias modifications.
These conditions are not a claim that a failed replay satisfied them.

Next use this qualified empty initialization as a conditional model input,
resolve native removal-mask/selection update semantics and effective
definition inputs, and then reconstruct cumulative state before attributing
an actor or owner to a talent. Historical 41810 rules and successful native
playback remain separate unfulfilled requirements.

All work stays offline: no game, Battle.net, Computer Use, network, remote
refresh or publication. Original/R8/control replay and sync bytes remain
unchanged. Full upgrade/playback remains false.

Addresses, offsets, descriptor defaults and allocation/stride literals are
hexadecimal; counts and lengths explicitly described as decimal are decimal.
