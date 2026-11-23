# Build 98348 checksum history

The gameplay publisher can copy 72 words without recomputing a full checksum vector. RVA `0x132dda4` publishes the current sample, `0x132ddae` calls the recorder, and the ordinary tick increments the frame before advancing the world at `0x132de64`. The chained PE unwind record links the mode-4 sampling call at `0x985b88` to this world tick.

| Operation | Result |
| --- | --- |
| Request current vector, `0x986f20` | Calls `0x989810`, then copies counted words from history entry `count-1`. The on-disk history count and pointer start at zero. The copy assumes a valid latest entry. |
| Deferred build, `0x989810` | When count exceeds one and `(count-2).processed` is zero, builds mode 0 on that predecessor, marks it processed, and copies the whole entry to latest. Other requests skip the build. |
| Latest tick sample, `0x987d10` mode 4 | Clears both data arrays while preserving the count. If world flags bit 6 is clear, writes only slot 0 and returns before writing the processed flag. All 71 other counted words are zero. |
| Mode 4 with bit 6 set | Calls the 70-slot primary producer, skips the 92-component aggregation and marks latest processed. Slots 3 and 69 remain zero. |
| Mode 0 | Runs the primary and aggregate producers and sets the processed flag. |

Fast slot 0 is CRC-32 over five consecutive little-endian DWORDs in order: `world+0x0c`, the decoded field at `world+0x14`, `world+0`, `world+4`, and the scalar at RVA `0x34ef5c0`. The allocating constructor sets `world+0` to `0xffffffff` and `world+4` and `world+0x0c` to zero. The world reset also writes zero to the final scalar. The values at allocation and reset alone do not give the five words sampled after ticks and player setup.

The type-7 user option at event offset `+0x34` records `m_syncChecksummingEnabled`. The receiver updates the corresponding physical user bit at `+0x4a`. The option application loop tests active users 0 through 15. An active user missing the bit clears world flags bit 6 via `0x97aa10`. TEN records false for users 0–9 at loop zero. All 254 opening options across the 24 independent build-98348 controls also record false. This supports the fast branch after normal option application. The source replay physically contains 308 type-2 records and the controls contain 7,501. Every sequence begins at 64 and advances by 64. These recordings omit the history vector and the native branch indicator.

The mod checksum at `0xe04850` uses a different entry selector. Its lookup at `0x980570` calls the same deferred helper, then copies the record indexed by global RVA `0x34f0200`. On the validated stored-state loading path, `0xcfa47c` compares this mod checksum before `0xcfa504` calls the map loader. Its successful path reaches `0x6ac960` via `0xe04c7e` and calls `0x97d870` with `edx=1,r8d=0`. This appends two fresh entries with 72 counted words. The branch at `0x97dad1` preserves the selected mod index. The prior mod record and the new latest map record can coexist. A mod-checksum match alone cannot identify the first gameplay vector.

For a fixed, initially pending pair under fast mode 4, with no intervening history changes, 65 consecutive publication/tick cycles consist of one mode-0 build and 64 fast samples. A fresh pair inserted immediately before the last publication changes those counts to two and 63. The map-loading calls establish one real boundary. Additional direct append paths in stream readers and a virtual setup interface, plus pair removal and deferred reads during loading, leave the actual predecessor flag and pair lifetime at TEN's first publication unresolved. The verifier reports the loop-64 type-2 value as unknown.

Run `python verify_sync_history_cadence.py EXE STATIC_TEXT TEN_REPLAY CONTROL_PATHS_JSON` with the repository modules on the Python path. The controls JSON maps the repository's 24 pinned SHA-256 values to local replay paths. The verifier checks whole-file identities, code-window digests, direct calls, unwind metadata, a native field table, exact sync re-encoding, and both conditional recurrence cases.
