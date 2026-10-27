# Event-user lookup and original-PE observer page provenance

The selected sequential reader stores the serialized frame user byte at
event+29. The talent callback reads that byte and performs a row/tag/handle
lookup before obtaining the first selector used by the talent state writer.
The callback does not simply substitute the serialized user value as that
selector. This is a conditional static field/lookup binding; the actual
resolved selector and its player/user namespace remain unauthenticated.

The selected transformed dispatcher tables and callback page were also freshly
reproduced from the pinned original PE. Original ciphertext and transformed
plaintext differ as previously recorded. Their relationship is now checked
for these pages under the existing analyst page-transform model. Native
bootstrap parameter choice, execution and replay playback are unproved.

See the two dated `native-observer-user-route` observations. Addresses and
member offsets below are hexadecimal unless explicitly stated otherwise.

## Serialized user byte to callback input

The earlier frame binding identifies native root890 with the physical wire
graph corresponding to upstream `m_userId`: one five-bit value with declared
range0..16. Original type slot27C9F28 remains890.

In sequential reader13266B0, call1326789 supplies stack+50 as the root890
output. Following successful root and ID/payload reads and a nonnull event
pointer,13267B4 loads that byte and13267B9 stores it to event+29. The selected
event110 constructor1351460 initially puts16 in both byte29 and byte2A;
the sequential reader subsequently overwrites29 with the serialized value.
Byte2A is a different field whose eventual effective value is unknown here.

CallbackB612D0 loads event+29 into ECX atB612DA and callsA28B60. Its incoming
event pointer is retained in RDI. The binding assumes the same event reaches
the callback with byte29 preserved; the intervening opaque dispatcher has
not been proved to preserve it.

## Numeric lookup route

A28B60 is a56-byte straight-line leaf ending atA28B98. Its only RET is at
A28B97; subsequent padding/junk is excluded. It reconstructs an encoded
64-bit global base and returns:

```text
row = encoded_global_base + (uint8(input) + 0xB0) * 0x1A4
```

No effective base address or row contents were captured. The row stride is
420 decimal bytes; this alone does not identify its native type.

The callback zero-initializes a DWORD output and, for a nonempty row, calls
202ED90 with capacity1 and a tag from row+2. That94-byte function scans the
row's byte count, compares item tag bytes at row+84+i, and copies matching
DWORD items from row+4+i*4. It stops after the first match for this call's
capacity. The callback then validates the returned handle and object identity.

On its successful resolution branch, the first selector is a byte at resolved
object+44, while event+2A supplies the bitmask's other selector. On the fallback
branch, both are derived from event+2A. The callback's bitmask still gates the
call toB10720 with the payload index at event+30.

The resolved object type, byte44 meaning, row initializer, tag meanings and
effective bitmask are unbound. Neither `userid == firstSelector` nor
`firstSelector == userid+1` is established. This does not override the earlier
recorded-purchase auditor's explicit setup-based user/player associations.

## Fresh original-PE data reproduction

The existing pinned Python page-transform implementation was run from RVA
BA000 through B62000, starting from the same explicit previous-hash hypothesis0.
It processed2728 pages /11173888 bytes in RAM. Every page matched the saved
transformed text, and the complete prefix hash is recorded.

Three selected4096-byte pages were also checked using a second local
generator-form permutation/stream implementation and a separate FNV routine:

| Page RVA | Relevant selected data/code |
| --- | --- |
| B58000 | Original observer-method entry in transformed form |
| B5F000 | Header switch suffix, call arm,116-byte RVA table and99-byte selector table |
| B61000 | Complete B612D0 talent callback |

The selected ranges are entirely inside those freshly reproduced pages. The
whole original PE and saved transformed-text lengths/hashes are checked.
Key material comes from the original PE's42320-byte region at2B7A347, with
115 blocks of368 bytes. The recurrence and previous-page hash remain explicit
analyst-model parameters. The second implementation comparison concerns the
three selected pages, not an independently reimplemented2728-page chain.

This authenticates the selected transformed bytes as deterministic outputs
of that model on the pinned original PE. It does not prove the native loader
uses the same initial state, reaches/completes this chain, or executes the
selected dispatcher suffix. The previously observed98/116 differing bytes in
the two switch tables remain differences between ciphertext and plaintext.
No original file, replay or runtime memory was patched or captured.

## Validation and remaining boundary

Five selected ranges total845 bytes/231 instructions. These comprise the
previous complete sequential-reader and callback fragment unions, the complete
202ED90 RuntimeFunction, and two straight-line leaves. Every selected byte and
boundary was rechecked;34 direct non-call branch targets stay within their
selected ranges, and32 specific instruction/call checks support this binding.
Helpers must return normally and follow Windows x64 ABI. Valid disjoint
storage, native metadata/output layouts, stable handles/objects and no alias
mutation are required. Native execution is outside this proof.

REA readiness reports no open target or pending cleanup. Its IDA adapter is
configured but was not live-probed or used for analysis; the installed Ghidra
version remains unsupported by that REA adapter. Existing unrelated sessions
were left alone. This stage used Python and bounded GNU objdump under WSL,
with no new native-engine database or target execution.

Original/R8/current replay and unused-launcher hashes are unchanged. There was
no fresh event-stream decode, production/conversion change, new unit test,
broad corpus, hosted CI or independent peer review. All work stays offline.
Full replay upgrade/playback remain false. Next authenticate dispatcher
preservation and the actual row/object/selector and effective catalog data;
historical41810 rule equivalence remains unresolved.
