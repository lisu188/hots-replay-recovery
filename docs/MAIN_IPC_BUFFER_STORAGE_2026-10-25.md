# Main-client IPC buffer storage - 2026-10-25

The pinned 98348 client contains a static chain from its product IPC name to a
name-pointer global, two indirect calls, a stored result pointer and an atomic
operation on that result's `+0x20` field. This identifies the main client's
storage and state-operation path. The actual API identities of the indirect
calls remain unproved, so the mapping/view interpretation is an inference.

The [companion observation](../observations/main-ipc-buffer-storage-2026-10-25.json)
records source hashes, addresses, export quality and limits. Addresses below
are RVAs. The source is the 53,573,840-byte `HeroesOfTheStorm_x64.exe` build
98348, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.

## Name and pointer ownership

The [earlier product-table result](MAIN_PRODUCT_IPC_TABLE_2026-10-25.md)
located the constructor and its `Heroes of the Storm IPC Mem` literal.
The product-object getter `0x1384490` calls the record getter at `0x13844C1`,
then invokes record `+0x20` at `0x13844CD` with destination object `0x3A26CA0`.
The getter returns that product object. Its name field is product `+0x340`,
slot `0x3A26FE0`; it is distinct from the constructor pointer in the record.

Initializer `0x176130` calls the product-object getter at `0x176134`, reads
product `+0x340` at `0x176139`, and stores the name pointer into global
`0x2FE3F78` at `0x176140`. Consumer `0x115A4D0` reads this global at
`0x115A4E3` and supplies the pointer as the sixth argument of its first
indirect call.

| Location | Confirmed selected-ASM behavior |
| --- | --- |
| `0x115A507`, slot `0x262E4A0` | Calls with `(-1, 0, 0x08000004, 0, 0x10000, name)`. |
| `0x115A52B`, slot `0x262E630` | If the first result is nonzero, calls with `(first result, 2, 0, 0, 0x10000)`. |
| `0x115A539`, slot `0x262EAC8` | If the second result is zero, passes the first result to this cleanup call. |
| `0x115A54C` | On second-result success, writes the first result through the incoming out pointer and returns the second result. |

The argument and ownership sequence is consistent with the official
[CreateFileMappingA contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createfilemappinga)
and [MapViewOfFile contract](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile).
This is an inference from the sequence. The three pointer slots above have no
authenticated API names in this result. No runtime mapping was observed.

## Returned-pointer storage and atomic state

The bounded decoded-patch scan yielded one E8 candidate for `0x115A4D0`,
confirmed as a real call at
`0x115A796` in the selected record beginning at `0x115A760`. The caller passes
out-pointer global `0x37EBC58`, then stores the returned second result in
global `0x37EBC48` at `0x115A79B`. These are separate storage locations for
the first and second results.

After testing the returned pointer for zero, the caller forms its `+0x20`
address at `0x115A7B0` and calls helper `0x115A0B0` at `0x115A7B8`. EDX is 1;
`LEA R8D,[RDX+3]` makes the expected value 4. The helper's first eight bytes
move R8D to EAX, perform a locked DWORD compare-exchange from EDX through RCX,
and return. This attempts **4 to 1** on the returned pointer's `+0x20` field.
The prior DWORD value is returned and stored in global `0x37EBC50` at
`0x115A7C4`. No live value of any global or field was read.

The factory record, product object, name-pointer global, returned-pointer
global, out-handle candidate global and cached prior state are distinct
owners. This chain supplies a concrete receiver for the `+0x20` operation;
it does not assign IPC state to product `+0x20` or record `+0x20`.

## Export boundaries and remaining work

| Selected RuntimeFunction interval | Bytes | Selected / expanded instructions | Outside blocks |
| --- | ---: | ---: | ---: |
| `0x176130..0x17614C` | 28 | 6 / 6 | 0 |
| `0x115A4D0..0x115A55A` | 138 | 36 / 36 | 0 |
| `0x115A760..0x115A89D` | 317 | 70 / 149 | 19 |

All three Ghidra jobs completed in the existing project with `readOnly`,
`noanalysis` and two CPUs; their logs confirm discarded changes. The third
selected record is a fragment. Its expanded output is not size-truncated,
but 19 blocks lie outside the selected record, so it is not a complete CFG
claim. The name, pointer-storage and compare-exchange chain above is present
in the selected ASM and does not depend on those outside blocks.

The separate 64-byte objdump window for `0x115A0B0` is not a `.pdata` function
export: no RuntimeFunction covers that entry. Only the first eight bytes
through its first RET are classified here. Trailing window bytes remain
unclassified. Native export payloads, including that window and its decoding,
total 32,288 bytes, below 64 KiB. Six candidates were retained, below 32;
three `.pdata` records were exported, below four. The private receipts retain
failed-selection and repair attempts as well as actual read accounting.

The missing-build state-3/result-3 consumer and downloader remain unresolved.
No historical 41810 payload or first replay simulation mismatch was recovered.
No game launch, Computer Use, IPC send, replay read/write or
sync modification occurred. Full replay upgrade and playback remain unproved.
The public pair contains source fingerprints and summarized static facts;
raw PE/ASM and private filesystem paths are excluded.
