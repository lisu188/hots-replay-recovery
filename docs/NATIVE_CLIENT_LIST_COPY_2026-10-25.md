# Current client-list copy paths — 2026-10-25

The native list-copy code separates existing-record assignment, appending and removal. On the append path, it directly forwards the source player-level DWORD and boost byte into the new ClientInfo record. Existing records go through a separate helper whose field behavior remains unresolved. These findings establish current native data flow; they do not provide historical values or authorize defaults for TEN_GREYMANE.

This follows the [backing-list address proof](NATIVE_CLIENT_LIST_BACKING_2026-10-25.md), published at commit `4817630ad65419b17c0f8121d7ae695651fb16a5`. The [structured observation](../observations/native-client-list-copy-2026-10-25.json) contains the source pins and scope limits. Addresses below are RVAs; record displacements are hexadecimal.

## Scope and conditions

The analysis used the existing analyst-derived, statically transformed 98348 text patch. It is not runtime capture or unaltered on-disk PE text. A 31-byte entry, a 982-byte continuation and a separate 10-byte self-exit join into 1023 bytes and 196 decoded instructions. All decoded inline conditional targets are inside those joined spans; six external callees remain open. The individual RuntimeFunction records are fragments, so their ends are not treated as whole-function boundaries. Two new hidden IDA batches completed with exit0, using empty databases and no PE input or execution of decoded game code.

Source-value forwarding is conditional on valid initialized source/destination storage, counts consistent with accessible record ranges, nonoverflowing address arithmetic and valid accesses. Helpers must return normally and preserve the nonvolatile registers required by the ordinary ABI. Counts and relevant source bytes must remain stable across intervening calls except for the stated destination-count updates. Overlap, aliases and callbacks must not modify unread source bytes, headers or object lifetime. These conditions have not been established for a runtime replay instance; arbitrary overlap-safe snapshot copying is unproved.

## Count and record handling

The helper loads and updates **64-bit QWORD counts**. The retained DFE7D0 consumer instead loads the header through **32-bit DWORD operations** at DFF516 and DFF90C. This width difference remains explicit; no general equivalence is inferred.

For distinct list pointers, the existing-record loop uses the unsigned minimum of the counts. It passes records at `list+8+i*0x360` to `6B9A50`, advancing by `0x360` (864 bytes). It reloads both counts after that opaque helper, so treating the loop as a snapshot of the initial counts requires the stability conditions above.

When the destination count is smaller, the append path uses its current count as the new index and increases that count after construction. When it is larger, the shrink path decreases it and calls cleanup helpers. Complete nested assignment and cleanup effects remain unresolved. The equal-pointer branch at `6B5F95` returns the destination through its decoded epilogue, with no explicit container write or helper call on that path.

## Appended fields and the unresolved variant

The record base is `list+8+i*0x360`. The append path contains two direct transfers:

| Current native field | Record offset | Load → store | Transfer |
| --- | --- | --- | --- |
| `m_playerLevel` | `+0x358` | `6B5EE5 → 6B5EEC` | Source DWORD to destination DWORD |
| `m_hasActiveBoost` | `+0x35C` | `6B5EF3 → 6B5EFB` | Source byte to destination byte |

The corresponding list-relative operands are `+0x360` and `+0x364`; subtracting the eight-byte record header gives the pinned native field offsets. These are append-only source transfers under the stated conditions. They do not establish existing-record behavior, Boolean normalization, absent-wire-field handling or the values that the old replay should receive.

For SharedPlayerInfo at record `+0x2BC`, the append path first writes sentinel `0xFFFFFFFF`, then calls `6BADE0` at `6B5E49` with the corresponding destination and source variant addresses. Branch-tag and InfoHero flag transfer remain unproved. The sentinel is initialization, not a migration default.

The next concrete targets are `6B9A50` for existing-record assignment and `6BADE0` for variant construction. This milestone changes no production codec or replay. Historical source values, the upstream request builder, full conversion, native playback and synchronization compatibility remain unresolved. No new exact-head CI result is claimed here.
