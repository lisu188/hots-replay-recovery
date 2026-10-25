# Replay header transfer: independent IDA decode and selector 879

The current-client static analysis now establishes how the cached header word
reaches the loader's validation input. IDA Professional 9.0 independently
decoded the same 201-byte entry prefix as Ghidra 12.0.4, matching all 38
instruction boundaries and bytes. A separate eight-byte source-file read
also distinguishes the header reader's numeric selector, **879**, from the
adjacent setup reader's **888**. These results do not establish playback or
the historical meaning of the transferred word.

Repository baseline: `6ac0bce7785a457d10ef9534d71639e061b130dc`.
Addresses below are RVAs unless identified as offsets. Exact evidence pins
and scope are recorded in the [paired observation](../observations/replay-header-transfer-ida-and-root-selector-2026-10-25.json).

## The bounded transfer contract

The retained call at `134DC55` authenticates entry `134C220`. The selected
predecessor metadata interval ends at `134C21D` and does not cover that entry.
Consequently, the new export is a caller-anchored linear prefix, with a
256-byte window, a 128-instruction cap and a stop at the first decoded RET.
It is not a claim about whole-procedure bounds or a complete control-flow graph.

For entry RCX=`D` and RDX=`S`, the prefix keeps both base registers unchanged:

| Site | Local effect |
| --- | --- |
| `134C28C` | Load DWORD `[S+A0]` into EAX. |
| `134C292` | Store EAX into DWORD `[D+A0]`. |
| `134C2D7` | Set RAX to D. |
| `134C2E8` | Return normally, with no intervening RAX write. |

No later prefix store overlaps `D+A0..D+A3`. The complete observed stores
cover half-open offset ranges `[0,BD)` and `[C0,D4)`: 209 bytes within a
212-byte bounding extent. Offsets `BD..BF` are untouched. This is not a
whole contiguous structure copy or a general arbitrary-overlap memmove.
For arbitrary overlapping inputs, earlier stores could change later source
loads. Entry-snapshot identity therefore needs the stated address, memory,
normal-completion and concurrency conditions.

## Composition with the retained loader frame

The separately retained `1A24E60` prefix has no RAX, RCX or RDX writes and
balances its local RSP adjustment on normal return. This closes the earlier
helper-return condition for the saved prologues. It does not close faults,
concurrent mutation or the effects of other opaque callees.

For the `CFE3B0` loader's normal frame, the retained call sequence gives:

| Expression | Derived address |
| --- | --- |
| Destination D | `RBP-C0` |
| Cached source S=`O+1370` | `RBP+5E490` |
| Validation object T | `RBP-28 = D+98` |
| Validation word `T+8` | `D+A0` |
| Corresponding cached word `S+A0` | `O+1410` |

The source and destination are separated by `5E550`, so their observed
212-byte bounding spans are disjoint under valid, non-wrapping frame
addresses. Subject to ordinary frame/register preservation across the
opaque calls and the stated memory conditions, **T+8 receives the cached
DWORD at O+1410 at transfer return**.

The later `134D9D0` call precedes `CFA810`. Its alias effects, the validation
routine's opaque helpers and the optional later callback are still open
boundaries. No unchanged value at the later controller store is proved.
The separate request caller's `P=RBP+350` belongs to another frame context;
its `P+18/P+1C` fields are not identified with this loader's `T+8`.

## Independent IDA result

IDA ran its installed text executable with a reviewed IDC script in a new
empty 64-bit database. The script populated only the fixed 201-byte literal
reconstructed from the pinned Ghidra export, checked every loaded byte,
and decoded linearly without autoanalysis, function creation, a PE loader,
debugger or target execution.

The captured run exited zero. Its 38 instruction boundaries and opcode
bytes exactly match Ghidra, including the first RET at `134C2E8`. The common
code SHA-256 is `3ec14f18b790bed49ec9927dfe8d20cb4c9720068ae4386e2fe475afb70d5cc9`.
Assembly text formatting differs between tools; text equality is not claimed.
IDA's 2134-byte TSV plus 911-byte status JSON total 3045 bytes, below the
16384-byte cap checked before creating those payloads.

An earlier attempt terminated without a database, log or result and without
a captured exit code. That observation is preserved separately, with no
inferred cause or successful-decode claim. The successful attempt used new
output names and captured process completion and diagnostics. REA and
OllyDbg were not used in this milestone.

## Static selector binding

The retained header reader at `134DC70` supplies DWORD `[27C9F20]` in R8D
and context address `393EB80` to `1A772C0`. The counterpart reader uses
DWORD `[27C9F24]` with the same context address. The initializer at `1D08A0`
binds that context to the separate 13744-byte, 1192-type stripped program;
this is distinct from the 8330-type Battlenet registry.

The new read maps exactly `[27C9F20,27C9F28)` into the source PE's readable,
non-executable `.rdata` section. One eight-byte read at file offset 41717536
returns little-endian DWORD values **879** and **888**. The source path and
handle match all four inherited identity fields before and after the read.
The full source SHA is inherited from the pinned completed hash checkpoint;
this step does not rehash the executable or observe live process memory.

The retained setup bridge's 888-to-889-to-775 relation belongs to the adjacent
setup selector. It does not name selector 879 or establish the header's
field layout. Source-file initial values also do not prove that runtime
code leaves those globals unchanged.

## Remaining work

The next constraints are the stripped registry's selected record and native
output layout, the meaning of cached `O+1410`, and the intervening alias,
owner and lifetime relationships. No executable/data-build field name is
assigned here. Historical 41810 package/schema/rule recovery and catalog,
ability, instance and deterministic synchronization migration remain open.

The original replay and R8 are unchanged. R8 still declares 98285. No replay
was generated, no game/client was launched, and no Computer Use or IPC send
occurred. Full replay upgrade and playback validation remain false.
