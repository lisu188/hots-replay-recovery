# Selector2 source pointer - 2026-10-27

The current native code sets discriminator2 and copies its payload from an existing source pointer. The newly qualified caller loads that pointer from the incoming object's `+0x18` field. This advances the source trace for the current ClientInfo list; it supplies no historical player values or conversion defaults.

This extends [ClientInfo source transfer](NATIVE_CLIENTINFO_SOURCE_TRANSFER_2026-10-25.md). The [structured observation](../observations/native-selector2-source-2026-10-27.json) records the static witnesses. Addresses below are hexadecimal RVAs; offsets describe native memory rather than wire positions.

At `CC1630`, the selected 451-byte prefix includes the actual instruction at `CC1647` that writes DWORD2 to `[RCX]`. After saving this receiver in RDI, `CC1667` calls `6BAF50` with destination `receiver+0x4310` and the source pointer in RDX. The preceding `1A24E60` helper has now been decoded separately through its return: it preserves RCX and RDX, probes stack memory and calls no further functions. Argument preservation here requires normal return, a valid stack, and the ordinary ABI; stack faults and hostile aliases are not covered.

The prior `6BAF50` witness calls `6B5BA0` on payload `+0x120`. Consequently this selected call passes `receiver+0x4430` and `source+0x120` as list addresses. This is an address relation at the call boundary. It does not prove list contents survive every helper, callback, alias or later operation.

One fixed-target E8/E9 scan of the authenticated transformed text found a single raw direct caller of `CC1630`, at `CD6D95`. A separate 506-byte IDA decode qualifies that call. In this body, RSI retains the entry RDX object pointer. At `CD6D83`, `RDX = QWORD[RSI+0x18]`; at `CD6D87`, RCX receives the result of `CBEF50`; and `CD6D95` passes those arguments to `CC1630`. The type, lifetime, creator and contents of that incoming object remain unresolved. This scan says nothing about indirect calls or references outside the selected transformed text.

The same decoded body later copies the receiver's tag and payload into the object returned by `25A480`: the tag at `CD6E59/CD6E5B`, and payload `+0x4310` via `CD6E83 -> 6BAF50`. Several opaque calls intervene. The later tag is therefore a fresh load, not an unconditional proof that it still equals2; unchanged payload values across those calls also remain unproved.

Three hidden IDA9 batches completed with exit0 in fresh empty databases. They decoded 1,038 bytes into 208 instructions. The `CC1630` prefix ends at its hard boundary without a return; it is not a complete function or CFG. The other two selected records reach their returns, with their observed local branch targets on decoded instruction boundaries. The byte source remains the existing analyst-derived static text patch, not an original unaltered PE section or runtime capture. No game code was executed.

The next source question is who fills the incoming object's `+0x18` pointer and its pointee. Discriminator2 is still unnamed; it must not be equated with a particular replay or offline schema by analogy. This milestone changes no codec, archive, catalog mapping or replay. Full historical conversion and playback remain unproved.
