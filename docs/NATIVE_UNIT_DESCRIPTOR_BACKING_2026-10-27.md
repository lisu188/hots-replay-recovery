# Unit descriptor construction and nullable backing lookup

A nonzero descriptor returned for the selected `GameData/UnitData.xml` call
is insufficient evidence that Unit data is loaded or that the replay's unit
links pass their catalog gates. The selected producer admits a cache-miss
route that constructs a descriptor with a null underlying lookup result.
This is a conditional static route, not captured Unit state, a missing-file
diagnosis, or an explanation of the earlier desync/client exit.

## Binding to the prior Unit manager

The prior catalog checkpoint binds index 83 to original metadata `Unit` and
`GameData/UnitData.xml`. Its call at `31EB61 -> 1609450` receives that XML
descriptor row, with R8D=0 and receiver:

```text
E = QWORD[context+2E8] + 28
```

The returned descriptor is stored at context `+588` and copied into the Unit
manager at `+30`, under the prior stable-slot/helper conditions. The manager
is at context `+2A0`; logical counts and entry gates remain separate from
this descriptor pointer. The original metadata relationship is inherited
from the pinned committed report and rechecked; no replay decode is repeated.

At `31E942..31E946`, the context constructor initializes the embedded lookup
object at a newly allocated root object's `+28` using `16083B0`. The root
object is stored at context `+2E8` by `31E9DB`. The initializer writes the
original address `142F2F988` to `[E]` and initializes `DWORD[E+10]` to zero.
It returns E. This establishes an initial lookup/cache layout, not the live
contents of the mutable global object at that address.

## Producer, cache hit and miss

Complete original chained function `1609450..1609804` saves the selected
optional input in RDI, its receiver in R12, and descriptor row in R15.
It calls external helper `1EFA550` with the temporary buffer, `QWORD[E]`,
optional input and original descriptor. That helper's body is not audited
here, so neither its boolean nor its buffer effects are labeled a confirmed
file-open or parse result.

For the selected optional input zero, either boolean result proceeds to
the cache lookup. AL=true jumps directly to `1609534`; AL=false tests the
zero optional input and falls through to the same address. The producer
builds a key from the original descriptor and calls `16092D0` at `16095AA`,
using receiver E+8. A nonzero result takes the cache-hit route, is returned
after cleanup, and bypasses both the underlying lookup and construction.
This selected hit path does not refresh descriptor `+28`.

The complete cache lookup is `16092D0..1609448`, 376 bytes. It reads the
capacity at its receiver `+8`, corresponding to E+10. Capacity zero branches
to XOR EAX/EAX and returns null without a comparison-helper call. The
initializer therefore supplies one legal empty-cache state. This does not
establish the cache state at Unit index 83, after earlier catalog iterations,
or during replay application. A missing matching entry is an explicit
selected-route condition, not an observed Unit cache miss.

## Underlying lookup permits null

On a cache miss, `160962B` calls the exact 15-byte tail window
`1EF9F80..1EF9F8F`. It adjusts RDX by 120, sets R8D=0 and jumps to `2A7B10`.
No original RuntimeFunction covers this thunk, so only this exact external
tail window is qualified; no larger function extent is invented.

Complete original chained function `2A7B10..2A7D37` keeps its receiver in
R13 and initializes result register R14 to zero. It prepares a temporary
key using external helpers, then reads the receiver's DWORD entry count
at `+8`. Count zero skips the entry loop and returns R14, hence null, under
ordinary helper and stable-receiver conditions. A matched entry can assign
R14 from the pointer array at receiver `+18`. Comparator/normalization
semantics and actual receiver contents are not inferred beyond these
selected relationships. In particular, the address stored by the embedded
initializer does not prove the live global has zero entries.

The count-zero route establishes that a null underlying lookup result is
admitted by the called code. It does not show this result occurred for Unit,
whether a particular file exists, or which input content has been merged.

## Fifth argument and descriptor field

