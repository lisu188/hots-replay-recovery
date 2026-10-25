# Numeric879: actual native handler route

Three static IDA runs now locate the INT, STRUCT and USER branches selected by
numeric metadata in the current header decoder. They decoded **254 bytes into
64 instructions** and exited successfully. The result narrows the native field
binding question: USER builds a recursive child request, STRUCT delegates its
field work, and the INT success path leaves the selected span before its sink.

The source client is build **98348**, x86-64, **53,573,840 bytes**, SHA-256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
The selected bytes came from an existing statically transformed text patch
(analyst-derived static text, not a runtime capture or unaltered on-disk PE text).
Each run used a fresh empty analysis database containing only its selected,
authenticated static text bytes. These runs did not load the original PE as an
input, execute the client, or observe replay playback.

## Selected handler spans

The earlier core at `0x1A76740` obtains a metadata kind through `0x1A6D8B0`,
subtracts one and dispatches through the 16-DWORD table at `0x1A77268`. The
selected table and its kind mapping bind these three entries:

| Kind | Table index | Selected RVA range, end exclusive | Bytes | Instructions |
| --- | ---: | --- | ---: | ---: |
| INT | 8 | `0x1A76DC6` to `0x1A76E69` | 163 | 41 |
| STRUCT | 13 | `0x1A77108` to `0x1A7712D` | 37 | 9 |
| USER | 15 | `0x1A7721A` to `0x1A77250` | 54 | 14 |

These are jump-table entry spans, not authenticated whole-function boundaries.
All three end in an unconditional jump to `0x1A77255`, contain no RET, and have
no fallthrough from their last instruction. Other calls and branches leave the
selected spans. The complete control-flow graph remains open.

## USER: a recursive destination snapshot

At `0x1A77227`, the handler calls descriptor helper `0x1A6D3D0`. After that call,
it takes a context from descriptor+0 and a child type from descriptor+`0x28`.
At `0x1A77235`, it reads the current request's destination at +`0x10` and places
that exact QWORD in a local child record at +`0x10`. The call at `0x1A77249`
passes the reader and the child record to actual core `0x1A76740`.

This proves the destination copy from that post-helper load to the recursive
request. It does not prove that the incoming destination survived the earlier
opaque helper, or that the returned descriptor represents the declared USER
element. Those contracts are required before composing USER881 and USER28
along numeric path `[1,5]`.

## STRUCT: the offset work is delegated

The handler obtains a descriptor through `0x1A6D370` and calls `0x1A77970` with
the reader, returned descriptor and current request. No field-offset loop is
present in the selected 37 bytes. The actual helper must establish tag routing,
field offset use, destination addition and recursive dispatch. The retained
loop in separate core `0x1A70A00` is not substituted for this evidence.

## INT: the successful sink remains outside the span

The selected code compares a consumed byte with9, calls `0x1A77390` with a local
output address, and requires EAX zero before loading a QWORD from that local.
It passes the value and descriptor+`0x28` to `0x1A77FC0`. Nonzero AL branches at
`0x1A76E59` to `0x1A76CEA`, outside the selected span. Zero AL produces EAX one
and jumps to the common continuation. The helper contracts and successful
DWORD sink, width, truncation and unsignedness remain unproved.

## Verification and remaining field binding

Root and independent reviews matched all selected bytes and contiguous
instruction boundaries to the prepared source and recomputed all17 relative
control targets. IDA supplied the instruction decoding; a second instruction
decoder was not run. All three captured process exits are zero. Retained TSV
and JSON payloads total **11,203 bytes**, within the per-run **8192-byte** and
aggregate **24,576-byte** payload limits. These limits do not cap database size.

The corresponding [sanitized observation](../observations/numeric879-native-handler-route-2026-10-25.json)
contains code hashes and evidence pins. It preserves the distinction between
observed call-site flow, conditional composition and remaining unknowns.

The offset arithmetic `0x98 +8 =0xA0` remains a candidate association with
numeric path `[1,5]`. `m_version.m_baseBuild` is an independently established
official wire label; it is not yet a proved native field name at that offset.
STRUCT mapping, both USER contracts, the INT sink and later lifetime/alias
relations must be closed before that composition is accepted.

The baseline `e163ae4` offline and CodeQL runs were still queued when observed
at16:23:02 UTC on2026-10-25. This checkpoint makes no new publication CI success,
full replay conversion or playback claim.
