# Ability class names and the selected EffectTarget query

Two numeric ability descriptors now have direct static name bridges through
their selected construction callbacks. Descriptor6 constructs an object whose
installed method table has a leaf returning `CAbilAugment`; descriptor9 has the
corresponding bridge to `CAbilEffectTarget`. Both names agree with the registered
`EClassIdCAbil` enum. This is stronger than matching a19-value numeric range.
It identifies selected current implementations, not the names/types of source
replay ability links126/351 or live catalog records.

The distinction changes the next data dependency. The previously examined
record+190 target-class query belongs to the selected Augment implementation.
The selected EffectTarget implementation follows a different reference at+140
and another runtime callback table. Neither dependency supplies a historical
flag mapping. All conversion rules and replay bytes remain unchanged.

See `observations/native-ability-class-names-2026-10-27.json` and its validation
receipt for exact code/data pins and conditions. Addresses are RVAs unless
described as object offsets.

## Registered class enum

The whole registration function5FA730..5FBCAC supplies the exact
`EClassIdCAbil` name at5FA759 and table2BDA000 at5FA773. It places count20 in
caller stack+30 and calls1600E80 at5FA79A. The previously qualified forwarding
through1600E80 and16001D0 binds20 source records of24 bytes each: low DWORD
value, name pointer and name length. All480 original PE table bytes and every
literal name are checked separately from transformed instruction bytes.

| Enum value | Registered name |
| ---: | --- |
| FFFFFFFF | CAbilUnknown |
| 0 | CAbil |
| 1 | CAbilEffect |
| 2 | CAbilQueueable |
| 3 | CAbilRedirect |
| 4 | CAbilArmMagazine |
| 5 | CAbilAttack |
| 6 | CAbilAugment |
| 7 | CAbilBehavior |
| 8 | CAbilEffectInstant |
| 9 | CAbilEffectTarget |
| 10 | CAbilMorph |
| 11 | CAbilMorphPlacement |
| 12 | CAbilMove |
| 13 | CAbilQueue |
| 14 | CAbilRedirectInstant |
| 15 | CAbilRedirectTarget |
| 16 | CAbilRevive |
| 17 | CAbilStop |
| 18 | CAbilTransport |

These are ability **type** values. They are distinct from the replay's numeric
ability link and from the validator's target class0..3. Constructor/name bridges
are directly checked here for6/9 only; other rows are authenticated enum
definitions, not additional live-object or source-link assignments.

## Constructor and name bridges

The existing initializer profileA51FE0 links each selected command descriptor
with a neighboring construction callback. Registry base3602D60 has stride2A48,
construction pointer offset1528 and command-descriptor offset1530. GetterA51A70
therefore returns a descriptor eight bytes after the same type's construction
pointer. The caller's RBP=RSP+100 relation binds its local header store to source
offset1520 used by installerA51F10.

For type6, the initializer stores A51400 at3614038 and copies the command
descriptor to3614040. A51400's selected construction code installs table26AEF18
at object+0. Its original PE method slot+68 (26AEF80) points to A511D0, whose
complete eight-byte leaf returns the literal `CAbilAugment` at26AF0D8.

For type9, the initializer stores A51540 in the local header, passes type9 to
A51F10 atA5254C, and pairs construction pointer361BF10 with descriptor361BF18.
A51540 installs final table26AF6A0 at object+0. Its original slot+68 (26AF708)
points to A51200; the complete eight-byte leaf returns `CAbilEffectTarget` at
26AF890. The two literal strings exactly equal the enum names at values6/9.

These are conditional initialization/construction assignments. Normal helper,
copy and constructor behavior, valid disjoint storage and absence of later
alias/table changes are required. No construction callback or name method was
executed, and no live descriptor or catalog instance was observed.

## The EffectTarget target-class dependency

The type9 builderBA9A40 assigns BA6130 to command0's target-class slot+80.
On its selected resolved-record path, BA6130 calls A8B390 with:

- RCX pointing to the resolved ability record+140;
- EDX loaded from normalized command byte+0A.

The byte at+0A is separate from command index+08. Its semantic name is not
assigned here. It must not be relabeled as the command index merely because
both are bytes in the same normalized command.

A8B390 follows another lookup at201F770, obtains a selector through201F540,
and supplies it to B2AD50. That leaf returns the pointer at
`36DE920 + zeroextend(selector_u32)*72`, offset0, with no bounds check in the
selected leaf. A nonnull pointer is called atA8B3F6. The query returns that
callback's result orFFFFFFFF on its checked failure paths. The reference field's
symbolic name, selector namespace and live callback-table values are unbound;
this receipt does not infer them from the ability's class name.

The selected BA61C2..BA61DE block then maps query result0/1/2 to target class
1/2/3, respectively; other32-bit values map to0. Thus EffectTarget is not assigned
a constant class by this analysis. Its nested data/callback dependency remains
material to the None-versus-Unit flag investigation.

This route is separate from type6/Augment's C02780 callback reading record+190.
Do not use that Augment field as a generic EffectTarget target-kind field.

## Source boundary and validation

The cached publisher41810 catalog and heroes-followup assessments are pinned
and reused. They identify a publisher-labeled historical projection, but still
do not authenticate the original installed/CASC root or numeric replay ability
links. This is not a fresh raw-hero/full-historical-corpus audit. No ability name
or current type is assigned to source126/351 from hero selection, string IDs,
JSON array ordinals or the new type enum.

Original PE authority:53,573,840 bytes, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
Instruction authority is the separate analyst-transformed text patch,
36,581,376 bytes, SHA-256
`3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83`.
It is not unchanged signed PE text or a runtime capture. Python and local GNU
objdump were used without a new REA/IDA or native execution claim.

Twenty selected nonoverlapping ranges, including reused code, total10,917
bytes/2,036 instructions and match the pinned transformed text exactly. Direct
noncall branches land on internal decoded instructions except two explicit
builder tails to separately qualified settersA27810/A27780. The reused C02780
callback's three RuntimeFunction fragments retain their original CHAININFO.
Raw xrefs and exploratory partial consumer records are excluded from counts.

A restricted byte-opcode interpreter checks260 result values through the actual
BA61C2..BA61DE mapper, including unsigned boundary values. All agree with its
formula. This is finite static interpretation, not full callback execution or
an exhaustive32-bit run. No production code or new unit tests changed; unit
tests, broad corpus, hosted CI and independent peer review were not rerun.

Original/R8/current-control lengths and SHA-256 values remain unchanged. The
unused launcher drafts remain untracked. No replay/sync value was written and
no game, Computer Use, network or remote publication occurred. **Keep all work
offline** remains active. Full upgrade and playback remain unproved; next bind
authentic ability-link/type data and the appropriate nested query state.
