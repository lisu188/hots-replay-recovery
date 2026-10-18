# Complete read-only battlelobby suffix coverage

`battlelobby_tail.py` decodes the section after terminal mod s2mh handles through
the actual end of the member. Its explicit `historical-tail` and `current-tail`
profiles preserve every observed scalar, blob, optional flag and unknown bit in
memory and re-encode the complete original member exactly. The encoder refuses
cross-profile conversion and changed output. The CLI writes a new JSON report
only; no member or replay output is available.

The layout sources are the pinned community
[historical schema2](https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/2.txt)
and the pinned
[current reader](https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs).
These provide serialization descriptions; unknown field meanings and runtime
compatibility are not established by a successful parse.

The actual verification covers the immutable41810 original, published R8 and all
twelve admitted98348 Dragon Shire controls. Every case reaches EOF, accepts at
most seven zero padding bits, and reconstructs the entire member byte for byte.
Every input replay is hash-bound and checked again after the audit. The current
cohort admission manifest and canonical Blizzard protocol source hashes are
retained in the fixture report. This tool does not repeat the separate full
game/message/tracker reference-validation work.

Observed source differences remain explicit:

- The source/R8 collection contains263 variable UTF-8 names,3–29bytes each.
  Current controls contain5418 fixed eight-byte identifiers. No name-to-ID or
  ownership conversion is provided. All per-slot ownership bytes stay private.
- The unknown player block is174bits historically and198bits currently. All
  observed player blocks are nonzero. Adding24 zero bits has no established
  semantic basis and is not implemented.
- The community field named `m_build` contains64541 in the source/R8, although
  the original replay header is41810. The report labels it only as the observed
  community-named32-bit field and never treats it as verified client-build
  evidence. Current observed values are98348.
- Disabled-hero, flag, account, boost, per-icon, later table-width and all-hero
  differences are read according to the selected profile. No defaults are added
  and no source field is removed.

Player identities are checked privately against the independently decoded
`replay.details` and `replay.initData` streams. Numeric Toon region, program,
realm and ID and working-set slots are compared without emitting them. The
tail's32-bit FourCC program is normalized to four big-endian ASCII bytes for
comparison with the decoded details FourCC bytes. InitData's textual Toon
handle is parsed and compared privately.

All ten details participants match their tail identities and slots in each of
the14 cases. Some current recordings have one or two additional occupied tail
and initData slots. Those additional identities also match initData exactly;
the tool does not assign their role or repair any slot. Both random-seed
crosschecks match in all cases. Current disabled-hero lists also agree with
initData. A full tail/details identity-multiset difference remains visible when
the tail has these extra occupied slots and is not mislabeled as corruption.

Reports expose hashes, boundaries, counts, aggregated nonzero-bit counts and
explicit limitations. They contain no player names, Toon IDs, working-set slot
values, party IDs, tags, account levels, collection identifiers or ownership
matrix. Models suppress their automatic representation, and report generation
returns an independent copy of the sanitized summary.

From the repository root with the modules installed there and verifier under
`scripts/`:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest test_battlelobby_tail -v
python battlelobby_tail.py MEMBER.bin --start-bit KNOWN_TAIL_START --profile historical-tail --report NEW_AUDIT.json
python scripts/verify_battlelobby_tail.py --original ORIGINAL.StormReplay --candidate R8.StormReplay --output NEW_FIXTURE_REPORT.json
```

To reproduce the full current cohort, add `--cohort-manifest MANIFEST.json
--cohort-root DIRECTORY` to the verifier. Paths in the manifest must remain
inside the explicit root; each replay digest and admitted canonical98348
reference status is checked. Inputs use the bounded regular-file reader.

The20 focused tests use frozen small historical/current complete suffixes with
nonzero unknown data and optional branches. They verify semantic observations,
private identity/seed comparisons, malformed profiles, count mismatch, UTF-8
corruption, truncation, extra bytes, EOF padding, immutable encoding, privacy,
and exclusive JSON output. This is complete observed suffix serialization
coverage. It does not establish a migration between the profiles, modern
engine acceptance, deterministic simulation or playable replay recovery.

The newer canonical-LF fixture report corrects the original41810 schema hash
from a CRLF checkout to the exact pinned Git blob879d228d...866fd. See
`observations/canonical-schema-line-ending-correction-2026-10-18.json`; the
older report remains historical. The fourteen fixtures were rerun successfully.
