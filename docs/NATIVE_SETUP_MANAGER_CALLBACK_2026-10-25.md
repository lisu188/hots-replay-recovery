# Native setup manager callback — 2026-10-25

The indirect setup callback at `E03E65` now has a constructor and table trace.
The observed mode-1 implementation copies an existing user setup into an
operation queue. It does not supply the missing historical ClientInfo level,
boost, staff or voice values. This closes a concrete static dispatch question;
it introduces no new conversion assignment or replay checkpoint.

The sanitized evidence is
[`native-setup-manager-callback-2026-10-25.json`](../observations/native-setup-manager-callback-2026-10-25.json).
All RVAs below refer to the pinned installed 98348 PE, image base `140000000`.
No game, Battle.net or Computer Use was used. No replay or member was read or
written during this trace. All five Ghidra jobs used the existing project with
`-readOnly -noanalysis`; their changes were discarded.

## Receiver initialization

The known caller obtains staging through `G.virtual1A8` and calls slot `E0` of
`J = QWORD[143941CF0]` with arguments:

```text
J, 1, staging+8, initialized stack local, staging+E198
```

A scan restricted to one exact global and seven-byte REX.W RIP-relative
MOV/LEA forms found 156 load candidates and one store candidate. These are
candidate counts, not an exhaustive write or alias analysis. The initial
128-candidate cap stopped the first attempt; its marker was retained. The
bounded second attempt retained stores and the known caller control.

The store at `1361EE1` initially fell inside an unwind fragment whose entry
skips it. Exporting the two preceding exact unwind records recovered the
reachable `1361C90` body and authenticated this initializer:

| Initializer mode | Allocation size | Constructor | Primary table installed | Table slot E0 |
| --- | --- | --- | --- | --- |
| 1 | `218` | `136BE10` | `27CB118` | `136C0F0` |
| 3 | `1D98` | `1362FB0` | `27CAAF0` | `1364890` |
| 4 | `45B8` | `136D470` | `27CB308` | `136D8B0` |

Modes 3 and 4 require nonnull `QWORD[143B7C6B0]`. Other modes return
`20020001`. An already nonnull J returns `20020005`. Each allocation branch
stores its constructor result in J, then returns `20020000`. Allocation failure
instead stores null and still returns `20020000`: that status alone does not
prove a usable receiver.

The existing caller `13297D0` supplies its second argument as the initializer
mode. It constructs the separate fixed G object only after `20020000`.
This proves an initialization order, not `G = J`. These constructor modes
1/3/4 are distinct from the recorded selector `M+100E8 == 2`.

Each reviewed constructor installs its visible primary table once and returns
the original object pointer. The mode-3 helper `1368900` registers `object+8`
through `2DE170/2DE340`; its visible stores target returned registry entries.
It contains no direct primary-table store. Registry-helper effects and later
receiver lifetime or replacement are not universally closed by this trace.
The table associations remain conditional on those effects preserving them.

Only three fixed eight-byte table cells were read from `.rdata` (24 bytes).
Both other targets begin with `B8 01 00 02 20 C3`, which decodes directly to
`MOV EAX,20020001; RET`. No absent unwind boundary was invented for these
six-byte prefixes. Their execution and actual receiver selection remain
unobserved.

## Mode-1 callback

The exact unwind entry `136C0F0` and its complete bounded listing show:

1. Set J state at `+14` and `+18`.
2. Save incoming R8, which is `staging+8` at the known caller.
3. Construct one local user record, stride `C30`, then copy the source into it
   through `CF9D70` at `136C1BA`.
4. Allocate a `C3C0` operation object and set discriminator `10028` at `+10`.
5. Copy the local user through the same `CF9D70` at `136C286` into a queued
   record with stride `C38`.
6. Pass that object to `20E8E30(J+208, object)` at `136C29F`, then return
   `20020000`.

The known copy routine transfers optional presence at `+164` and its u32 value
at `+168` from the same source offsets to the destination. This is a transport
of an already-present setup record. Neither the callback body nor this copy
establishes a producer from ClientInfo `+358` or a historical default rule.
The body has no direct use of the incoming fourth or fifth arguments. This
is not a universal purity claim about its allocator, copy or queue callees.

## Verification and remaining work

Eight bounded exports across five read-only Ghidra jobs completed without
truncated expanded listings. Exact unwind records can be fragments; the
receipt records blocks outside each selected interval instead of treating
each interval as a complete high-level function. The RIP recognizer passed
96 synthetic register/opcode/displacement forms and a non-target control.
The publication preparation checked the specific caller, constructor,
copy and queue instructions against the retained listings and bound all
source evidence with SHA-256. A separate reviewer checked the register flow,
return values and constructor qualifications. These are static checks.

The production setup and whole-lobby codecs from `d37700a` and `bb57233`
are unchanged. Their existing tests and current-replay round trips remain
separate evidence; this documentation adds no runtime or playback claim.

Full recovery remains unfinished. R8 (`98285-resumable-r8`) remains the latest
replay. Current-only account/player value rules, resource identity and
ownership, historical catalogs and deterministic synchronization still need
authenticated migration rules. No guessed flags, copied donor values,
constructor defaults or altered synchronization data were introduced.
