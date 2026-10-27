# Named native talent fields and the selected query layout

The selected native registration now binds `CHero.TalentTreeArray` to
`SHeroTalentTree` entries of64 bytes. Its registered offset470 is relative to
the CHero data body. CHero's selected initialization/copy callbacks use a body
at object+90, giving the count/base offsets500/510 used by the earlier index
query. The named entry's `Tier` field is at+8, and its copy callback reaches
the same50B800 helper used by that query.

This closes the selected static name/layout gap under normal metadata and
CHero-record conditions. No live resolved object or effective catalog snapshot
was captured. It does not establish loaded entries, XML ordering, historical
rules, purchase acceptance or a safe index migration.

See `observations/native-talent-field-bridge-2026-10-27.json` and its validation
receipt. Addresses are RVAs; structure offsets are stated separately.

## Owner and element bindings

The earlier descriptor2BC5320 is a pointer/length descriptor for
`SHeroModification`. It is not a literal string and is not the owner pointer
used for the later TalentTreeArray registration. Function50CA80 initializes
many different types and reuses both registers and stack slots.

At50F02A, RDX receives the original descriptor2BC5360, whose first pointer and
length5 identify the exact `CHero` literal at2BC5498. Call50F046 supplies it to
16037E0, and50F04B stores the returned metadata pointer in stack slot RBP+978.
The pointer is restored to RBX at510579 and supplied as RCX at51113E for the
TalentTreeArray registration call51115E.

The field's original literal is at2BC5958. The call supplies R9D=470 and a fifth
argument18. Registrar1601160 preserves R9 in RBX and forwards it as the fifth
constructor argument to16003F0. The constructor's stack adjustment binds that
argument to its RSP+80 load, which it stores at field-descriptor+80. The470 value
is preserved; no arbitrary offset adjustment is inserted in the registrar.

At50F0F4, the paired name/initializer arguments are the literal
`SHeroTalentTree` and509AF0. The returned type metadata is stored at RBP-50,
then restored to R8 at511125 for the same field call. The selected initializer
stores40 as the type size, agreeing with the original named struct descriptor's
size64. These are selected normal metadata bindings, not a live table read.

## Entry fields and copy path

Original descriptor2BC5220 identifies `SHeroTalentTree` through the exact
15-byte literal at2BC5410. Call50D57C registers that descriptor through16038E0;
its result is kept in R12 for the following field registrations:

| Field | Original name literal | Registration call | Registered byte offset |
| --- | --- | --- | ---: |
| Talent | 2B9E2D4 | 50D698 | 0 |
| Tier | 2BC3A00 | 50D6D2 | 8 |
| Column | 2BC54FC | 50D708 | 12 |

The descriptor's selected copy callback505910 calls50B800 for valid distinct
source/destination pointers. That is the same copy helper as the previous
runtime index query B0F160. Its explicit entry+8 to output+8 copy therefore
carries the named Tier field in this SHeroTalentTree context.

Consequently the previous sender's use of output+8 as B0F720's second selector
has a selected native Tier binding. The first selector's player/user namespace
remains unauthenticated. A single state-table cell per selector pair is not a
proof of a universal one-purchase-per-tier acceptance rule.

## CHero body and query offsets

The CHero descriptor pairs initializer505CF0 and copy callback505DB0. The
initializer passes object+90 to the complete straight-line leaf614460. Its
explicit instructions zero the array count at body+470 and pointer at body+480.
The copy callback separately adds90 to source and destination before calling
the body-copy helper50A710.

| Quantity | Body-relative offset | Object-relative offset |
| --- | ---: | ---: |
| TalentTreeArray count | 470 | 90 + 470 = 500 |
| TalentTreeArray base pointer | 480 | 90 + 480 = 510 |

These match B0F160's count/base offsets and its64-byte entry stride. This is
a conditional static type/layout bridge: it applies when the resolved record
is a normally initialized CHero object. No actual resolver result, record type,
count, base pointer or talent entry was captured. The bridge supplies no
current effective catalog values for either replay's map/mod context.

## Control flow and verification limits

The complete50CA80 registration body has4897 decoded instruction nodes. Its
direct control-flow graph has no indirect jumps or external direct non-call
exits. Six definition/use checks confirm that the selected CHero owner, field
type and SHeroTalentTree owner definitions dominate their corresponding uses.
There are no intervening explicit RBX/R12 writes that break the selected
register bindings. Calls must return normally and preserve Windows x64 ABI;
exception/reentry, later callback replacement and unknown alias mutation are
outside this proof.

Twelve selected ranges total31469 bytes/5601 instructions, including the full
registration, complete class lookup/resolver fragment unions, original callback
bindings, field registrar/constructor and two straight-line initialization
leaves. Every selected byte, instruction boundary, direct non-call branch and
original descriptor/name/callback pair is checked against pinned inputs. This
is ordinary local GNU objdump analysis under WSL, not native execution or
REA/IDA/Ghidra Evidence.

Source/R8/current whole-file and launcher-draft pins are rechecked. No stream
decode, production change, new unit tests, broad corpus, hosted CI or independent
peer review is claimed. All replay, synchronization and conversion values remain
unchanged. Keep all work offline; full replay upgrade/playback remain false.

The next useful boundary is the code that writes the selected per-tier state
and consumes event110. Native reference candidates are retained privately but
are not promoted to write, purchase or acceptance evidence. Neither a15->7
rewrite nor a substitute for a missing historical talent is authorized by this
layout proof.
