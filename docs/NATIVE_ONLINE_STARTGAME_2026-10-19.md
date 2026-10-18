# Current native online lobby reader

`native_startgame.py` is a read-only reader for native type5917,
`Battlenet::Event::S2GameEngine::OnlineStartGameRequest`, from the authenticated
98348 executable snapshot. It consumes the member from bit0 through EOF and
retains every wire token. Encoding must reproduce the entire input exactly;
same-width token changes are rejected. This module does not produce replays,
apply historical transformations or establish deterministic simulation parity.

The513-type JSON closure is pinned to SHA256
`0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640`,
PE SHA256 `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`
and embedded native-metadata SHA256
`ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741`.
The private field/token types are imported from the frozen `native_clientinfo.py`
source pinned to `e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202`.
The selected graph also contains offline type5962 as a source dependency;
the public decoder accepts only the explicit `online-start-98348` profile.
No PE, native client, DLL, SDK, network request or machine-specific path is used.

The public API accepts an already bounded `bytes` member:

```python
from native_startgame import PROFILE, decode_startgame, encode_startgame

value = decode_startgame(member_bytes, PROFILE)
assert encode_startgame(value) == member_bytes
facts = value.summary()
```

`audit_current_startgame(member_bytes, profile=PROFILE)` returns the same safe
summary directly. It reports the25 named root spans, member digest and bounded
array counts, without author, account, session, client or license values.
Decoded objects, fields and tokens have disabled `repr`; their contents remain
private to callers. Archive executable/base/data build, NGDP root, genuine-source
provenance, core-stream roundtrips and private initData/details comparisons are
separate caller checks and are not granted by successful native decoding.

The input limit is8MiB. Independent local budgets cap fields at500000, wire
tokens at250000, arrays at32768 elements, strings/blobs at4096 bytes, and
recursive depth at64. Field limits are checked before entry and again before
the post-recursion append. Shared decoder globals are never modified.
Byte-alignment padding must be zero. At most seven zero bits may follow the
native payload to complete its final byte; extra bytes and nonzero EOF padding
are rejected and the framing padding is reported separately.

Run the14 focused tests with standard Python:

```shell
python -m unittest discover -p test_native_startgame.py -v
```

The fixtures use an independent physical-bit writer and invented values only.
They include nonempty native branches that the older observed opaque grouping
cannot generally describe: season ratings, unlockable overrides, license IDs,
variable mastery-tier counts and rejoin handles. They also cover ASCII/UTF8,
bit arrays crossing64 bits, real64 bit patterns, native/generic limits, EOF and
alignment, schema/shared-source pins, privacy, independent field/wire budgets
and same-width mutation rejection. Real replay-cohort verification is recorded
separately and must not be inferred from these synthetic fixtures.
