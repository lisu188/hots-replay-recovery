# Registry array and callback arguments - 2026-10-27

Static initialization now identifies the storage containing the selector2 callback slot. The callback helper also forwards its incoming argument pointer directly at both covered call sites. These findings extend [the callback binding](SELECTOR2_CALLBACK_BINDING_2026-10-27.md); the producer and historical contents of that argument remain unresolved.

All addresses and offsets below are hexadecimal. The [observation](../observations/registry-array-and-callback-arguments-2026-10-27.json) pins the selected native witnesses. They come from the existing analyst-derived static 98348 text patch, not runtime capture or an unaltered PE section.

## Storage and lifecycle

The selected initializer requests `0x930` bytes. On its nonnull path, it initializes 251 eight-byte slots at `object+0xD8+i*8`, ending at `+0x8B0`. Each iteration calls `2DD9A0`, whose eleven-byte body writes a null QWORD and returns the slot address. The object also receives a separate table pointer at `+0xD0`, immediately before the array.

Consequently `object+0x4A0` is physical array element121, or `embedded_base+0x3D0` when the embedded base is `object+0xD0`. This is an address calculation, not a recovered event number, schema type or historical resource identity. Empty callback slots do not supply defaults for missing historical ClientInfo values.

At `1D836CE`, the initializer publishes its candidate pointer to global `3B7C6B0` before calling `1D83080` with the candidate and the initializer's original first argument. The covered failure path includes cleanup and a zero store at `1D8370E`; the separate shutdown path clears the global at `1D84A4C`. These observations do not establish thread safety, successful initialization, or the candidate's stability through opaque cleanup and virtual calls.

The two original-PE words preceding the selected primary/secondary table addresses point into code and did not authenticate the expected RTTI locator format. No class name was recovered from this route. This is not a claim that RTTI is absent throughout the executable.

## Argument passed to callbacks

`2DDC10` saves entry RDX in R12 at `2DDC2C`. Its two covered callback branches reload RDX from R12 immediately before calling the listener:

| Argument reload | Callback call | Receiver form |
| --- | --- | --- |
| `2DDD87` | `2DDD8A` | Untagged key, virtual call at receiver table `+8` |
| `2DDD9C` | `2DDD9F` | Tagged key with bit0 removed, stored function pointer |

The second branch matches the previously observed slot containing `CD1660`, conditional on that slot being the same valid list node and remaining stable until read. The thunk then forwards RDX to `CD6D30`, which reads its `+0x18` pointee. This proves pointer forwarding at the covered boundaries; it does not snapshot the pointed-to contents, guarantee which callbacks run, or exclude writes by earlier callbacks, aliases or concurrent activity. Normal ABI preservation and valid list/receiver storage are required.

A search for callers of this helper near the derived slot offsets produced eight raw candidates. The selected `CDF300` caller uses its incoming receiver plus `0x4A0`; equality of that receiver with global `3B7C6B0` has not been established. Matching the displacement alone therefore does not authenticate the requested producer.

The four core witnesses cover 1,310 bytes and 351 decoded instructions: initializer, shutdown, empty-slot helper and callback helper. GNU objdump 2.42 completed each read-only decode, and the instruction-byte columns were checked against guarded source bytes. No new analysis database, game process, codec change, replay, historical default or playback result was produced. The next source task is to bind a candidate sender's receiver and argument to this exact registry slot.