For a null underlying lookup result and selected optional input zero, the
producer requests a 190-byte descriptor allocation. Allocation failure
returns null. On allocation success it selects the temporary descriptor,
sets R14 to the still-zero RBX and passes:

| Argument | Selected value |
| --- | --- |
| RCX | nonzero descriptor allocation |
| RDX | temporary descriptor at caller RBP+B0 |
| R8 | the same temporary descriptor |
| R9 | optional input zero |
| fifth argument, caller RSP+20 | R14, zero |

At constructor `16081E0`, the call's return address and three pushed
registers give the same fifth-argument address as callee RBP+40:

```text
caller_rsp + 20 = callee_entry_rsp + 28 = callee_rbp + 40
```

The constructor saves the allocated pointer in RBX. At `16082A4..16082A8`
it loads the fifth argument and stores it unchanged at descriptor `+28`.
At `16082AC` it stores the selected optional input at descriptor `+20`.
There is no local fifth-argument null rejection. At `160837F`, the normal
return value is the original allocation. The producer retains this result
in RDI while linking its cache/list nodes and returns RDI after cleanup.

Thus a nonzero descriptor with a direct `+28=0` store is a legal selected
static route, provided allocation succeeds and the stated helper/memory
contracts hold. The ordinary bounded helper assumptions are explicit:
valid temporary objects and private stack, distinct writable allocation,
Windows x64 register preservation, no alias/reentry/concurrent mutation,
normal string/registration helper returns, and no later helper changing
the retained `+28` field. This is not full CPU emulation, actual target
execution or a proof of every helper's memory footprint.

Ten small relation-model cases cover both external-helper booleans and
five outcomes: cache hit, miss/null/allocation fail or success, and
miss/found/allocation fail or success. The two null/success cases retain a
nonzero descriptor and modeled `+28=0`. These are conditional code models,
not runtime observations, fabricated replay fixtures or playback tests.

## Consequence for recovery and validation limits

The catalog XML name and nonzero descriptor pointer cannot close the
effective catalog gap. Conversely, this checkpoint does not introduce a
new universal requirement that `+28` must be nonzero for every effective
Unit entry. Other inheritance, merge and manager-population paths remain
unclosed; a null field alone does not prove all effective entries absent.

The next useful artifact is the actual same-context descriptor/cache/backend
state together with populated Unit manager counts and entry/reference data,
or an authenticated historical catalog/input set. No guessed link, talent
remapping, default entry or acceptance flag is added. The earlier singleton
selection/owner model still depends on catalog gate acceptance. Historical
41810 rules and native playback are separate unresolved requirements.

Six ranges totaling 4247 bytes / 1039 instructions are byte-qualified:
five complete original RuntimeFunction/CHAININFO unions and one complete
branch-closed no-call initializer leaf. Of these, 2473 bytes / 629 instructions
are new to this checkpoint. The tail window adds 15 bytes / 3 instructions.
All 86 selected instruction/call/reference checks, five register-flow
checks, six constrained path checks, fifth-argument address identity and
ten relation-model cases pass. These are bounded static checks; the
decoder's extra seed bytes beyond each qualified extent are excluded.

Original PE and transformed-text authorities remain distinct and hash-pinned.
Original/R8/current replay and unused launcher-draft bytes are rechecked.
The first qualifier attempt stopped on a Python metadata type mismatch;
the metadata handling was corrected and the final check passes. No native
target fault was involved. No fresh game/tracker decode, conversion/replay/
sync write, unit tests, full corpus, CI or independent peer review occurred.
Subagent review remains unavailable due to the reported usage limit.

Native evidence uses local Python and GNU objdump under WSL. REA native
provider analysis, target execution and emulation are false. No new REA
session/import, game, Battle.net, Computer Use, external-network request,
remote refresh or publication occurred. All work remains offline and full
upgrade/playback remains false. Addresses, offsets and allocation sizes are
hexadecimal; counts and catalog index 83 are decimal.
