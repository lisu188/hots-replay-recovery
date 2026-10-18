# Offline battlelobby attribute-layer capacity migration

The source member inherited by R8 retains a 2016 attribute-capacity layout.
Its dependency prefix was updated earlier, but the remainder was copied intact.
Reading the first attribute's value count with the modern 12-bit width gives
18 instead of the original 2 and loses alignment before the eventual C# parser
overrun. The correctly bounded values are `Part` and `Watc`.

`battlelobby_attribute_layer.py` models two explicit observed profiles:

| Profile | Value-list count | Value index |
| --- | ---: | ---: |
| `legacy-10` | 11 bits | 10 bits |
| `observed-11` | 12 bits | 11 bits |

These are inferred capacity profiles, **not an authoritative complete Blizzard
schema** or an automatic mapping from every build number. The original's 68
attribute definitions and 68 selected choices parse coherently with the old
profile. Every one of 428 values in its separate attributes stream matches.
Two genuine-source 98348 Dragon Shire recordings have 87 definitions and
selections and round-trip under the modern profile. Different working-set slot
layouts require separate mapping; the original scope cross-check deliberately
does not invent modern remaps.

The eight-bit field called `a170Length` by the independent C# reader is modeled
only for observed tags 0 and 1. Tag 0 contains a global `(index, IsSet)` pair;
tag 1 has a five-bit slot count and interleaved pairs. All real observed
by-player defaults have 16 slots. This accounts for the apparent 170-to-185-bit
group expansion and its following 20-to-21-bit group. Unknown fixed fields,
optional metadata, float bits and trailing nine bits are preserved numerically.
Unsupported tags, noncanonical padding, invalid indices and unsupported sizes
are rejected.

The codec walks the dependency prefix, definitions, selected choices and locale
handles. It then keeps the entire remaining suffix opaque and byte-identical.
It never follows embedded paths. Its audit omits dependency path bytes and does
not publish player account records. No donor's attribute catalog, settings,
players, seeds or defaults are copied.

Every decode checks same-profile byte reconstruction. Transcoding checks field
identity, suffix identity and exact inverse recovery. The observed R8 member
grows from 41,918 to 42,106 bytes, widening 166 count fields and 1,336 index fields.
The prospective member SHA-256 is
`bee7a6367574224321539ab21f0613e7c8e369a588327a2758ec53d64efe5edd`.
No whole replay is created by this tool.

## Commands

Audit an extracted member, optionally checking it against the immutable original:

```text
python battlelobby_attribute_layer.py audit INPUT.bin --source-profile legacy-10 --original-replay ORIGINAL.StormReplay --report NEW-audit.json
```

Produce a separate member file and a complete width-change audit:

```text
python battlelobby_attribute_layer.py transcode-member INPUT.bin --source-profile legacy-10 --target-profile observed-11 --original-replay ORIGINAL.StormReplay --output NEW-member.bin --report NEW-transcode.json
```

Outputs must be new files. `.StormReplay` output names are refused. The optional
original cross-check requires the recovery repository's MPQ reader and pinned
Blizzard protocol checkout on `PYTHONPATH`; the layer codec itself uses only
Python's standard library.

Focused fixed-golden, malformed-input, bounds, semantics and output-safety checks:

```text
python -B -m unittest -v test_battlelobby_attribute_layer
```

Real original/R8 and modern-control verification, without writing any member:

```text
python scripts/verify_battlelobby_layer.py --original ORIGINAL.StormReplay --candidate R8.StormReplay --modern-reference MODERN.StormReplay --output NEW-fixture-report.json
```

Repeat `--modern-reference` for at most four references. The verifier requires
the exact original and R8 hashes, compares all 428 original attribute values,
checks exact inverse recovery, and independently validates each supplied 98348
reference's observed core payloads through pinned Blizzard schema 96477.

## Independent parser boundary

The unchanged Heroes.StormReplayParser 2.3.0 reader fails in the original R8
attribute-definition loop. The prospective member passes that loop and advances
to a later `ChoiceSection2` failure in old mod metadata. Therefore this repair
is a bounded partial format correction. It does not establish full battlelobby
compatibility, game-data identity, unit allocation, simulation parity or playback.
No synchronization data is removed or changed.

Modern primary code reference:
https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs


The local focused suite passed all 23 tests with no skips. Root independently
reproduced all four real fixture checks (original, R8 and both current donors).
The workflow in `.github/workflows/battlelobby-attributes.yml` separately runs
the focused suite and the restored original/R8 checks on Linux and Windows.
Its actual outcome must be checked; creating the workflow is not a CI pass.
The modern donor replay files are not committed or uploaded by this workflow.

The user requires offline-only work. Do not launch HotS to test this change.
Historical community schemas and genuine current recordings are being used
to investigate the remaining mod metadata layout separately.


The final combined local run passed 42 tests (23 attribute-layer tests and 19
existing mod-data-audit tests), with no skips or failures. Its first attempt
found the existing integration test's expected source fixture absent; restoring
the tracked Base64 artifact to its ignored work path and verifying its SHA-256
resolved that setup issue. The independent code review also found that a
missing report directory could leave a member without an audit; all output
parents are now checked before either write, with three new regressions.
Multiple output writes are still not an atomic transaction.
