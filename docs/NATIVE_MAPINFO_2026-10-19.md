# Native S2MapInfo 98348 reader

`native_mapinfo.py` adds a separate, explicitly selected `mapinfo-98348` reader.
It decodes all 32 ordered native `Battlenet::Event::S2Maps::S2MapInfo` fields.
The reader requires neither the client nor a game installation. Its selected
191-type schema is 45,724 bytes, SHA256
`3900a63c0799474becd2ecfb03eece4f8c523a965b38e539264867d5cdf2075c`.
It uses the already reviewed native ClientInfo scalar/structure decoder, whose
exact source bytes are separately pinned. The old observed metadata profiles
and their historical receipts remain separate.

The schema is extracted from the actual installed 98348 PE, SHA256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`,
and its independently decoded BSN container, SHA256
`ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741`.
Selected type records, names and bounds are included; the PE, complete container,
raw headers, replays and decoded author/player values are excluded.

## Actual current-reference binding

All 21 already acquired genuine current references pass fresh build/base/data
98348 and NGDP-root checks, full observed mod/tail reconstruction and EOF, and
private identity/seed checks against official initData/details. Their prior core
stream reports are hash-bound, without rerunning all core events in this audit.

All **136 native MapInfo records** match the independently observed metadata
record ends, handle identity pairs and exact consumed bit spans. Every record
has all 32 native root fields. Their final 32 bits resolve as `m_addMultiMod`
(one Boolean bit) plus `m_requiredPermissions` (31-bit count, zero in this cohort).
This is a typed current-layout observation. The implementation also tests
nonempty permission lists using synthetic values and the native 96-bit handle.

The 21-case producer explicitly reads 69,272,280 input bytes, including source
guards and repeated native pin reads, across 29,002,257 distinct replay bytes
(21 current files plus original/R8 guards). No PE read occurs in this binding
stage. Implicit interpreter/import reads are outside the explicit read ledger.
Every current file and the original/R8 hashes remain unchanged.

Thirteen focused tests pass locally. An independent physical-bit writer also
reconstructs all six genuine US Dragon Shire record spans directly from decoded
tokens, without using this module's encoder for that proof. It verifies all 32
contiguous root fields and rejects a saved metadata report with altered offsets.
That independent review does not rerun the full 21-control producer.

## Interface and boundaries

```python
from native_mapinfo import decode_mapinfo, encode_mapinfo, audit_current_map_infos

info = decode_mapinfo(member, record_start_bit, 'mapinfo-98348')
span = encode_mapinfo(info)
aggregate = audit_current_map_infos(member, observed_metadata_report)
```

`span` starts at the byte containing the record start. It preserves preceding
bits in that byte and zeroes unused high bits after the consumed end. It is not
a replacement replay member. The encoder rejects changed wire tokens, source
hashes, profiles or extents. Record objects and nested field/token objects have
disabled value representations. Aggregate reports exclude authors, addresses,
names and player values.

`audit_current_map_infos` freshly parses the observed-current metadata layer.
An optional supplied report must equal that fresh report; offsets cannot be
supplied from another member. The caller must separately authenticate the replay
header/build/root and initData/details. Explicit caps limit schemas, member size,
strings, arrays, recursion and fields/tokens; structurally valid larger records
can be refused by these inspection budgets.

This milestone establishes no historical MapInfo schema, legacy permission
counter width, missing US DataMod namespace, reconstructed dependency header,
complete replay conversion, engine acceptance or deterministic compatibility.
No client or game DLL is loaded or executed and no replay is generated.
