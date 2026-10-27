# Typed native sync records in the startup audit

The startup audit now decodes synchronization record boundaries and recorded
gameloops instead of assuming that every record occupies five bytes. The
original TEN_GREYMANE member and unchanged R8 contain **308 records**, beginning
at recorded loop **64** and ending at **19,712**. Their complete sync-member
bytes are identical. A genuine current98348 control contains **304 records**,
beginning at loop 64 and ending at 19,456. This supplies a concrete recorded
comparison position for future diagnostics; it does not identify the first
actual simulation mismatch.

The paired [observation](../observations/native-sync-member-audit-2026-10-27.json)
records the actual fixture fingerprints, complete-member checks, source pins,
focused tests and limits. No replay archive or serialized synchronization value
was changed.

## Implementation and native profile

`portable_sync_98348.py` provides bounded in-memory decoding and source-preserving
inverse encoding. Its explicit profile is `native-sync-98348`. The pinned
[21-type closure](../observations/native-sync-98348-type-closure.json) comes from
the stripped current-client sync program with 1192 declared records and context
VA `0x14393EB80`. It is separate from the 8330-record Battlenet registry. The
closure's SHA-256 is
`0c0227b406fcde24f2b3bd56466eae9e867be3b3abeb3f6df303629a10599e1b`.

The physical profile includes:

- A two-bit delta choice with payload widths 6, 14, 22 or 32.
- Event identifiers 1 and 2, encoded as one bit with minimum 1.
- An event 1 word vector with an eight-bit count and u32 elements, followed by a
  u16 value; event 2 contains the u16 value without a vector.
- Byte alignment after each record. The decoder retains the original delta
  choice and alignment bits, including noncanonical wide choices and nonzero
  padding, so the inverse does not silently normalize an input.

The codec caps input size at 1 MiB and record count at 200,000. It rejects
truncation, invalid scalar/shape bounds and ambiguous u32 frame accumulation
wrap. Empty input is a valid empty codec stream; the startup audit separately
requires a nonempty member. These are explicit research-profile limits, rather
than claims about every native engine input the client might accept.

`audit_startup_interval.sync_summary` uses the actual decoded boundaries to
report record lengths, identifiers, delta choices, vector counts and first/last
recorded gameloops. Its elapsed/64 count comparison remains a count observation.
It does not equate that comparison with a cadence or first failing tick. Large
record contents and parsed anonymous payload values are not emitted in its
summary. No replay writer or migration policy is added.

## Actual members and independent comparison

| Pinned input | Sync bytes | Records | Recorded loop range | Observed event IDs |
| --- | ---: | ---: | --- | --- |
| Original 41810 | 1540 | 308 | 64–19712 | event 2 only |
| Partial R8, declared 98285 | 1540 | 308 | 64–19712 | event 2 only |
| Genuine 98348 control | 1520 | 304 | 64–19456 | event 2 only |

Every observed delta is 64; all three members use the 14-bit delta variant and
five-byte records, with zero alignment padding. Other legal physical record
lengths and event 1 vectors are covered by synthetic literal tests, not by these
three observed members. This result does not establish historical native
semantics for 41810 or 98285: the old bytes are being interpreted under the
explicit current-native physical profile.

All **920 records** were compared field by field, including offsets and padding,
with a separate authored native-field adapter using Blizzard's unchanged
[`BitPackedBuffer`](https://github.com/Blizzard/heroprotocol/blob/9af3ea7150f1a8acb53464c92519a9bbcc7a3594/heroprotocol/decoders.py).
The pinned source is 9199 bytes, SHA-256
`17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1`.
This compares independent bit-reader implementations; it is not an official
upstream sync-payload schema. The small six 1.17.0 dependency was extracted from
its SHA-verified PyPI wheel into private task storage, with no global install.

Each whole member re-encoded exactly. All three replay SHA-256 values and
device/file-ID/size/modification-time identities remained unchanged. No raw
member or anonymous u16 values were published. The inverse reproduces recorded
values; it neither derives the current computed checksum nor replaces a failed
expected value.

## Validation and remaining playback evidence

**67 focused tests passed**, with zero failures, errors or skips: 8 codec tests,
30 startup-audit tests and 29 neighboring catalog-diagnostic tests. Literal wire
oracles cover width transitions, both payload forms, maximum vector count,
truncation, nonzero padding and frame overflow. The actual three-member check is
separate from those synthetic tests. The full local corpus was not rerun while
C: remains over the 90 percent disk guard; hosted CI must be checked for the
published commit independently.

The dedicated startup workflow was updated with the five reviewed codec/audit
source pins, all three focused test modules and the expected total of 67 tests.
Its actual-replay gate now checks the typed sync profile, recorded loop range,
event IDs, record lengths and explicit absence of a divergence/playback claim.
The workflow also retains the codec and pinned type closure with its diagnostic
artifact. The [follow-up verification](../observations/native-sync-startup-ci-2026-10-27.json)
records two fresh complete-stream audits of the original and R8. Both produced
the same 7034-byte report, SHA-256
`fef71828b69962c7adaacea0a8ab05264dc786d3e7cd513aa2bd0383eec3d328`.
The focused fixture check took 17.015 seconds. Both embedded workflow Python
blocks passed syntax checks and its actual source-pin block executed locally.
This does not claim that the whole Actions job or its separate mpyq checks ran
locally, and does not replace the pending hosted result.

The official [EU build manifest](https://eu.patch.battle.net/hero/versions), read
at 2026-10-27T13:14:09 UTC, still declares **2.57.0.98348**. The 874-byte response
has SHA-256
`f94345ccb04cd3c794ceceb7395efbe6e314eb9a0aec7cb6c3a779b400d74cf4`.

The native diagnostic report's runtime frame, actual checksum and expected
comparison value remain the next acquisition target. Recorded loop 64 alone is
not an observed mismatch. Historical resource/player/catalog semantics and
engine state reconstruction remain incomplete. No Computer Use, game launch,
target-code execution, synchronization bypass or new playback claim occurred.
R8 remains `98285-resumable-r8`; both full-upgrade flags remain false.
