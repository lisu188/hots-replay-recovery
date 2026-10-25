# Main IPC: second bulk-request caller source and result mapping

The retained client-98348 interval `[0xCFC16A, 0xCFC7B0)` contains a second authenticated call to the bulk-request forwarder at `0x115AB90`. It loads a DWORD from `[RSI+0x19118]` and explicitly stores it in request offset `+0x1C`. After the call, returned value `3` selects numeric output code `0xA`. This establishes a member-derived request source and a distinct higher-level result branch. The member's build/version meaning and its actual value remain unresolved.

## Source and bounded export

The source PE is 53,573,840 bytes, SHA-256 `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`. Its retained decoded patch is 36,581,376 bytes, SHA-256 `3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`, placed at RVA `[0xBA000, 0x239D000)` with image base `0x140000000`.

A new selected-ASM-only postscript verified the whole patch file and the corresponding current-program memory hash. It used the previously retained `.pdata` bounds and ran once against the existing Ghidra 12.0.4 project with `readOnly`, `noanalysis` and two CPUs. No new PE pass, import/data scan, decompiler output or expanded ASM was used. Completion and read-only discard were logged. The source PE was not rehashed in this step.

The selected interval contains 355 contiguous instructions covering all 1,606 bytes. Their bytes match the pinned patch; the selected-code SHA-256 is `713a9ec86835d5b313789bd5fff7f386ce29b0c65f14394155657012a74dfd60`. The actual E8 instruction at `0xCFC660` targets `0x115AB90`. There are 28 direct call instructions and 55 direct branch instructions. Every direct non-call target stays in the selected interval.

The exporter checked the combined UTF-8 ASM and quality-JSON size before creating its output files: 19,575 + 2,083 = **21,658 bytes**, within its **32,768-byte** cap. Logs, scripts and receipts are separate provenance. This successful cap check does not alter the separately preserved size-limit failure from the earlier full exporter.

The selected record begins without a prologue. Complete-function context, inherited register bindings and a full high-level CFG are not established by local instruction coverage or by the absence of direct branch targets outside the interval.

## Request source at the explicit stores

At `0xCFC651`, RCX becomes `RBP+0x350`; the call at `0xCFC660` passes that request pointer to `0x115AB90`.

| Request field | Observed source and store |
| --- | --- |
| `input+0x1C` (`RBP+0x36C`) | `0xCFC1DB` reads DWORD `[RSI+0x19118]` into EAX; `0xCFC1E1` stores EAX in the field. |
| `input+0x18` (`RBP+0x368`) | `0xCFC1EE` stores inherited R14D. The local R14D zeroing at `0xCFC1F5` occurs afterward, so it does not establish a zero value for this store. |

RSI's owner and the formal meaning of member `+0x19118` are not bound in this fragment. No concrete field value, including `41810` or `98348`, was observed.

There are **20 static call sites** between the `+0x1C` store and the AB90 call; some are conditional or in loops. This count is not a runtime execution count. Three `N=0x10` helper destinations (`RBP+0x3A98`, `+0x3AA8`, `+0x3AB8`) lie inside the bulk-request extent. Earlier pointer escapes are unknown, and opaque-helper effects and indexed/indirect-store alias contracts are not closed. The selected instructions show no later direct literal rewrite of `[RBP+0x36C]`; that observation does not prove the value at AB90 or copy-helper entry.

The existing fixed-`N=0x4180` copy receipt conditionally maps source `+0x18/+0x1C` to mapped-buffer `+0x48/+0x4C` for the source snapshot at copy-helper entry. Its readable/writable-range, no-overflow, normal-completion, no-concurrent-mutation and REP-direction-flag conditions still apply. AB90's preceding CAS and buffer-flag helper call are another boundary. The receipt does not prove stability from the earlier caller stores or parity for every copy length.

## Numeric post-call result mapping

For normal paths following the return from AB90, the selected instructions implement this mapping. R13's formal output-object binding is not established by this fragment.

| AB90 return | Observed effect |
| --- | --- |
| `1` | Call unresolved helper `0x2923D0` at `0xCFC66C`, then write QWORD `[R13]=0` at `0xCFC671`. |
| `2` | Select code `0x9` at `0xCFC693`; write DWORD `[R13]=2` and DWORD `[R13+4]=code`. |
| `3` | Select code `0xA` at `0xCFC68C`; perform the same tag/code stores. |
| Any other value | Select code `0xE` at `0xCFC685`; perform the same tag/code stores. |

All these paths reach the common DWORD `[R13+8]=9` store at `0xCFC6A8`; the retained epilogue places R13 in RAX. The numeric codes have no authenticated human error labels or download semantics. This caller has no observed AC30 fallback call, unlike the previously documented CFB680 caller.

## Evidence boundary and next source

The next source frontier is the owner and producers of DWORD `[RSI+0x19118]`. The separate controller/loader witness for CFB680 does not bind this fragment's RSI or supply a value for this member. No additional native expansion was performed after this export.

This stage used the offline `static_native_analysis_lane`: no Computer Use, game/client launch, target-code execution or IPC send. It establishes neither an actual old-build request nor an acquisition/downloader path, playback compatibility or completed replay conversion. Machine-readable pins and limits are in [the paired observation](../observations/main-ipc-second-request-caller-2026-10-25.json).
