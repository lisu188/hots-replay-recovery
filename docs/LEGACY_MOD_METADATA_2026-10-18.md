> Later evidence: the earlier fixed447/unknown-hero interpretation below is
> superseded by [content-addressed static arcade arrays](AUTHENTICATED_ARCADE_SECTIONS_2026-10-18.md).
> This document preserves the initial diagnostic history. No bits should be
> removed or retagged based on that earlier interpretation.

# Historical battlelobby mod metadata: bounded offline diagnosis

The unchanged original and R8 still carry the same 1399-byte historical mod
section. A primary community schema explicitly assigns build41810 to its
historical layout. Reading that layout succeeds through five used mods, five
metadata records, all five CAFEBABE sentinels, every cache magic, and five terminal
s2mh handles. The earlier current-layout walk's16/18 counts were misaligned
reads, not the actual source counts.

The report and auditer provide serialization evidence. They do not convert this
section, write a member or replay, launch a client, or establish simulation
compatibility. The separate attribute-layer transcode remains a partial fix.

Primary sources are pinned to immutable commits:

- [Historical version assignments](https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/version%20list.md)
- [Historical schema2](https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/2.txt)
- [Later schema5](https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/5.txt)
- [Unchanged current C# reader](https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs)

These are community reverse-engineered descriptions. The author's version
groups are explicit sets, including overlapping build ranges; they are not
safe monotonic build thresholds. Neither profile is an official complete
Blizzard schema. The actual fixture boundaries, sentinels and exact
reconstruction below support this particular interpretation.

| Field | Historical schema2 | Pinned current reader | Actual source evidence |
|---|---|---|---|
| Unknown locale filler |131bits|128bits|The last3 old bits are000; their semantics remain unknown|
| UsedMods count |6bits|5bits|5 records|
| ModParams count |6bits|7bits|5 records|
| End of each mod record |8bits|32bits|All five source8-bit values0; all twelve32-bit values in two current controls0|
| Optional hero metadata |Fixed4+4+4+447+7 bits after initial11bits|Counted93-bit records,4bits,4-bit choice, counted23-bit records|Two old447-bit payloads are nonzero and lack an established current mapping|

Historical schema2 calls `a8*5` a **fixed four-bit field**. Its observed value3
is not established as a choice discriminator. The following unknown payload
has120+150+29+148=447bits. The later schema5 and current C# instead declare a
four-bit choice: values0..4 have no payload; value5 carries400bits. No source
establishes a semantics-preserving mapping between these representations.
Changing3 to5, deleting47bits, clearing this block, or copying donor metadata
would fabricate an unresolved transformation.

The two old payloads have85 and34 set bits. Their canonical packed SHA256
values are `208b36e7f276ef502d244e350339d8692dd4486a6108cee8777e4245b1db80cc`
and `c9a4ed6a83b70218b0b8fda71e0b6f6733e1b67f9c83a19361d42bc85648ed6c`.
Packing starts at bit0 using the same documented scalar-bit reader/writer and
zero pads the final unused bit. The exact447-bit length accompanies each hash.
The payload bytes and all names, toons, mod IDs and cache contents are omitted.

| Fixture | Section start bit | End after terminal handles | Section SHA256 |
|---|---:|---:|---|
| Original41810 |204704|215896|`d15681f2eb4aab1613d1dc7d450ab15fbcabedd3e5c83e025830721d7da501d9`|
| Published R8 |206080|217272|same|
| Prospective attribute layer, memory only |207584|218776|same|
| Stormblessed98348 control |480560|494552|`8d1c6095294ad9caeb0b53fe80f53eeb988415873b4b4b488edc7ab7fccef84a`|
| Protectors98348 control |480560|494552|same|

Original, R8 and the attribute-layer candidate also retain the identical14759-byte
post-section suffix, SHA256
`e93354e2f93df0664a6edebe53dc5087a099b2e886592d792d5516ae01bc1027`.
The fixture report records complete input replay and member digests. Its current
control labels rely on the separate current-reference provenance/build/core-stream
report; this tool does not repeat or substitute for that validation.

Every scalar and blob read is reconstructed privately, and the complete member
must remain byte-exact. The auditer validates cache magic, CAFEBABE, repeated
mod identities, ordering, and dependency **ID components**. Dependency offset
components are preserved exactly and hashed with the IDs. Their semantics are
not validated: source dependencies use offset0, whereas used-mod records carry
nonzero offsets. The tool therefore makes no claim that full dependency pairs
resolve semantically.

Reports contain only bounds, counts, selected unknown numeric fields, hashes
and explicit limitations. A successful audit does not decode the later cosmetic,
player or remaining battlelobby sections. The full member remains incompatible
with the unmodified independent reader, and R8 remains the latest replay.

From the repository root, after placing the auditer beside
`battlelobby_attribute_layer.py` and the verifier under `scripts/`:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest test_audit_battlelobby_mod_metadata -v
python scripts/verify_battlelobby_mod_metadata.py --original ORIGINAL.StormReplay --candidate R8.StormReplay --modern-reference CURRENT_CONTROL.StormReplay --output NEW_REPORT.json
```

The focused tests cover frozen historical/current goldens, fixed unknown hero
payloads, current choice5, wrong profiles, sentinel/identity/magic corruption,
truncation, unsupported choices, alignment padding, report privacy and refusal
to overwrite an existing report. The integration verifier checks immutable
original/R8 hashes, computes the existing prospective attribute layer only in
memory, and audits optional current controls. Its sole output is a new JSON file.


Local validation passed all 56 combined tests: 23 attribute-layer tests,
14 mod-metadata tests and 19 existing dependency-audit regressions. Root also
reproduced the five fixture cases: original, R8, R8 after an in-memory attribute
conversion, and two genuine current controls. The original/R8 files remain
unchanged. Independent review added ten real-member mutation/boundary probes
and two CLI input-bound probes, all with their expected outcomes. Unknown
dependency-offset and hero-payload semantics remain explicitly unvalidated.


## Published CI and source backup

CI run 39153672088 at 7e23a6a completed successfully on Linux and Windows.
Each job passed 37 focused tests, restored and checked the original/R8 files,
then passed three mod-audit cases including the in-memory attribute conversion.
The run wrote JSON evidence only and launched no game client. See
`observations/combined-battlelobby-ci-2026-10-18.json`.

A full-history Git bundle through 7e23a6a was verified with `git bundle verify`
and archived with the progress and diagnostic evidence. The 7,575,279-byte ZIP
was uploaded into a new dated subfolder of the existing OneDrive project.
Fresh cloud metadata agrees with local size and Microsoft's QuickXor hash.
The local ZIP SHA256 is retained. A remote content re-download returned HTTP403
serviceReadOnly, so independent remote SHA256 verification is not claimed.
Existing OneDrive artifacts were preserved. See
`observations/source-backup-2026-10-18.json`.
