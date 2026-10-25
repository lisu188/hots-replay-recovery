# Current native `replay.initData` value codec

`native_setup.py` exposes the pinned build98348 native setup reader and value
writer as a production API. Callers can validate a whole `replay.initData`
member, serialize a supplied value tree, reproduce an unchanged source member,
and compare decoded values with the pinned Blizzard protocol projection. This
adds an independent current setup value writer to the recovery tools. It does
not create an upgraded or playable TEN_GREYMANE replay.

The official EU manifest returned `2.57.0.98348` at
`2026-10-25T08:28:27.778601+00:00`. The 874-byte manifest has SHA-256
`f94345ccb04cd3c794ceceb7395efbe6e314eb9a0aec7cb6c3a779b400d74cf4`.
The retained source is [Blizzard's EU versions endpoint](https://eu.patch.battle.net/hero/versions),
with its receipt in
`observations/native-setup-live-target-2026-10-25.json` and body in
`references/hero-versions-2026-10-25.txt`.

## API and representation

```python
from native_setup import (
    decode_setup,
    encode_setup_values,
    reencode_setup_source,
    compare_setup_with_official,
)

setup = decode_setup(member_bytes, profile='setup-98348')
canonical = encode_setup_values(setup.value, profile='setup-98348')
original = reencode_setup_source(setup, profile='setup-98348')
node_count = compare_setup_with_official(
    setup, official_decoded_initdata, official_protocol.typeinfos)
```

The only public profile is `setup-98348`, rooted at native type775. Its exact
anonymous schema contains 200 types and 11 kinds: ARRAY, BIT_ARRAY, BLOB, BOOL,
ENUM, FOURCC, INT, OPTIONAL, STRING, STRUCT and USER. STRUCT and ARRAY values are
tuples; OPTIONAL is `None` or its child value; BOOL and integer values retain
their exact Python types; FOURCC, BLOB and STRING are bytes; BIT_ARRAY is a
`(length, pattern)` tuple. The STRING implementation checks the recovered
native sequence-count rules as well as encoded byte-count bounds.

Native type775 is compared with the pinned Blizzard protocol96477 outer
type71, whose only field is `m_syncLobbyState` of inner type70. The entire
213-record official table is pinned before comparison. This is a selected
wire-value projection. Anonymous native field names, in-memory object layout
and the separate Battlenet root5917 graph remain outside this claim.

The public facade accepts a whole member from bit zero. It does not expose
alternate roots, arbitrary schemas, offsets or STRING callbacks. It verifies
the exact bytes of its three private models and schema, bounds input/output
and traversal work, and rejects invalid field types, values, shape or trailing
data. The frozen decoded object suppresses value representation, and public
summaries retain hashes, sizes, positions and aggregate counters. Official
comparison checks exact built-in containers and leaves before walking them,
so caller-defined objects cannot supply equality or formatting behavior to
the comparison.

## Padding and source identity

`encode_setup_values` writes the supplied logical values with zero alignment
padding. Its result is a canonical serialization, and accepted nonzero
internal source padding can therefore make it differ from the source.

`reencode_setup_source` revalidates the decoded source, hash, payload boundary,
statistics and unchanged value tree, then returns the exact retained member.
It preserves accepted internal padding. The two operations have separate
contracts because equal values alone do not establish source byte identity.
Whole-member decoding requires fewer than eight trailing bits and zero final
padding, and records the payload boundary before consuming that final padding.

The static writer provenance identifies scalar helpers at RVAs `0x1A6EA50`
and `0x1A6EB10`, setup caller `0x133D350`, and the selected dispatch/alignment
helpers. The successful-value model uses declaration-order STRUCT writing
with context zero. It does not execute those native functions or authenticate
runtime pointers, object lifetime, failure prefixes or cached CRC state.
Selected source fingerprints and exact model/schema pins are retained in
`observations/native-setup-codec-provenance-2026-10-25.json`; raw client code and binaries
are not part of this milestone.

## Validation

The focused suite contains 46 synthetic tests: 20 writer tests, 15 public API
tests and 11 official projection tests. It covers all 200 schema types and all
11 kinds, an independent direct-per-bit oracle across offsets0..7 and
widths0..64, a manual unaligned byte vector, strict bounds and type rejection,
budget failures, profile/model pin failures, source tampering, internal padding
and privacy controls. A separate official-table interpreter checks a populated
321-byte/2565-bit synthetic member with 237 compared nodes and an empty/absent
52-byte/416-bit member with 100 nodes. Integer1/booleanTrue equivalence is
rejected in both directions.

The local selected regression run passed all 110 tests: these 46 new tests and
64 existing ClientInfo, MapInfo, StartGame and legacy MapInfo codec tests.
Its source-bound receipt is
`observations/native-setup-local-tests-2026-10-25.json`. This selected run is
separate from the full repository corpus assigned to hosted CI. The new
synthetic tests can be reproduced from the repository root with:

```text
python -m unittest test_native_setup_writer test_native_setup test_native_setup_official
```

Two retained actual replay members were checked without writing a replay,
running the client or using Computer Use:

| Input | `replay.initData` bytes | Payload end bit | Official nodes compared |
| --- | ---: | ---: | ---: |
| Public build98348 control | 111953 | 895621 | 83907 |
| TEN_GREYMANE R8 partial build98285 | 4262 | 34089 | 3520 |

For both members, the source-preserving operation and canonical value writer
reproduced the whole source member exactly. Both happened to contain zero
discarded internal padding. The combined comparison covered 87427 nodes;
whole input file hashes and file identity were unchanged before and after the
check. The public receipt
`observations/native-setup-two-actual-2026-10-25.json` retains only file/member
fingerprints, aggregate counts and these bounded results.

CI for this candidate has not run at documentation preparation time. The
prepared workflow adds the current EU setup gate and retains a sanitized setup
summary. Its eventual run must be assessed against the published commit.

## Remaining conversion work

The R8 replay retains build98285 metadata. Passing its physical setup member
through the current775 graph does not retarget it to build98348 or authenticate
historical field semantics. No new replay was generated, no sync records were
replaced, and no historical defaults were invented.

Full conversion still requires historical resource identities and ownership,
the semantics of the current-only ClientInfo fields and legacy SharedPlayerInfo
branch, compatible catalog state, and deterministic sync/playback evidence.
The codec's byte equality and official value agreement do not prove those
conditions. `full_upgrade_complete` remains `false`.

The selected official protocol table is derived from Blizzard Entertainment's
MIT-licensed heroprotocol. Its complete copyright and permission notice is
retained in `references/heroprotocol-LICENSE.txt`.
