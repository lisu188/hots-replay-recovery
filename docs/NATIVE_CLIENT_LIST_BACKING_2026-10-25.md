# Native client-list backing argument link

The selected third-member helper now connects to the list address selected by
the getter's discriminator2 branch. At RVA `0x6BAFB4`, helper `0x6BAF50` passes
source and destination subobjects at offset `0x120` to `0x6B5BA0`. Its previously
verified caller uses third-member offset `0x4310`; adding `0x120` reaches
`0x4430`, the getter's selected list address. This establishes the argument and
address link. It does not identify the third member or supply historical values.
The earlier [getter observation](../observations/native-client-list-getter-2026-10-25.json)
retains the separate receiver and discriminator boundaries.

## Two different analysis boundaries

| Entry | Selected bytes | Instructions | Selected control flow |
| --- | ---: | ---: | --- |
| `0x6BAF50` | 392 | 84 | Six direct calls, two internal conditional branches, RET at `0x6BB0D7` |
| `0x6B5BA0` | 31 | 10 | Pointer-equality branch and unequal fallthrough both leave the fragment; no RET |

All 392 bytes of the first selected record are decoded contiguously. Its six
relative calls and two internal branch targets were checked against the saved
bytes. External callees remain separate contracts. A complete selected record
and its RET do not establish a complete deep copy, unique metadata extent or
whole-engine control-flow graph.

The 31-byte entry fragment retains the source and destination pointers, compares
them, and branches to `0x6B5F95` when they are equal. That target lies outside the
selection. On unequal pointers, it reads 64 bits at each container base and
falls through to `0x6B5BBF`, also outside the selection. No container store or
element iteration appears in this fragment. The equal-pointer path is not yet
proved to be a no-op or return.

Both selected exception-table floor records begin at their requested entries.
Unique covering records and nonoverlap were not proved. The second record is
explicitly a fragment, despite its metadata boundary.

## Consumer geometry remains separate

Retained `0xDFE7D0` consumers read 32 bits at the returned list base at
`0xDFF516` and `0xDFF90C`. Their first record is at `+0x8`, with stride
`0x360`, or **864 bytes**. Those observations do not turn the new fragment's
64-bit loads into a proved count or copying contract.

The distance `0x3728 - 0x120 = 0x3608` is **13,832 bytes**. It equals
`8 + 16 * 864`. This is a layout consistency calculation; it does not independently
prove a sixteen-record capacity, an array extent or a required record count.

## Source and next boundary

The source client is build **98348**, length **53,573,840 bytes**, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction evidence uses an analyst-derived statically transformed text patch,
length **36,581,376 bytes**, inherited SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
This is neither runtime capture nor unaltered on-disk PE text.

The two cited selections used 432 bytes of PE exception-table metadata and 423
patch bytes. Their source-identity guards matched, and both bounded IDA analyses
exited zero. Target code and the game were not executed. Safe source fingerprints
and selection boundaries are in the accompanying
[observation](../observations/native-client-list-backing-2026-10-25.json).

Next decode the actual fallthrough `0x6B5BBF` and equality target `0x6B5F95`, then
authenticate element-copy behavior and the incoming source producer. List-copy
semantics, historical player values, discriminator2 meaning, runtime object
continuity, synchronization parity and playback remain unresolved. This
milestone changes no codec or replay and assigns no defaults.
