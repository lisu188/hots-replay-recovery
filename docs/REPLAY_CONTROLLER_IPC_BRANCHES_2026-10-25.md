# Replay controller IPC branches — 2026-10-25

Saved static evidence connects the owner passed to request caller `CFB680` with
a controller that also has a recorded `replay.initData` loader path. The two
paths are alternative branches. The request branch returns before the loader
branch, so this evidence does not establish a sequence in which loading a
replay causes an IPC request. It also does not identify a producer of the
replay executable build or data build.

The machine-readable evidence and exact source pins are in
[`replay-controller-ipc-branches-2026-10-25.json`](../observations/replay-controller-ipc-branches-2026-10-25.json).
All code addresses below are RVAs in the current main-client evidence.
Repository baseline: `e1dac1d56bf6be1df37939bec77ba988fa7c566f`.

## One entry object, two alternative branches

Function `D000D0` retains its incoming `RCX` in `RBX` at `D000E2`. Call this
entry object `M`. The selected record is `[D000D0,D00219)`, with 90 instructions,
completed decompilation and zero decompiler blocks outside that record.

| Branch | Conditions and observed call |
| --- | --- |
| Request preparation | Common entry/status guards pass, `DWORD[M+106C8] == 0`, and `115AA10` returns `AL == 0`. `D0014D` supplies the same `M` as `RCX`; `D00150` calls `CFB680`. This branch returns before the alternative loader branch. |
| State/loader continuation | The alternative branch constructs or reuses a state. A virtual `+10` result other than `2` permits continuation. `D001D2` supplies the same entry object as `RCX`; `D001F1` calls `CFE3B0`. |

This is a static object-flow witness. A native class name, runtime instance
lifetime and actual execution order remain unresolved.

## Mode selection and the recorded loader

`CFE3B0` retains its incoming owner in `RBX` and reads `DWORD[M+100E8]` at
`CFE3F3`. The comparison at `CFE439` and branch at `CFE43C` send mode `2` to
`CFEA2D`, the recorded-stream route. That route calls `134DD30` at `CFEC51`.
Existing member-decoder evidence binds `134DD30` to `replay.initData`; the
decoded-configuration copy targets `M+19460` at `CFECDB`.

The retained state wrapper `E01EA0` also loads this mode field at `E01EC7` and
uses `unsigned(mode-2) <= 2` to select modes `{2,3,4}`. These comparisons identify
`M+100E8` as a numeric mode selector. They do not identify it as an executable
build or data build.

## Request-value boundary and next step

In the already captured `CFB680` request preparation, `CFBA16` explicitly
writes sentinel `FFFFFFFF` to `input+1C`. The source value when the later copy
helper begins remains unproved. Within this owner pair and the captured
`CFB680` route, `input+1C` has no authenticated replay-executable-build or
data-build meaning.

The separate replay-version path `20EA0C0/20EA1D5`, including error `20010010`,
is not used to infer this owner identity or IPC result `3`.

The next step is to trace the explicit `RSI+19118` producer and its context
in the companion second-caller observation. This owner pair does not establish
that receiver's identity or assign replay-build semantics to the field.
Branch, lifetime and aliasing conditions remain part of that investigation.

This preparation used only reviewed text evidence. It performed no new PE,
patch, dump or process-memory reads, native analysis, target execution, game
launch, Computer Use, IPC or replay access. No runtime request value, historical
payload acquisition or working replay upgrade is proved.
