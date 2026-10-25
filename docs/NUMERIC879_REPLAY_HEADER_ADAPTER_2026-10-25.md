# Source-preserving numeric879 replay-header adapter

`native_replay_header.py` interprets versioned user-data headers using the
published 22-record numeric879 topology and a separately pinned Blizzard
decoder. It does not infer native output-memory offsets, controller ownership,
runtime dispatch or a build-retarget policy. Listed ENUM membership is an
adapter constraint derived from the selected metadata; it is not evidence that
the native client rejects every unlisted value.

The module reuses
`observations/numeric-root-879-topology-2026-10-25.json`; it adds no duplicate
schema asset. All native type and field names remain unauthenticated. Names
used by the official comparison describe wire tags only.

## API

```python
from native_replay_header import (
    decode_header879, encode_header879, replace_existing_int,
)

source = decode_header879(raw_user_header)
assert encode_header879(source) == raw_user_header
numeric = source.value                 # independent copy with integer tag keys
unknown = source.unknown_paths         # preserved in the underlying wire tree
missing = source.missing_paths         # reported without inserting defaults
changed = replace_existing_int(source, (1, 4), requested_integer)
changed_bytes = encode_header879(changed)
```

The example is a wire edit, not authorization or policy for choosing a target
build. The integer must have exact Python `int` type: `bool` is refused. The
path must identify an existing known integer leaf. Missing fields, unknown paths,
boolean leaves and invalid range/enum values are refused without modifying the
source view.

`decode_header879` accepts at most 4096 bytes and requires exactly one complete
versioned node. Both decoding and encoding enforce selected numeric constraints,
independent official projection and exact EOF. The ordered `lossless_wire.Node`
tree remains authoritative. Unknown fields, nonminimal count/key/integer
spellings and negative zero survive unchanged output and a reversed edit.
Public value projections are copies; a named dictionary or canonical encoder
does not replace the original wire tree.

## Actual local checks

The staged implementation passed 17 focused tests with no failures, errors or
skips. They cover independent literals, missing/unknown/deprecated optional
fields, duplicate keys including negative-zero aliases, every truncated prefix,
trailing bytes, source pins, numeric bounds, and edit/reverse preservation.
Signature length 33 and enum value 4 demonstrate where the official schema is
broader than this selected metadata profile.

The separate CLI checked the original 41810, R8 partial 98285 and genuine
public 98348 controls. All three declared user-data headers are 119 bytes and
roundtrip exactly. For each, the controlled RAM edit changes only tag path 1/4.
The edited bytes are decoded directly with both pinned official 41810 and 96477
schemas, and their complete named projections are compared with the original
projection plus that one change. All six edited-byte oracle comparisons passed,
and reverse edits restored the exact source bytes. This check is stronger than
checking an edited numeric view alone.

Local fixture authentication reused a SHA-bound previous full-hash report and
matching current four-field identities. It read 417 additional prefix bytes and
no additional full hashstream. That mode requires an explicitly supplied trusted
receipt SHA; it is not a fallback after a guard mismatch. The CI default performs
one full SHA pass per fixed fixture, with a combined 4 MiB cap. No archive members
are read and no replay or user-header payload is written by the CLI.

## Source pins and format scope

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| Existing numeric879 topology | 9536 | `6765c0d8795f3af57333d200e1ea722818e965158bf46a804574a78d4fe2b17b` |
| Existing lossless wire engine | 11513 | `9d725f9be88c4185419a306ef995e82a774d174a93912ffd381cced2d6ebb7a7` |
| Blizzard decoder | 9512 | `c5e4e7c588ebc2ef722ab9fd9def2e67e309c45d451639cfdee3126b0f616a42` |
| Official 41810 schema | 25890 | `879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd` |
| Official 96477 schema | 26921 | `e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84` |

The existing workflow pins Blizzard/heroprotocol to
`9af3ea7150f1a8acb53464c92519a9bbcc7a3594`. The saved 97771 file is identical to
96477 and is not used as an independent release oracle. Compatibility with the
genuine 98348 payload does not assert an official 98348 schema release.

Numeric879 root tags 0..7 and version tags 0..5 correspond to the observed official
wire fields after USER unwrapping. Signature bounds, enum membership and a
deprecated optional hash member differ between the schemas. The original 41810
header already satisfies the observed constraints. Historical digest semantics,
version policy, package/rule migration and full replay compatibility remain open.
BitPackedDecoder gave different/incomplete projections for actual versioned
headers; a nonthrowing decoder alone is not acceptance evidence.

## CI and CLI

The minimal workflow change reuses the existing original restoration and current
EU acquisition. It restores R8 from its already published hash-bound Base64
parts, runs the CLI once, and retains only the sanitized report. Root unittest
discovery automatically includes `test_native_replay_header.py`.

```sh
python -m unittest -v test_native_replay_header
python scripts/check_replay_header879.py \
  --original work/TEN_GREYMANE_source_41810.StormReplay \
  --r8 work/header879-R8.StormReplay \
  --current "$HOTS_EU_REFERENCE_CONTROL" \
  --report work/header879-audit.json
```

The report contains source/header hashes, lengths, counters and boolean results.
It contains no raw header, player data or private source identity fields. Input
fixture restoration in CI is separate from generating a converted replay.

These are staged local checks. This adapter has not yet run in exact-head CI,
and no client, Computer Use, IPC, target execution or playback validation is
claimed.
