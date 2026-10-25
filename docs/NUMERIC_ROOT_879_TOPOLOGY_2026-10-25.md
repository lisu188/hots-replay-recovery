# Numeric root 879: retained metadata topology

The selected result now contains the complete transitive closure of numeric root **879**: **22 records and 28 references**. Root 879 is decoded as `STRUCT` with eight numeric tags, `0..7`. All type and field names remain `null`. This adds numeric shape to the [previous transfer and selector checkpoint](REPLAY_HEADER_TRANSFER_IDA_AND_ROOT_SELECTOR_2026-10-25.md), whose publication baseline is `226baa93d4b0117d519e6e9ca2da9915897f16c7`.

The producer parsed a retained 13,744-byte program using pinned grammar and stripped-profile sources. Its saved receipt reports validation of all **1,192 records**, **982 materialized fields**, ordered record boundaries, child-reference bounds and the explicit final **12 zero bytes**. The producer completed once with exit code 0 and emitted an 8,010-byte complete selected closure under its 32,768-byte result cap. The root, peer result review and separate parser source review accept that result with native-layout limits. Publication preparation checked the saved JSON graph without rerunning the parser or reading the program binary.

| Root tag | Immediate record | Retained numeric path and shape |
|---:|---:|---|
| 0 | `USER 880` | `STRING 878`; decoded bounds `0..32` |
| 1 | `USER 881` | `STRUCT 20`; six tags `0..5`, described below |
| 2 | `USER 882` | `ENUM 877`; decoded bounds `0..7`, listed tags `0..3` |
| 3 | `USER 883` | `INT 3`; value bounds `0..4294967295` |
| 4 | `BOOL 884` | Direct `BOOL` record |
| 5 | `USER 885` | `STRUCT 124`, tag `1` points to fixed-length `BLOB 125` with bounds `16..16` |
| 6 | `USER 886` | `INT 3`; value bounds `0..4294967295` |
| 7 | `USER 887` | The same `STRUCT 124` / `BLOB 125` path |

Within `STRUCT 20`, tags `0..3` pass through `USER 23..26` to `INT 29`, whose value bounds are `0..255`. Tags `4..5` pass through `USER 27..28` to `INT 3`, whose value bounds are `0..4294967295`. These are decoded kind and bound records; they establish no native object layout. The companion JSON retains the exact decoded bound parameters and all 22 numeric record shapes.

The earlier single eight-byte source-file read returned **879** at RVA `0x27C9F20` and **888** at adjacent RVA `0x27C9F24`. The retained parser-call composition associates the former slot with this selected root. The adjacent value remains a separate static-source observation. Runtime dispatch was not observed. Any descriptor offsets in the underlying result locate records within the saved program stream; they are not offsets in a native output object.

The numerical topology leaves the schema-to-native bridge open. No type or field name, native object offset, field at `T+8` / cache `O+0x1410`, build/version meaning, output writer, controller instance or lifetime is established. The prior conditional transfer relation remains subject to its normal-frame, ABI, valid-range and concurrency assumptions, and later helper/callback alias effects remain unresolved.

This publication contains a sanitized summary and evidence hashes. Its preparation read pinned retained text only and performed no client, Computer Use, IPC, native-tool, network, replay, repository or canonical-state operation. The separately recorded producer read the retained program and its parser/profile text; publication preparation did not repeat those reads. Playback was not tested, and both full-upgrade flags remain false.
