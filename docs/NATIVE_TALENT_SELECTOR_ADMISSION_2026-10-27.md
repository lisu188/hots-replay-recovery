# Talent selector admission and pooled-object initialization

The selected talent write requires a first-selector low byte in0..15. The
provider9D5080 returns zero for16..255 before accessing its encoded globals,
switch or helpers; B10720 requires a nonnull provider result before its write.
The object field+44 used by the callback is initially16, so that default is
not a usable selector for this selected write path.

The callback's handle resolver and the examined allocator use the same encoded
pool slots, keys and752-byte object stride. This binds the selected object's
initialization and numeric admission boundary. Its native class name, the
meaning of field44 and the later assignment of effective selector values
remain unknown. No player/user identity, catalog mapping or gameplay result
is inferred from these bounds.

See the two dated `native-talent-selector-admission` observations. Addresses
and member offsets are hexadecimal unless described as decimal counts.

## Shared pool and selected initialization

Allocator990AF0 reads next-slot state34F02C0 and extent count34F02C4, and uses
encoded block-pointer slots at34F02C8. Its unsigned next-slot limit is1023
decimal. The slot's low four bits select an object within a block; its higher
bits select the encoded block pointer. A block allocation requests2F00 bytes,
which equals16 objects of2F0 bytes each.

The callback B612D0 uses those same slots and decode-key globals32C38B4 and
32C55D0. It obtains a slot index by shifting the handle22 bits, uses low4/high
remaining bits of that index to locate the object, and checks the full handle
against object+10 before reading object+44. This is numeric pool/identity
evidence; it is not an observed live lookup.

On its selected normal allocation path,990AF0 calls990020 on the returned
object. That initializer saves its input object, installs method table26A87F0,
and writes byte44=10 hexadecimal (16 decimal) at99006F. This is a selected
initializer assignment, not proof that the field retains that value after
later setup, loading, callbacks or alias writes.

Original table26A87F0 points to destructor candidate990730 in its first slot.
The preceding original QWORD is700000005, which is not an admitted image VA
for an MSVC Complete Object Locator. The attempted conventional RTTI route
therefore supplies no class-name binding. Adjacent debug strings and nearby
function pointers are not promoted to type names or table-extent evidence.

## Provider guard and expanded switch

At9D5084, `cmp cl,10` compares the incoming low byte with16. `jb` selects the
normal lookup only below16. Otherwise `xor eax,eax`, stack restoration and
RET return zero. A finite model of these checked instructions classifies all
256 low-byte values:16 reach the lookup;240 return zero before its globals or
helpers. This is an opcode/branch model, not native execution.

On the below16 path, the function computes an8-byte slot displacement. An
optional incoming pointer or encoded global reference selects the slot array.
Global mode3366118 chooses one of16 decode-helper arms through the RVA table
at9D522C. Results still depend on actual pointer storage, decode state and
helper behavior.

The selected code is9D5080..9D522A:426 bytes/106 instructions. The following
two alignment bytes and64-byte/16-entry RVA table are separate data. Together
they account for the complete original RuntimeFunction ending9D526C; the
embedded table is not disassembled as instructions. All16 table targets are
code boundaries, and the expanded normal-call/return graph reaches all106
instruction nodes. Direct non-call branches remain internal.

The global-mode-above15 path returns a stack local whose initialization or
validity is not established here. No safe fallback or guaranteed valid result
is asserted for that state. This does not weaken the earlier low-byte>=16
rejection, which happens before the mode read and table dispatch.

## Consequence for the selected talent writer

B10720 preserves the first low-byte selector and calls9D5080 atB10755. Its
`test rax,rax`/`je` atB1075A/B1075D sends null to failure. Removing the nonnull
edge makes the scalar write atB10934 unreachable in its selected graph.
Consequently that write requires a selector low byte0..15 under the stated
normal-call/ABI conditions.

The previous callback can obtain its selector from resolved object+44, or
from event+2A on the fallback branch. Both the selected object initializer and
event110 constructor initially write16 to these respective fields. A path
that still supplies16 cannot reach this write; the effective value must come
from later state or a different path. Those later assignments and their
player/user meaning have not been recovered. Do not substitute userid or
userid+1 or rewrite event110 indices from this result.

## Verification scope

Four complete original RuntimeFunction/CHAININFO unions (allocator, object
initializer, existing callback and existing writer) total2183 bytes/504
instructions. The provider adds426 code bytes/106 instructions and its
separate64-byte table.31 specific instruction/call/reference checks include
the shared pool/key addresses, object stride, initializer store and required
nonnull edge. Every selected byte is checked against the pinned transformed
text; original exception records supply the fragment extents.

Instructions and embedded switch data come from the analyst-transformed98348
image, not unchanged original ciphertext or a new runtime capture. The prior
original-PE prefix-reproduction result remains a separate data-model proof.
Normal returning helpers/x64 ABI, valid disjoint storage, stable identities
and no exceptions, reentry, concurrent writes or alias mutation are required.
The effective provider globals, slots, mode and resulting objects remain
unobserved.

Exploratory raw references and other nearby functions are retained privately.
In particular9D4E90 was initially searched under a setter hypothesis; its
decoded body is another accessor-shaped routine, so those candidates are not
published as writes or used to name field44. The unqualified scans are not
coverage claims about all callers or all ways the field can be assigned.

Source/R8/current replay and unused-launcher hashes remain exact. Ordinary
Python/GNU objdump under WSL only: no native target or new REA provider
analysis, production/conversion/replay/sync change, fresh event decode, new
unit tests, broad corpus, hosted CI or independent peer review. All work stays
offline. Full upgrade/playback remain false. Next find the effective selector
assignment and its object/namespace binding, then the target-context catalog
and historical41810 rule data required for a safe migration.
