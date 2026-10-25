# Replay loader: numeric validation gate at CFA810

The retained client-98348 function at RVA `[0xCFA810, 0xCFA8D5)` checks a structure passed by its caller and returns numeric statuses. It reads DWORD `T+8` and returns `0x18` when that value equals `73016`, `79155` or `79515`, after earlier helper gates have passed. The selected instructions establish this validation flow; they do not establish a build/version name for the field or its producer.

## Arguments and normal return paths

Entry RCX is retained in RBX as `T`; entry RDX is retained in RSI, R8 in R14 and R9D in EBP. The prologue also loads a pointer from entry-stack offset `+0x28` into RDI. It initially writes zero through this pointer and later writes the AL returned by `271B50` through it.

| Gate | Authenticated normal-flow rule |
| --- | --- |
| `CFA83E → 271C60` | RCX is `T`. AL zero returns `0x15`; nonzero continues. |
| `CFA854 → 271B50` | RCX is `T`, RDX is entry argument 2. AL is stored through RDI. Nonzero continues to `2719B0`; zero calls `271CE0`. |
| `CFA862 → 271CE0` | RCX is `T`. EAX `1` returns `0x14`, `2` returns `0x16`, `3` returns `0x18`; other values continue to `2719B0`. |
| `CFA87B → 2719B0` | RCX is entry R8 and EDX is entry R9D. EAX zero returns `0x17`; nonzero reaches the field read. |
| `CFA899` field read | Read DWORD `[T+8]`. Equality with `0x11D38`, `0x13533` or `0x1369B` returns `0x18`; a value different from all three returns zero. |

These are numeric contracts. Helper names, human error labels and download behavior have not been recovered. CFA810 has no direct store addressed as `[T+8]`, but this does not establish nonmutation: stores through RDI may alias the structure, and the called helpers' effects remain unknown. `271B50` is a concrete contract seed because it receives `T` before the read; it is not a proven or unique field writer.

## Earlier caller boundary

The retained loader passes `T=RBP-0x28` to CFA810 at `CFEB3D`. It also has an earlier call to `134DC00` at `CFEB01`, with RDX formed from live `RSP+0x40`. The root review records prior local zero-initialization sites `CFEA47/CFEA51`.

The caller prologue includes `MOV EAX,0x90540`, a call to `1A24E60`, then `SUB RSP,RAX`. **Only if that helper preserves RAX as `0x90540`** does the reviewed stack algebra give live `RSP=RBP-0x100`, the earlier region pointer `RBP-0xC0`, `T=region+0x98` and `T+8=region+0xA0`. That helper contract is unauthenticated. The earlier region's extent and field-write contract are also unknown, so `134DC00` remains a prior header-candidate seed with conditional overlap.

After CFA810 returns, the loader can pass `T` to an optional callback before reading its then-current DWORD `T+8` into controller field `+0x19118`. Neither unchanged propagation through that callback nor identity between this controller and the second request caller's inherited RSI has been proved.

## Source and export checks

The source PE is 53,573,840 bytes, SHA-256 `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`. The selected-code SHA-256 is `1f4d77bb6ea921c91008fb6b7c346603080cfaf8d2d41d57659aad9a455569bb`.

| Stage | Source bytes read or verified |
| --- | ---: |
| One fresh PE identity hash stream | 53,573,840 |
| Header and `.pdata` metadata in that pass | 2,450,948 |
| Separately authorized UNWIND_INFO metadata window | 256 |
| Total PE reads across those metadata steps | 56,025,044 |
| Selected-export postscript PE reads | 0 |
| Decoded-patch file verified by the postscript | 36,581,376 |
| Corresponding saved-program patch memory verified | 36,581,376 |

The postscript's `source_PE_rehash_this_step=false` describes the export step; the earlier fresh identity pass is accounted separately. This table covers source PE/patch inputs and excludes small guard, script and receipt files.

The decoded patch has SHA-256 `3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`, placed at RVA `[0xBA000,0x239D000)` with image base `0x140000000`. Ghidra 12.0.4 ran once with `readOnly`, `noanalysis` and two CPUs. All 59 contiguous instructions cover the exact 197-byte retained RuntimeFunction record and match the pinned patch. Four direct calls and 14 direct branches were independently checked from the exported bytes; all direct non-call targets remain in the record. No expanded CFG or callee behavior is claimed.

The exporter checked its UTF-8 output size before creating result files: 3148 bytes of selected ASM plus 2172 bytes of quality JSON equals **5320 bytes**, within the **32768-byte** cap. Completion, exit zero and read-only discard were retained. No decompiler or expanded ASM was used.

## Separate chained-unwind observation

A bounded 256-byte metadata read at `2CF73D0`, associated with the previous CFC16A record, has version 1, flags 4 (`CHAININFO`), prologue size zero and four unwind codes. Its aligned optional tail contains the literal previous RuntimeFunction entry `[0xCFBDC0,0xCFBE23)` with unwind RVA `0x2CF739C`.

Microsoft specifies that a chained entry can itself refer to another chained entry. This one record therefore does not establish the primary procedure entry or any owner-register meaning. See the `UNWIND_INFO` and chained-unwind sections of the [Microsoft x64 exception-handling specification](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170). The metadata is not an RSI identity proof.

## Continuation boundary

The two next contract seeds are `134DC00` in the earlier header-candidate route and `271B50` in CFA810. Neither is assigned a unique-writer role. No further native expansion occurred in this stage.

This is an offline `static_native_analysis_lane` milestone against repository baseline `43189dabfcbce950ecaf58f7ba6f4d22cb664100`. It supplies no actual field value, old-client acquisition route, playback result or completed conversion. No game/client launch, target-code execution, Computer Use or IPC send occurred. Source pins and limits are in [the paired observation](../observations/replay-version-validation-gate-2026-10-25.json).
