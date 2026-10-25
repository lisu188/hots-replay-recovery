# Replay loader: cached header transfer and request prefix

The selected client-98348 records establish a cache-and-transfer wrapper at
`134DC00` and the prefix leading into the retained second request caller.
The prefix exposes an earlier request-pointer escape and the initial stores
preceding its member-derived field overwrite. The transferred type, field
layout and build/version meanings remain unresolved.

Repository baseline: `c08d4b9fdd266be65859483911a5c7dd01fb8d05`.
All code addresses below are RVAs. Exact pins and limits are in
[the paired observation](../observations/replay-header-transfer-and-request-prefix-2026-10-25.json).

## The 134DC00 wrapper

The wrapper retains entry RCX in RBX as `O` and entry RDX in RSI as `D`.
Its selected normal paths implement these operations:

| Condition | Observed operation |
| --- | --- |
| Low bit of the first byte at `O` is clear | Call `134DC70` at `134DC29` with RCX=`O+8` and RDX=`O+1370`. |
| That call returns nonzero EAX | Store EAX at DWORD `[O+33310]` and return that value through the early epilogue. |
| That call returns zero | Set bit 0 of DWORD `[O]` at `134DC48`, then continue. |
| The low bit was already set, or the call returned zero | Call `134C220` at `134DC55` with RCX=`D` and RDX=`O+1370`; after normal return, clear EAX and return zero. |

The last call's EAX is ignored by the wrapper. These instructions identify
a cached region and an output-transfer call. They do not establish the
region's typed schema, the transfer's extent or copy semantics, or a write
to the earlier loader's `T+8`. The earlier conditional stack relation remains
as described in [the CFA810 validation-gate observation](REPLAY_VERSION_VALIDATION_GATE_2026-10-25.md).

## Prefix register and request boundaries

`CFBDC5` forms RBP from then-current `RSP-44F0`. The prefix sets EAX to
`45F0`, calls `1A24E60` at `CFBDD2`, then subtracts the returned RAX from RSP.
Only afterward does `CFBDE1` save RDX in R13 and `CFBDE4` save RCX in RSI.
These are post-helper register values. Entry-argument identity and exact
stack algebra require an authenticated preservation contract for that
helper. A standard helper name is not assigned, and this evidence does not
bind RSI to the separate loader's controller.

`CFBE40` reads DWORD `[RSI+100E8]`. The following local arithmetic assigns
R14D as follows: `1 -> 2`, `2 -> 3`, `3 or 4 -> 4`, and other values `-> 1`.
This is a numeric producer; later callees' register and memory effects
remain outside the proved contract.

For the request pointer `P=RBP+350`, the captured stores and call are:

| Site | Observed effect |
| --- | --- |
| `CFBFF3` | Initialize DWORD `P+18` to `1`. |
| `CFBFFD` | Initialize DWORD `P+1C` to `FFFFFFFF`. |
| `CFC12C` / `CFC153` | Supply RCX=`P` to `CFFD10`, with RDX=`RSI+19140`. This is an authenticated earlier pointer escape. |
| Retained `CFC1DB` / `CFC1E1` | Load DWORD `[RSI+19118]` and overwrite `P+1C`. |
| Retained `CFC1EE` | Store inherited R14D at `P+18`, before its subsequent local zeroing. |

The initial sentinel, the later member-derived store and the source snapshot
at the AB90 copy helper are distinct observations. Opaque-call effects,
retained aliases and value preservation to that snapshot remain unproved.
No actual field value or executable/data-build name is supplied.

## Record joins and bounded verification

| Selected record | Code bytes | Instructions | Direct calls | Direct branches |
| --- | ---: | ---: | ---: | ---: |
| `[CFBDC0,CFBE23)` | 99 | 23 | 1 | 1 |
| `[CFBE23,CFC16A)` | 839 | 169 | 15 | 22 |
| `[134DC00,134DC6C)` | 108 | 31 | 2 | 2 |
| Total | 1046 | 223 | 18 | 25 |

The first selected record falls through at `CFBE23`. The second has one
direct branch outside the selected batch, `CFC168 -> CFC1BA`, and its
untaken path falls through at `CFC16A`. Both destinations are authenticated
instruction boundaries in the hash-checked retained `[CFC16A,CFC7B0)`
listing. That listing was reused without re-exporting it.

Every selected instruction span and relative target was checked against
the saved bytes. The source patch and corresponding project memory were
verified before the one Ghidra 12.0.4 run with `readOnly`, `noanalysis` and
two CPUs. Completion and read-only discard were retained. The exporter
checked all three ASM files plus quality JSON before creating result files:
**13177 + 4862 = 18039 bytes**, within **32768 bytes**.

Bounds came from retained V3 metadata with 460 source bytes read and no new
hash stream in that metadata step. The exporter itself performed no PE
read. These are floor-by-begin candidates checked to cover their targets;
global EndAddress non-overlap, unique covering records, primary procedure
entries and a full high-level CFG are not claimed.

This static three-record milestone performed no game/client launch,
target-code execution, Computer Use or IPC send. The concrete next contract
seeds are `1A24E60`, `134C220` and `134DC70`. No historical acquisition,
playback result or completed migration is established.
