# Switcher missing-build IPC — 2026-10-25

The installed 98348 Switcher resolves a requested client from local `Versions`
directories. When its exact-build lookup fails, the inspected branch returns
result `3` through shared memory. It does not call a downloader or launch another
executable in that branch. This identifies a concrete next source to inspect:
the main client's producer and consumer of that IPC response. No historical
41810 client, build configuration or game-data payload was recovered.

The machine-readable evidence is
[`switcher-missing-build-ipc-2026-10-25.json`](../observations/switcher-missing-build-ipc-2026-10-25.json).
All addresses below are RVAs in the Switcher unless explicitly marked VA.

## Source and validation

The source is `Support64/HeroesSwitcher_x64.exe`, file version `2.57.0.98348`,
773,840 bytes, AMD64, image base `0x140000000`, SHA-256
`cc721ecc93f086c562425a2697878b2622d6a5cde81f9817458e7e68a3e1fe9d`.
Its hash remained unchanged. No imported target code was executed.

Separate temporary Ghidra 12.0.4 projects used a 120-second import-analysis limit
and two CPUs. The completed export contains 18 functions and 1,459 instructions;
the retained verifier compared every exported instruction's bytes against the
source PE. All 1,459 comparisons match. These are static provenance checks, not
native runtime tests. The temporary projects were deleted and their directories
verified empty. The existing main-client Ghidra project was not opened.

The first attempt exported 12 functions and then stopped because requested RVA
`0x3253` is an internal fragment of function `0x3220`, not a separate Ghidra
function. Those partial exports and the failure remain preserved. The second
attempt selected the containing function, added actual initializer/CAS roots,
and completed all 18 exports. A zero headless process exit code alone was not
treated as proof that the first export script completed. Some decompiled return
types are unreliable; the reported status stores and return value use ASM.

## Requested client lookup

The literal `Heroes of the Storm IPC Mem` is at RVA `0x14DC0`, file offset
`0x13FC0`. Product initialization at `0x1060` stores it in product field `+0x340`;
initializer `0x1000` copies that field to global VA `0x140020FF0`. Function
`0x3190` uses the name with `CreateFileMappingA` and maps 65,536 bytes.

| Location | Observed operation |
| --- | --- |
| `0x23F0` | Claims a request by CAS on `shared+0x20`, expected `2`, replacement `1`. |
| `0x24E3`, `0x2500` | Reads the requested build from `shared+0x4C`. |
| `0x2A10` | Resolves `Versions\Base%05d\HeroesOfTheStorm_x64.exe`; the alternate name is `HeroesOfTheStorm.exe`. |
| `0x251A` | After failed resolution, writes `shared+0x24 = 3`. |
| `0x2521` | Sets `EAX = 1`. |
| `0x2526` | Writes `shared+0x20 = 3` and exits the branch. |
| `0x2F30`, call at `0x30E8` | Creates a process from a successfully selected local path. |

For a normal typed request, the selected architecture is tried first; a failed
64-bit lookup may retry the 32-bit executable. The exact-build resolver requires
the directory and a non-directory executable to exist. Both failures reach the
result/state stores above. No fetch call or process creation occurs in that
failure branch. The complete main-client meaning and handling of result `3`
remain outside this observation.

The **unsigned `0xFFFFFFFF` selector uses a different path**: it enumerates local
`Base*` directories and selects the greatest parsed version containing the
requested executable. This highest-installed selection does not acquire an old
client and does not substitute for an exact 41810 request.

## Command-line relay and remaining boundary

Function `0x2200` also contains a route for handing command-line bytes to an
existing process through the same mapping. With positive `shared+8`, or `-link`
and positive `shared+4`, it copies at most 512 bytes to `shared+0x3578`, writes
state `6` at `shared+0x20`, and waits for state `7` while the referenced process
remains alive. The inspected relay has no replay-extension filter, so text
containing a replay filename is syntactically forwardable. The recipient's
argument parser, acceptance of that filename, and playback are unverified.
No IPC message was sent to test this route.

The next static investigation is the main-client owner of request state `2`,
response state `3`/result `3`, and command relay states `6`/`7`. It may explain
where missing-build acquisition is handled; this observation does not establish
a download caller or CDN address. No global claim about downloading elsewhere
follows from the scoped Switcher branch.

No game or Switcher launch, Computer Use, network request, replay edit or sync
data replacement occurred. Full replay upgrade and deterministic playback remain
unproven. Private evidence paths and hashes are retained in the JSON; the public
pair contains no raw PE, raw ASM, player data or unclassified NGDP identifiers.
