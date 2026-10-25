# Main-client IPC request and response handlers - 2026-10-25

The pinned 98348 client produces request state 2, checks for response state 3,
and reads the result at buffer `+0x24`. Its generic request routine returns
result 3 unchanged while clearing the state. This closes a concrete main-side
response-consumer path. The selected producer supplies the sentinel build
`FFFFFFFF`; a producer of a concrete historical build remains unresolved.

The [companion observation](../observations/main-ipc-protocol-handlers-2026-10-25.json)
records source hashes, addresses, branch behavior and export limits. Addresses
below are RVAs. The source is build 98348, 53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.

## Request state and response result

The [buffer-storage result](MAIN_IPC_BUFFER_STORAGE_2026-10-25.md) identified
returned-pointer global `0x37EBC48`. The instructions here load that pointer
before accessing state `+0x20` and result `+0x24`. These fields belong to the
returned buffer, separate from the factory record's constructor slot `+0x20`
and the product object's name field `+0x340`. Formal API names for the earlier
indirect mapping-shaped calls remain unproved.

Setup record `0x115AC30` uses the previously authenticated atomic helper at
`0x115AC64` to attempt state **0 to 1**. If the prior value is zero, it enters
adjacent setup record `0x115AC82`. That record writes request type 1 at
`+0x48` (`0x115ACA5`) and build `FFFFFFFF` at `+0x4C` (`0x115ACAC`), then
calls generic request routine `0x115ADE0` at `0x115ACED`.

The [independently pinned Switcher contract](SWITCHER_MISSING_BUILD_IPC_2026-10-25.md)
interprets `FFFFFFFF` as the highest installed client selector. This observed
caller supplies no concrete historical build number.

| Generic request location | Selected-ASM behavior |
| --- | --- |
| `0x115AE25` | Writes result `+0x24 = 0`. |
| `0x115AE28` | Writes state `+0x20 = 2`. |
| `0x115AE9F` | Calls unresolved helper `0x115A270`. The shared-response wait is entered when this helper returns 1. |
| `0x115AEB5`, `0x115AEE2` | Compares live state with 3. The loop can also exit when unresolved helper `0x115A240` returns false. |
| `0x115AEEE` | Reads result `+0x24` into EBX. |
| `0x115AF25` | Returns EBX through EAX after the result-specific branches below. |

The result branches are asymmetric:

- Result **1** clears `+0x24` at `0x115AEFD` and jumps over the state-clear
  instruction. This branch does not clear state at `0x115AF07`.
- Result **0** becomes return value **2** and clears state to zero.
- Result **3** remains return value **3** and clears state to zero at
  `0x115AF07`. Other nonzero results except 1 follow the same preservation
  and state-clear path.

If the unresolved helper at `0x115AE9F` returns a value other than 1, that
helper value is returned through EBX after clearing state; this branch does
not require reading the shared result. Because `0x115A240` can stop the wait,
reaching the result load does not establish that state 3 was observed.
No live response or process was observed in this analysis.

## Separate startup completion and sentinel handling

Record `0x115A630` is a different handshake. Its guards require a nonzero
buffer pointer, cached prior state `0x37EBC50 == 4`, and live state 1. It then
writes result 1 at `0x115A680`, state 5 at `0x115A687`, waits for the result to
clear or a helper to return false, and clears state at `0x115A6C2`. This
startup path is distinct from the generic request state-2/result-3 path.

Selected continuation `0x115A89D` reads build `+0x4C` at `0x115A95A` and
compares it with `FFFFFFFF` at `0x115A95D`. When it differs, it reads `+0x50`
and copies that value to global `0x37EBC60` at `0x115A970`. The additional
record `0x115AD10` contains a bit/counter cleanup-like sequence and a tail
jump to `0x115A100`; it is not a concrete-build producer in selected ASM.
No selected instruction supplies build 41810 or another non-sentinel build.

## Scope and unresolved work

| Selected RuntimeFunction interval | Bytes | Selected / expanded instructions | Outside blocks |
| --- | ---: | ---: | ---: |
| `0x115AC30..0x115AC82` | 82 | 20 / 55 | 5 |
| `0x115AC82..0x115ACF7` | 117 | 29 / 35 | 1 |
| `0x115A630..0x115A6E5` | 181 | 39 / 39 | 0 |
| `0x115ADE0..0x115AF34` | 340 | 82 / 80 | 0 |
| `0x115AD10..0x115ADD2` | 194 | 42 / 50 | 1 |
| `0x115A89D..0x115A9E2` | 325 | 69 / 81 | 3 |

The initial four records and justified two-record followup total 1,239 bytes
of selected code. Native export payloads total 60,190 bytes, below 64 KiB.
Both Ghidra jobs used the existing project with `readOnly`, `noanalysis` and
two CPUs; completion and discarded changes are recorded. No export was
size-truncated. Outside blocks and differing selected/expanded instruction
counts remain explicit; these records do not establish complete CFG coverage.
The asserted request, result and sentinel operations are in selected ASM.

The source inventory counted 46 raw seven-byte RIP MOV/LEA/store patterns in
14 RuntimeFunction groups. Complete group counts and bounds were retained;
46 per-reference details were not retained under the 32-candidate cap. The
four-record selection used the unique build-write site, its preceding setup
record, and both result-read records. The two-record followup used already
retained bounds. One PE identity hash stream and 2,450,948 bytes of headers
and `.pdata` supplied metadata; no extra PE read, data-section scan or import
scan was needed for the followup.

The next concrete retained seed is `0x115AB90..0x115AC2B`, 155 bytes with five
raw buffer-global references. It has not been exported, and its request-layout
or caller semantics are unproved. The producer of a concrete requested build
and higher-level handling of returned result 3 remain open. No downloader or
historical 41810 payload was recovered.

Within the static native-analysis lane, no game launch, Computer Use, IPC
send, network request, replay read/write or sync modification occurred. Full replay upgrade, playback and the first
simulation mismatch remain unproved. The public pair contains summarized
facts and source fingerprints, excluding raw PE/ASM and private paths.
