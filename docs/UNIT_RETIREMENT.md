# Build 98348 unit retirement

The native unit phase at RVA `0x999690` visits the active list twice. The caller invokes this phase at `0x985a60` and drains the pool's pending list later at `0x985b0f`. The release pass refreshes the head at `0x9997d2` after the first pass. For each current node, it saves the successor from the 16-bit link at unit offset `+0x14` before checking the current node. Allocation prepends at `0x990c66`. With stable list membership and ordering, eligible units retire in reverse order of activation. Reentrancy and other list mutations can change the traversal. Tracker creation order alone does not establish the active links.

| Release pass condition (in evaluation order) | Result |
| --- | --- |
| Current unsigned game clock below unit `+0x94` | Skip this unit. |
| Byte `+0x39` has neither bit in `0x06` after state updates | Skip this unit. `+0x3b & 0x20` gates one update, and `+0x39 & 2` can invoke another. |
| Signed countdown `+0x90` is positive | Subtract the current debit and advance to the saved successor, even if the result reaches or crosses zero. |
| Countdown nonpositive and mode `+0x3d & 0x10` | Clear `0x10`, update a separate field at `+0x30`, read the descriptor's signed `+0x98`, set final bit `0x20` if the value is nonnegative, or clear it otherwise. Store the countdown clamped to zero and advance. |
| Countdown nonpositive, stage clear, final bit set | Call cleanup at `0x99996e` and retire at `0x999976`. Otherwise advance. |

The debit helper reads a global initialized to 4096. Its signed fixed-point multiply shifts right by 12 and clamps negative output to zero. Replay-loop cadence and the dynamic scale still require independent evidence.

The Galaxy registry and VM jump table bind `UnitKill` (1460) and `UnitRemove` (1459) to distinct native handlers. A resolved `UnitKill` jumps to `0xaa91c0` with a null context. A resolved `UnitRemove` performs a preliminary update then invokes `0xaaad70` with mode `0x10`. One path calls the same marker with a populated context. `UnitGetTag` (1466) returns the packed input value.

On the timer-initializing path, marker `0xaa91c0` sets `+0x90` to 1 and sets the final bit when `unit+0xa1 == 1`. Otherwise it selects the descriptor through `unit+0x18` or `+0x20` according to `+0x3a & 4`. Positive descriptor `+0xb8` arms the stage and supplies the first countdown. Otherwise the sign of descriptor `+0x98` controls the final bit and the initial countdown is at least 1. One subsequent branch sets `+0x39 |= 2` if this unit is currently being processed or signed byte `+0x5a` is positive. The other calls `0xaa6bd0`. The complete stage helper at `0x99d2b0` only writes `+0x30`. Other callees and indirect callbacks can affect state. A full reference-count criterion, exact tracker-death-to-retirement schedule, and per-unit descriptor values for TEN_GREYMANE remain unresolved.

Run `python -B -m unittest -q test_unit_retirement` for the bounded model and `python -B verify_unit_retirement.py ORIGINAL_PE PINNED_STATIC_TEXT` for the instruction, literal, and jump-table checks. The latter emits the receipt in `native-unit-retirement.json`. All executable analysis used static IDA.
