# Corrected source of the StartReplay parser descriptor

The reviewed StartReplay sender supplies a **local registry/type descriptor**
as parser argument R9. Earlier reports incorrectly grouped the wrapper's virtual
slot+18 with the incoming object's slots+20/+10 and called R9 external input.
This checkpoint corrects that source boundary. No historical value, new ability
mapping, converted replay or playback result follows.

All addresses and offsets are hexadecimal; type IDs are decimal. Code witnesses
use the SHA256-pinned analyst-derived98348 text, not unaltered PE instructions or
a runtime capture. The original PE supplies the selected table words/type ID.

## Receiver and descriptor

At1E5D064 the sender loads the table from local wrapper W=RBP-49. At1E5D068 it
passes W in RCX; the call at1E5D072 selects wrapper slot+18. The original PE word
at28F2FC0 points to1E5A8C0. Its complete straight-line five-byte body is:

```asm
lea rax, [rcx+18h]
ret
```

It returns W+18. That pointer is saved in RDI and passed as R9 at1E5D08F.
The shown wrapper stores registry address143B7F140 atW+18 and initially stores
type6060 atW+20. These are the descriptor's registry and current-type fields.

The kind16 loop at1E5D014..1E5D047 can overwrite W+20 at1E5D031. Therefore6060
is the initial configured type, not an unconditional live value at the parser
call. The pinned embedded metadata names6060 as STRUCT Response; actual registry
correspondence and helper/alias stability remain conditions.

## Incoming results remain distinct

| Native parser argument | Observed source |
| --- | --- |
| RCX | Parser interface atW+10 |
| RDX | Return of incomingR13 virtual+10, called at1E5D08C |
| R8 | Return of incomingR13 virtual+20, called at1E5D07F |
| R9 | Return of local wrapperW virtual+18, equalW+18 |

The incoming results' semantics are not inferred merely from register position.
Their concrete class, byte/storage ownership and actual values remain unresolved.
The full91-byte1A6E990 body reads registry from[R9] and type from[R9+8]. On the
branch requiring QWORD[registry+38] nonzero, it builds a frame containing those
values, entryRDX, entryR8, entryRCX and entryR9, then calls1A78CC0. The registry
gate is conditional; no actual loaded registry or successful decode was observed.

The separate transport investigation identifies stored G registration through
the manager atG+918 and a wrapper keyed0x417070(App). Allocation diagnostic tags
name TumorManagerImplementation/CreepTendril components. This does not prove an
incoming constructor, Gvirtual0 invocation, network source, archive-member source
or historical-player producer. Expansion stopped at that interface boundary.

## Verification and remaining work

The new leaf is5 bytes/2instructions. All1233 bytes/278instructions in the prior
sender/parser witnesses were rechecked;39 selected instruction assertions pass.
The sender's switch table and post-RET padding are excluded. Independent review
freshly decoded423bytes/109instructions across relevant prefix/leaves/parser and
verified the original table words, source hashes and receiver/data flow. It also
identified the type-unwrapping qualification, now preserved in this report.

See observations/native-wrapper-descriptor-source-2026-11-02.json and its
validation receipt. Historical observations remain as evidence of the earlier
analysis; their external-R9/all-three-slots-input interpretation is superseded.
The three affected narrative reports now link to this correction.

No production code, replay, synchronization data or historical default changed.
No new unit-test suite, provider import, native execution/emulation, game launch
or Computer Use was used for this static correction. The next source task is
the incomingR13 implementation of slots+10/+20 or an authenticated old-version
producer. Repeating the local slot+18 source search is unnecessary. Full upgrade
and current-client playback remain unproved.
