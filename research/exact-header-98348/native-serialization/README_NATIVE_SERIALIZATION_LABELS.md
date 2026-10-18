# Byte-only Base98348 serialization-label research

The one inspected PE is the installed
`Versions/Base98348/HeroesOfTheStorm_x64.exe`,53,573,840 bytes, SHA256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
The resource FileVersion string is `2.57.0.98348`. The fixed version resource
has16-bit words `2,57,0,32812`; its last word equals98348 modulo65536. It is
reported separately and was not substituted for the full textual build.

Neither helper executes, maps as an executable, or loads any game image/DLL.
No debugger, injection, process inspection, installation, network operation or
replay read/write is used. The image is read as ordinary bytes. No binary copy,
raw data-context dump or disassembly is saved.

`inspect_native_serialization_labels.py` performs a single bounded53,573,840-byte
RAM read, parses PE headers/version resources, scans ASCII/UTF-16LE static
strings, and records short allowlisted names with physical offsets/section/RVA.
The compact94,239-byte report retains320 selected labels and explicit match,
exclusion and truncation counts. Catalog names and possible serialization
labels are separate categories. Data-only MSVC RTTI structure checks found29
COL candidates; many named types are user-interface classes. No serializer
field semantics follow from those structures. The narrow RIP-relative byte-form
scan found no hints to the selected exact string starts. It does not constitute
instruction decoding or prove absence of code references.

`inspect_native_descriptor_contexts.py` performs one further bounded read of the
same PE, bringing total image reads to107,147,680 bytes. It examines a33,666-byte
union of contexts around11 occurrences of four requested labels, against an
explicit64KiB context limit. Its62,514-byte JSON contains only names, offsets
and candidate-grammar outcomes. No complete protobuf FieldDescriptorProto or
DescriptorProto candidate passed the bounded checks. This rejects that narrow
candidate grammar; it does not identify the surrounding custom container.

Concrete labels are all in `.rdata`:

| Label | File offset | RVA | Observed nearby type names |
|---|---:|---:|---|
| `replay.server.battlelobby` |41668408|41672504|Other replay stream filenames|
| `m_licenseCatalog` |43393499|43397595|`Battlenet::Client::BattlePay::GetInfoResponse`|
| `m_licenseInstance` |43396498|43400594|`Battlenet::Client::BattlePay::LicenseUpdate`|
| `m_clientLicensesList` |43426603|43430699|`Battlenet::Client::S2Game::EncodedGameDataHeader`|
| `m_mapNamespace` |43476303|43480399|`Battlenet::S2Map::BnetHeader`|

There are four `m_mapNamespace` copies and three `m_clientLicensesList` copies.
The BnetHeader neighborhoods contain the familiar archive handle, definitions,
result definitions, variants, dependency and arcade-data labels. Encoded game
header neighborhoods contain map/header handles, definitions, resource map,
resource access list and client-license type labels. These observations are
useful locations for a later formal schema/container examination. Adjacency
does not establish field membership, bit widths or a connection to a particular
opaque replay block. BattlePay label neighborhoods must not be promoted into
battlelobby license/availability semantics.

No available Python pefile/capstone/iced_x86/lief/yara package or PATH objdump/
llvm-objdump/dumpbin was found. Existing Ghidra directories were observed but no
Ghidra/headless import or analysis was invoked. A later disassembly step would
be a separate recorded operation, not part of this evidence.

Both executed sources are frozen machine-specific research helpers and refuse
an existing report. Their reported source hashes describe the actual executed
bytes. The two JSON reports total156,753 bytes, below256KiB. The five-file
allowlist contains only these sources, reports and this README. It contains no
game binary or player/account data.

No174-to198-bit mapping,32-byte availability interpretation, missing current
DataMod MapNamespace value, header reconstruction or replay conversion is
established by this research.
