# Source of the build 98348 sync word

On the ordinary eligible frame, producer `0x132fcf0` reads the current 32-bit state from `G+0xa13c4` and stores `(state >> 16) ^ (state & 0xffff)` in the type-2 record. The previously recovered frame accumulator `0x132f610` XORs the raw frame-state CRC with the vector CRC, then advances that raw CRC over four zero bytes. The frame-state input includes the prior accumulator, setup and ordered queue. This leaves the live simulation inputs to recover.

## Counted vector on the recovered history path

The `R8D == 0` branch of `0x97d870` makes the last history entry's count 72. Its growth loop at `0x97d9f0` initializes added words to zero. A second entry is prepared and `0x97dacc` calls `0x977ef0` to copy the preceding entry into it. Each history entry occupies `0x588` bytes. The deferred mode-0 path `0x989810` can fill the preceding entry and copy it again. Frame accumulator call `0x132f715` retrieves the latest counted vector via `0x986f20 → 0x977e40`. Under this 72-word state, the native type-815 serialized vector occupies 289 bytes, with one count byte followed by 72 32-bit values. The traced resize is conditional, and later writers can change state.

| Zero-based vector slot | Recovered upstream source |
| --- | --- |
| 0 | The result of `0x985bb0` goes to `entry+8`. |
| 1 | Standard CRC32 of the little-endian native DWORD at RVA `0x34ef5c0`, stored at `entry+0xc`. |
| 3 | Standard CRC32 of the concatenation of 92 little-endian component words in their native order. Component `i` is the complemented output of `0x15fc810` and is also stored at `entry+0x408+4*i`. The aggregate goes to `entry+0x14`. |
| 7, 37 | The two paths through the primary builder each complement an untouched all-ones CRC and store zero. [Checked instructions](CONSTANT_SYNC_SLOTS.md) |
| 69 | The builder resets the four bytes at `entry+0x11c` before selecting its mode. A fresh mode-0 computation yields zero. A hydrated entry can contain a value supplied by the stream. [Reset, copy and deserialization](SYNC_SLOT69.md) |

Primary builder `0x9707a0` has 70 distinct direct stores to the 72-slot vector. Mode-0 builder `0x987d10` also supplies slot 3. Its 92 component words begin beyond the serialized 72-word payload. The TEN replay retains folded checksums. Reconstructing the target values requires the per-frame simulation inputs and the history path actually used.

`verify_sync_vector_source.py ORIGINAL_PE PINNED_STATIC_TEXT` checks the two whole-file hashes, resize/copy branches, producer bindings, all 70 direct store destinations, and the native tables against eight synthetic one-word and 92-word CRC cases. `native-sync-vector-source.json` contains the reproduced result. Analysis used headless static IDA and prior authenticated Ghidra listings.
