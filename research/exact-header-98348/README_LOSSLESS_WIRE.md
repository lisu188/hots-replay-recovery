# Lossless versioned-wire research codec

`lossless_wire.py` parses a single complete wire value into mutable `Node(tag,
value)` objects. It preserves wire tags, struct field order, choice tags,
optional presence, unused bit-array padding bits and original varint spellings.
The encoder performs no I/O. It neither assigns field semantics nor selects
metadata for reconstruction.

The source of tag and signed-magnitude varint semantics is Blizzard's pinned
`heroprotocol/decoders.py` at commit
`9af3ea7150f1a8acb53464c92519a9bbcc7a3594`, especially lines197–270 and
`_skip_instance`. The task-local source SHA256 is recorded in the receipt.
The independent existing `depot_s2mh_wire` decoder supplies the second decode
comparison. Tag7 and tag8 payloads stay opaque fixed-width bytes; no float or
FourCC interpretation is selected.

| Tag | `Node.value` |
| --- | --- |
| 0 | `list[Node]` |
| 1 | `(bit_count: int, raw: bytes)` |
| 2 | `bytes`, with a counted blob prefix |
| 3 | `(choice_tag: int, child: Node)` |
| 4 | `None` or the present child `Node` |
| 5 | Ordered `list[(integer_key, child_Node)]` |
| 6 | Integer 0–255; raw byte value, without boolean normalization |
| 7 | Exactly four opaque bytes |
| 8 | Exactly eight opaque bytes |
| 9 | Signed-magnitude integer |

```python
from lossless_wire import parse, encode, clone, Node

original = parse(raw_header)
assert encode(original) == raw_header
candidate = clone(original)
header = candidate.field(0)
attributes = header.field(5)  # tag0; .value is an editable list of Nodes

# Only edit values whose identity and wire template are independently known.
# .field returns an existing struct child; .set_field replaces an existing
# field without moving it or changing the retained spelling of its key.
known_integer = attributes.value[known_index].field(known_field)
assert known_integer.tag == 9
known_integer.value = independently_observed_integer
candidate_bytes = encode(candidate)
assert encode(original) == raw_header
```

`parse(raw)`, `encode(node)` and `clone(node)` use only the Python standard
library. `to_generic(node)` imports `Choice` and `BitArray` from the existing
`depot_s2mh_wire` module solely to return directly comparable generic values.
It does not infer wire tags from a generic dict or list. Generic decoding loses
distinctions such as blob2 versus fixed7/8, so no automatic generic-to-wire
conversion is provided. A cloned authenticated Node supplies an explicit
template for an edit.

The codec retains original integer, choice, count and map-key varint bytes
when their logical values are unchanged, including nonminimal encodings and
negative zero. Changed logical values use canonical signed-magnitude bytes.
Changing array/blob length regenerates its count. Explicitly rearranging the
ordered map list changes field order; keys keep their original spelling when
the same integer key is retained. An independently cloned tree can be edited
without altering its source.

Limits are two MiB of input/output, 200,000 visited nodes, depth64 and
200,000 elements/bits/blob bytes per counted value. Varints use at most ten
octets, with signed magnitude at most `2**69 - 1`. Duplicate struct keys,
trailing bytes, unsupported tags, optional flags other than0/1, truncation,
wrong-width fixed blobs and cyclic mutable graphs are rejected. These bounds
describe the supported research profile, not every encoding the official
unbounded decoder might accept.

Twenty-one focused tests cover literal all-tag encodings, map order, clone
isolation, edits and canonical re-encoding, nonminimal varints/negative zero,
choice/optional distinctions, retained padding, every truncated prefix of a
compound value, malformed trees and resource limits. Thirty-six distinct
content-addressed controls (five original EU,28 cached payload-matching
candidates and three exact current US handles;2,598,006 bytes total) each pass
original and cloned byte-for-byte roundtrip and generic decode equality.
`verify_lossless_wire.py` emits only hashes, sizes, structural metrics and
booleans. Existing cache files are read only; nothing is fetched.

Run focused tests with this directory and the repository on `PYTHONPATH`:

```text
python -B -m unittest -q test_lossless_wire
python -B verify_lossless_wire.py
```

The actual-fixture verifier is a machine-bound research source using the
existing task/cache paths. It writes a new report only and refuses to replace
an existing one. Re-running requires a different report destination or an
explicitly reviewed wrapper. The frozen report is retained as
`lossless-wire36-control-verification.json`.

No candidate metadata bytes are published by this codec. Reconstruction is
accepted only by matching the entire already-observed target content SHA256;
these serialization checks alone establish no target reconstruction, unknown
timestamp/signature value, package version binding, replay conversion or game
playback result.
