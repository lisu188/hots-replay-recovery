# Native report output route - 2026-10-25

The current 98348 client has a conditional native text-report output route.
The inspected diagnostic-subsystem initializer enables its output byte; the
cleanup routine clears it. This byte is not an authenticated user setting.
The route supplies useful file-discovery clues without proving that a report
was created for TEN_GREYMANE or recovering its actual output directory.

This supplements [Native sync diagnostics](NATIVE_SYNC_DIAGNOSTICS_2026-10-25.md).
The companion [source-pinned receipt](../observations/native-report-output-route-2026-10-25.json)
records instruction anchors, literal bytes and fragment limits. Function and
global addresses below are RVAs in the pinned 98348 client; member offsets
are identified separately. Three Ghidra jobs used the existing project
read-only and discarded changes. No Computer Use, game launch, native target
execution, replay read or write, settings change or synchronization change
occurred in this supplement. Full upgrade and playback remain unproved.

## Initialization is separate from the replay gate

The selected assembly of `27C440` resets callback count `3007FD0` at
`27C50B`, then unconditionally sets byte `3004140` to 1 at `27C511`, among
string, lock and container initialization. The selected `27D160` cleanup
routine clears the byte at `27D1F3` while freeing the corresponding objects
and buffers. These instructions authenticate initialization and cleanup on
the inspected paths. They do not enumerate every possible write, establish
actual runtime state or recover a Variables.txt key, Cvar or console command.

The separate staging setup gate `G+CB10 & 8` still controls construction of
the detailed replay-desync report. The output lifecycle byte cannot be used
as a substitute for that prerequisite. Neither field was changed.

## Conditional text output

For the submitted type5 Replay Desync report, `27E2B0` supplies dispatcher
argument2 zero. `27E710` preserves it in R15D at `27E734` and supplies it as
argument4 to `2D9C00` at `27ED05`. Registered callbacks run before report
classification and may modify the report; the described nonfatal branch
therefore remains conditional on their effects and the output byte.

The selected `2D9C00` assembly preserves incoming RCX/RDX views and, when
R9D is zero, calls `2D8E40` at `2D9C83`. Its scalar-looking decompiled
arguments do not override that assembly binding.

`2D8E40` preserves the incoming filename view, copies it into path object
`32C8C98` at `2D916A`, and passes the authenticated literal `txt` to helper
`2A0350` at `2D9190`. It initializes a local registered file object through
`2A0BC0` at `2D91EA`, using flags `0xA` and zero arguments4/5. The retained
registration contract leaves its initial main-write inhibit counter at
member `+30` zero: flags bit0 is clear and the optional argument5 object is
null. This is an initial local-path derivation, not an observed runtime
counter or proof of successful opening.

The function builds a stream wrapper referring to that file object, passes
it with the report to serializer `2DC7A0` at `2D92DF`, then invokes file-object
teardown `2A0DB0` at `2D9316`. This authenticates an output attempt. The
complete serializer, stream callbacks and native operating-system write
contract have not been recovered end to end, and no created file or written
report was observed.

It subsequently supplies the authenticated literal `dmp` to a path helper
and conditionally calls `304330` at `2D93C4`. This is a conditional dump
attempt; its format and successful creation are unproved.

## Path clues and remaining directory gap

`27DEB0` calls path builder `2A1440` at `27DEF0` with flags `760000`.
Assembly preserves the incoming R8 destination path through that call,
although the decompiled call omits this third argument. In later expanded
blocks, its true-argument branch extracts a component, appends the
authenticated literal `.error` at `27E013`, and passes the composed component
to `2A0510` at `27E045`. Its false-argument branch supplies `error` to
`2A0350` at `27E09A`.

The literal mutation helpers have not been independently recovered. These
facts do not yet prove an exact `.error.txt` basename, a `.error` directory
container, or the complete relative filename. Retained `2A1440` assembly
conditionally prefixes the directory-like field `return(2E4AE0)+170`; that
field's runtime value remains unknown. No install, Documents, GameLogs or
Errors directory is substituted for the missing value.

Names containing `.error`, error-related text files and dumps are bounded
discovery candidates in existing authorized folders. Exact report strings
such as `Replay Desync` and `Desync between recorded replay and playback
simulation` can distinguish candidate text. A match still needs build,
time and replay attribution. This supplement performed no new runtime
capture and supplies no first failing native frame or checksum.

## Fragment and verification limits

| Entry RVA | Selected instructions | Expanded instructions | Outside blocks | Expanded size-limit truncation |
| --- | ---: | ---: | ---: | --- |
| `27C440` | 74 | 70 | 1 | true |
| `27D160` | 78 | 78 | 0 | false |
| `27D8E0` | 6 | 186 | 30 | false |
| `27E0B0` | 19 | 108 | 19 | false |
| `2AD6C0` | 160 | 160 | 0 | false |
| `2D9C00` | 46 | 146 | 22 | false |
| `2D8E40` | 758 | 749 | 0 | false |
| `27DEB0` | 18 | 126 | 15 | false |

The initializer's expanded export is explicitly truncated. Its selected
listing contains the decisive stores; the large decompiled continuation is
not a complete recovered configuration registry. The `27D160`, `2AD6C0`
and `2D8E40` selected intervals have no outside decompiler blocks. Other
entries retain their fragment qualifications. Different instruction counts
and a false size-limit flag are not silently treated as full CFG coverage.

Local preparation checked all required instruction anchors, the eight
selected functions, three read-only completion/discard logs and seventeen
authenticated literal bytes. The receipt hashes the retained inputs. No
new production codec or synthetic test was added, and earlier codec CI is
not runtime evidence. These results do not supply historical engine rules,
missing replay values or a playable conversion; expected sync data remains
preserved.
