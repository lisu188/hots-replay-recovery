# Registered replay input and abstract source interface

The registered App adapter now has a qualified conditional route to the input
object retained as R13 by the StartReplay consumer. The next inspected layer
uses an abstract input interface and a separate context. Its visible body does
not establish direct archive-byte parsing or a numeric input-length argument.

This advances the source boundary in
[the earlier descriptor report](NATIVE_WRAPPER_DESCRIPTOR_SOURCE_2026-11-02.md).
It supplies no historical player values or replay migration policy.
All addresses and offsets below are hexadecimal; type IDs are decimal.

## Adapter route

The original PE's RTTI identifies tables 298C798 and 298C7C0 as the primary and
offset-8 interfaces of `Battlenet::Tumor::EventAdapter`. Both validated MSVC x64
locators point to the same TypeDescriptor. The selected initialized wrapper L
stores its Tumor object B at L+20 and its supplied listener at L+30.

Primary slot+8, 1EC29E0..1EC2A40, uses its incoming index I to select
Q=QWORD[B+A8+8*uint32(I)]. If Q is nonnull, it calls Q's secondary interface with
RCX=Q+8, RDX=&H, and R8 equal to the original payload X supplied in entry R9.
The selected body has no index bounds check. Q need not equal the invoking L.

Secondary slot0 at 1EC2240..1EC224A is exactly ten bytes:

```asm
mov rcx, [rcx+28h]
mov rax, [rcx]
jmp qword ptr [rax]
```

If Q is a valid stable EventAdapter whose secondary table is 298C7C0, this leaf
with receiver Q+8 selects Q+30's listener and preserves RDX/R8. If that listener
has the previously qualified stable G table 28E6CE8, its primary thunk
1D84540 adds D0 to RCX and reaches 1E65070. On the H[0]==3 branch, the delegate
passes X as RDX to 1E5CF60. The consumer saves that pointer in R13 at 1E5CF84.
There is no intervening call on this selected delegate branch.

H is only partly initialized. The adapter stores a byte at H+0 and a byte 1 at
H+4; bytes H+1..3 and H+5..7 remain untouched. Its QWORD 1 store at H+10 is
followed by an index DWORD store at H+14. Only H[0] controls the inspected
delegate's selected branch. None of these stores supplies a historical default.

The three new adapter witnesses contain 235 bytes and 62 instructions. An
independent review freshly rechecked another 464 bytes and 101 instructions
downstream. Padding and the next procedure after the ten-byte thunk are excluded.
This is a conditional compiled call path, not observation of an actual call.

## Interface frame and dispatcher

The earlier 1A6E990 frame builder places incoming.slot10's result at F+10 and
incoming.slot20's result at F+18. Its output interface is at F+20 and its local
registry/type descriptor is at F+28. The call to 1A78CC0 reaches an exact
five-byte tail jump to 1A78210.

The qualified dispatch code is 1A78210..1A78665. A separate 64-byte switch table
and three padding bytes are excluded from its 1109 code bytes/287 instructions.
All sixteen table targets are instruction starts. Two selected branches show
the argument relationship directly:

| Classifier result | Input operation | Output operation |
| --- | --- | --- |
| 5 | Call [F+10].virtual+30 with context [F+18] | Forward zero-extended AL to [F+20].virtual+B0 with descriptor [F+28] |
| 7 | Call [F+10].virtual+28 with context [F+18] | Forward RAX to [F+20].virtual+A8 with descriptor [F+28] |

Thus F+10 is used as a virtual-interface receiver, and F+18 as its second
argument/context. These paths do not authenticate a numeric length. The visible
body is consistent with schema-directed traversal; an unexpanded input method
could still consume encoded bytes. Successful parsing and all field semantics
remain unproved.

## Concrete candidate wrappers

An original-PE RTTI scan admitted eight selected vtable candidates from 56
filtered descriptors. A nearby `IncomingEvent` table has only two executable
cells before the next RTTI locator; adjacent data must not be interpreted as
its slot+10/+20 methods.

Two actual BSN wrapper candidates have qualified getter and initialization
relationships:

| Candidate table | Slot+10 result | Slot+20 result | Initial descriptor stores |
| --- | --- | --- | --- |
| 298D700, DatagramConnection RequestPtr | W+10 | W+18 | Registry at W+18; type 4608 at W+20 |
| 298D0D0, DatagramConnection Response | W+178 | W+180 | Registry at W+180; type 4639 at W+188 |

Both type fields can be overwritten by their shown kind16 unwrapping loops.
The RequestPtr stack construction is qualified through its selected dispatch;
the Response proof stops at an initialization prefix. The separate Response
table-reset routine is destructor-like. Neither candidate has been bound to the
actual incoming R13, and neither initial type is the S2Response type 6060.

## Evidence and next action

See [the observation](../observations/registered-replay-input-interface-2026-11-02.json)
for whole-source identities, qualified range hashes, original table/global
bindings and independent-review pins. Executable witnesses use the preserved
analyst-transformed 98348 text; original PE bytes supply table, RTTI, type-global
and unwind facts. They are not runtime or unaltered-PE instruction observations.

Next bind the actual incoming object's source interface/context and upstream
construction, or obtain the historical native producer. Do not assume a raw
buffer/length signature, assign a candidate class from its name, or manufacture
missing values. No production converter, replay, synchronization data, game
launch or Computer Use changed. Full upgrade and 98348 playback remain unproved.
