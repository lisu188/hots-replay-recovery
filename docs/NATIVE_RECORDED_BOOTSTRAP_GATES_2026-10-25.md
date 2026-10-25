# Recorded bootstrap gates and player-field sources — 2026-10-25

The recorded-mode bootstrap does attempt the native battlelobby decoder, but
a failed battlelobby parse is not made fatal at the reviewed caller, next
stream gate or cleanup return handling. Required `replay.initData` has a
different error path. A strict managed parser's failure in the old battlelobby
member therefore does not establish the native playback blocker by itself.
Whole playback and deterministic compatibility remain unverified.

The new receipt is
[`native-recorded-bootstrap-gates-2026-10-25.json`](../observations/native-recorded-bootstrap-gates-2026-10-25.json).
All addresses below are RVAs in the pinned 98348 client. This work used static
Ghidra analysis under WSL, without Computer Use, game/client launch or native
target execution. No replay/member was read or written, and no synchronization
data, decoder failure handling or launch flags were changed.

## Recorded metadata path

The retained `CFE3B0` recorded-mode2 branch establishes:

| Step | Native code | Result handling |
| --- | --- | --- |
| Required setup | `CFEC51 → 134DD30`, native775 | Failure writes bootstrap result `{2,2,9}`; success copies setup to owner `+19460`. |
| Conditional metadata | `CFED0B → 134D950 → 134C690` | Owner `+191C8` bit17 must be clear; the inner reader decodes only when its stream flagbit3 is clear. |
| Metadata success | `CFED14..CFED59` | Copies discriminator/root to owner `+8088/+8090`, then sets owner flagbit16. |
| Metadata failure | `CFED12 → CFED63` | Joins cleanup and continuation at `CFEDB3`, without the required-setup error assignment. |

The fresh, complete 34-instruction `134D950` body authenticates the previously
missing direct call to `134C690`. It copies the cached discriminator/root from
reader `+2B2B0/+2B2B8` after success. Failure stores its error at temporary
reader `+33310` and returns it. The underlying reader supports online5917 and
local5962 battlelobby roots; those remain separate from native775 setup.

The next reviewed stream gate, `134E890`, does not load cached `+33310`.
Its reading path returns fresh required-stream errors, or zero on its success
path. Thus it does not merely forward the earlier battlelobby parse error.

The same temporary reader is then passed to cleanup `134BF90` at `CFF037`.
This cleanup calls retained `134CE10`, which **does** read and return cached
status. `134BF90` discards that returned EAX before its next call. It destroys
the stored battlelobby/initData containers and releases stream/archive state.
The exact selected cleanup listing has 126 instructions. Its decompiler
expansion is truncated (154 instructions, 11 outside blocks); the narrow
conclusion uses the complete selected listing plus retained `134CE10`.

These are conditional local paths. Runtime modes/flags, later metadata
consumers, receiver lifetime, and the global effects of every destructor or
callback have not been proved. This is neither an instruction to suppress
errors nor evidence that all playback paths can ignore battlelobby. The old
resource and ClientInfo semantics remain gaps in a complete current-format
conversion, while their necessity for ordinary native playback must be
established separately.

## Combined levels are a separate current source

The current native schema names two distinct fields:

```text
ClientInfo1768.field14 m_sharedPlayerInfo
  USER1804 → CHOICE1834
    tag0 infoS2 → InfoS2 STRUCT1851
      m_combinedRaceLevels → OPTIONAL1858 → USER1872 → u32
    tag1 infoHero → InfoHero STRUCT1852

ClientInfo1768.field16 m_playerLevel → USER1806 → u32
```

In the retained `DFE7D0` consumer, `DFF923` places RSI at
`ClientInfo+2D0`. At `DFFB7A..DFFB91`, tagzero is required; the consumer copies
InfoS2 presence/value at ClientInfo `+2C0/+2C4` into user `+164/+168`.
The destination is native775's optional u32 path
`775→776→107→108→82[field4]→87→106→3`, previously matched with pinned Blizzard
`m_combinedRaceLevels`.

This is an authenticated source for combined levels in this current consumer.
It is separate from mandatory player/account level at ClientInfo `+358`.
The optional combined-level field must not be relabeled as a proven account
level source for TEN_GREYMANE.

The other retained slot branch reads InfoHero lobby/team voice flags at
`+2C1/+2C2` and ORs them into one destination bit. A true result cannot recover
the two original inputs: `(false,true)`, `(true,false)` and `(true,true)` all
produce it. No missing historical voice state or default is derived here.

## Remaining producer candidates and verification

Two retained raw store candidates were exported. Both contain real
instructions at the candidate addresses, but neither establishes a ClientInfo
producer. `1BDF2C0` writes stack locals using an RSP-derived RBP. `2C236F`
constructs a temporary descriptor containing a qword, constant25 and byte0,
passed from `RBP+350` to `2871E0`. The callee's field semantics are not
authenticated. Its relevant instructions are in the full selected listing; its
expanded listing is capped. Reusing their `358/35C` displacements as account
field evidence would be incorrect.

Four fresh bounded exports across three read-only Ghidra jobs completed.
The receipt records each listing's quality and pins 15 source inputs. The
metadata-reader listing is complete; the large candidate and cleanup
expansions retain explicit truncation limits. Required instruction, schema
graph and source-hash checks passed locally. Independent reviewers checked
the bootstrap/status flow and the typed player-field binding.

No production codec changed and no new historical field assignment or replay
checkpoint was created. R8 remains `98285-resumable-r8`; both full-upgrade
flags remain false. Continue to distinguish current-format metadata gaps
from proven native playback gates, and seek authenticated historical rules
or an actual first synchronization divergence before changing the replay.
