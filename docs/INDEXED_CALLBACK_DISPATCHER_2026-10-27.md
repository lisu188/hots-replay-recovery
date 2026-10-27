# Indexed callback dispatcher and five index22 callers - 2026-10-27

Five identified direct callers of `1D8ADA0` select physical index22 through an indirect registry pointer. They do not authenticate the missing producer for the previously located slot121. This narrows the next source investigation without adding historical values or changing a replay.

Addresses and offsets are hexadecimal; slot indices, byte/instruction counts and the last table column are decimal. The [observation](../observations/indexed-callback-dispatcher-2026-10-27.json) contains the code and decoder-output pins. All code witnesses come from the retained analyst-derived 98348 static text patch, not an unaltered PE section or runtime capture.

## Dispatcher and receiver

The eighteen-byte body at `1D8ADA0..1D8ADB2` zero-extends entry EDX through EAX, moves entry R8 to RDX, computes `RCX=entry_RCX+8+uint32(entry_EDX)*8`, and tail-jumps to the previously inspected callback helper `2DDC10`. No bounds check appears in this selected body. This establishes an indexed address calculation and argument forwarding, without recovering semantic event or type names.

A raw E8/E9-relative-target scan over static patch RVAs `[BA000,239D000)` finds five candidate E8 sites and no E9 sites targeting this body. Native decoding authenticates those five calls. This scan does not cover indirect calls, code outside the retained patch, or every possible dispatcher implementation.

Every covered caller loads `G=QWORD[0x143B7C6B0]` and, on its guarded call path, calls `1D847E0`. That eight-byte getter returns `QWORD[G+A0]`; it does not compute `G+D0`. The caller passes that returned pointer as RCX, decimal22 (`0x16`) as EDX, and its local argument address as R8.

| Caller entry | Getter call | Dispatcher call | DWORD stored at argument+18 (decimal) |
| --- | --- | --- | --- |
| `1131400` | `11314E0` | `1131513` | 0 |
| `11353B0` | `11353FF` | `1135436` | 2 |
| `1135440` | `113549A` | `11354D1` | 1 |
| `11354E0` | `1135535` | `113556C` | 1 |
| `1135580` | `11355A2` | `11355D9` | 3 |

The argument also receives a QWORD address `0x1427AAB28` at +0, a zero QWORD at +8, and DWORD `0x16` at +10. These stores do not initialize every byte of the local object. In particular, the DWORD store at +18 does not establish a full QWORD source pointer or recover a historical ClientInfo field.

The resulting callback-helper receiver is `QWORD[G+A0]+B8`. The previously identified slot121 is `G+4A0`, equivalently `(G+D0)+8+121*8`. Equality of these receivers is unresolved. Neither a generic index calculation nor a shared callback helper supplies that missing identity proof.

## Setup boundary and evidence limits

The selected setup range `1D83080..1D83546` supplies further pointer provenance: it requests `E5D0` bytes at `1D833F2`, calls the allocator at `1D833FE`, and on the nonnull branch calls `1D85A10` at `1D8340B`. It stores that constructor's return value at the saved incoming receiver's +A0 at `1D8341A`; the allocation-failure branch supplies zero through RSI. The constructor has not been expanded here. Its return identity, later virtual-call effects, aliases and concurrent writes remain unproved.

The eight witnesses cover 2,084 bytes and 500 instructions. GNU objdump2.42 returned successfully for each bounded decode, and all contiguous instruction-byte columns matched the guarded source. The setup range spans four selected adjacent original-PE runtime-function records; adjacency does not establish a complete function or CFG. The first record alone ended at a nonterminal LEA, so it was not accepted as a complete function.

REA's Windows IDA adapter was checked, but its attached input hash differed from the selected HotS executable. No HotS function result was obtained through that adapter, and its target binding was closed without modifying the unrelated databases. No OllyDbg connector is exposed in this REA tool inventory. The native witnesses in this milestone are from the explicitly identified WSL decoder.

No new database, game launch, Computer Use, codec change, replay, historical default or playback result was produced. The next source task remains binding an actual sender's receiver and argument to the exact slot121 registration. The full replay upgrade remains incomplete.
