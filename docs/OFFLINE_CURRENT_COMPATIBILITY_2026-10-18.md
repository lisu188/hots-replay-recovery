# Offline compatibility with genuine build 98348 replays

Eight public Nexus Gaming Series Dragon Shire replays now provide actual
current-build controls. All eight report executable/base/data build 98348,
root `c3b3c8bc82e3a5a62e550fdde9a40c28`, map checksum `886294905`, and mod checksum
`13528913`. The combined replay download size is 9,634,155 bytes. Public source
URLs, complete SHA-256 values, event counts and provenance are retained in
`observations/offline-eight-current-references-2026-10-18.json`. Raw public
replays and player/chat contents are excluded from publication.

The current controls were discovered through the public NGS reported-match
endpoint using season 22. Its primary implementation and bucket configuration
are pinned to commit `4c4ad4d5a1d0a5d27bec8c2a4dd839ee6cefbc8d`:

- https://github.com/nexusgamingseries/ngs-mean-core/blob/4c4ad4d5a1d0a5d27bec8c2a4dd839ee6cefbc8d/client/src/app/services/schedule.service.ts
- https://github.com/nexusgamingseries/ngs-mean-core/blob/4c4ad4d5a1d0a5d27bec8c2a4dd839ee6cefbc8d/client/src/environments/environment.prod.ts

This supersedes the earlier absence of a downloadable current reference.
The separate Heroes Profile acquisition attempts still returned HTTP 403;
those were download failures rather than schema-compatibility results.

## Actual offline checks

Every current replay passed full observed header, details, initData and
game/message/tracker decoding and exact re-encoding using Blizzard's pinned
official schema 96477. The upstream commit is
`9af3ea7150f1a8acb53464c92519a9bbcc7a3594`; the canonical LF schema SHA-256 is
`e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84`.
No official 98348 schema was found in that pinned upstream. These checks
establish compatibility of the observed payloads with 96477, not coverage of
every event that build 98348 could produce.

For R8 and the two initial October 16 controls, a separate `mpyq` reader
extracted the same bytes for all 14 listed/metadata members as the project
reader. All three resumable streams also round-tripped with the modern layout.
This does not perform complete native StormLib checksum verification.

The unchanged independent `Heroes.StormReplayParser` 2.3.0 and `Heroes.MpqTool`
1.4.0 packages were verified against NuGet SHA-512 metadata. They ran using the
existing PowerShell/.NET 10 runtime without installing an SDK or launching HotS:

| Input | Full public parser | Isolated core reader counts: game / tracker / message |
|---|---|---|
| NGS Protectors, 98348 | Exception in pregame-to-replay mapping | 154012 / 7155 / 135 |
| NGS Stormblessed, 98348 | Success | 211947 / 9519 / 203 |
| TEN_GREYMANE R8, 98285 | Exception in battlelobby attribute definitions | 104257 / 6614 / 155 |

The isolated readers explicitly exclude battlelobby parsing/mapping. Their
counts and header/base-build values agree with Python, but they do not turn
the two public parser failures into success. Full event-payload equality
between the independent implementations has not been compared.

`scripts/read_independent_replay.ps1` reproduces these checks with explicit
input replay paths, a flat directory containing the two pinned net10.0 DLLs,
and a new output path. Optional Python profile paths must be supplied in the
same order. The script downloads nothing, verifies exact DLL bytes before
loading, and emits sanitized results. It requires a fresh PowerShell process
on .NET 10 or newer. Exit success means a report was written; inspect each
`public_api.status` for actual parser acceptance.

```powershell
./scripts/read_independent_replay.ps1 `
    -Replay ./work/first.StormReplay,./work/second.StormReplay `
    -AssemblyDirectory ./work/independent-dlls `
    -Output ./work/new-independent-read.json
```

The packages and exact assembly hashes are recorded in
`scripts/independent-parser-packages.json`. Actual results and seven completed
portability/input-preservation checks are separate observations.

## Concrete remaining differences

R8's ordered dependency paths, map title/dimensions and map checksum agree with
both first controls. R8 still declares build/data 98285, an older root key, and
mod checksum `2276260760`. Both initial controls and all six additional ones
declare mod checksum `13528913`. Copying that value would not port historical
simulation rules, so no checksum was transplanted.

The unchanged independent parser exposed a structural issue that the earlier
prefix-only battlelobby audit did not cover. R8 retains the original's narrower
attribute value-count and index fields. A source-preserving width conversion
is under investigation separately; this checkpoint does not contain a newly
repacked replay or claim that the entire battlelobby member is compatible.
The pinned modern implementation is:
https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs

The eight real controls support **33 unambiguous observed unit-name/index
pairs**, leaving **17 unresolved types**. Fourteen were not observed and three
are blocked by persistent aliases. Greymane now has direct evidence for
`807 -> 614`; Anubarak, Sonya/Barbarian, a beetle and several structures also
gain observed pairs. All per-file provenance is retained in
`observations/ngs-eight-reference-catalog-comparison-2026-10-18.json`.

Source link 531 belongs to both `TownCannonTowerDead` and `TownCannonTowerL2`;
current link 296 belongs to both `TownCannonTowerDead` and `TownCannonTowerL3`.
Those cannot be migrated by a global numeric replacement. No proposed pair
has been applied to a replay. Original/R8 catalog inventories remain equal
after accounting for their respective packed-tag layouts, and the original
synchronization payload remains byte-identical in R8.

## Native attempt and current testing constraint

Before the user's request to continue offline, the unchanged J2 diagnostic
map was launched once. Fresh Graphics log lines establish executable/data
build 98348 and the exact map argument. The game subsequently ended while
loading, as confirmed by the user; no journal export was observed. Bounded
event/log/diagnostic searches did not establish an exception code, exit code,
faulting module or Galaxy compilation outcome. Relevant sanitized evidence
is preserved in `observations/native-j2-launch-log-2026-10-18.json` and
`observations/native-j2-terminal-2026-10-18.json`. No raw personal logs or dumps
are published.

The current instruction is to test without running the client. No client was
launched for this offline cohort or independent-reader work. The latest replay
remains R8; the last explicit replay playback result remains R5's displayed
0:04 Replay Desync. A full upgrade still requires the remaining structural
layers, catalogs, 54 old ability links, unit-instance allocation, historical
rules and synchronization to be reconciled. No new full-match compatibility
or native playback claim is made.


## Later bounded expansion and historical mod audit

The remaining five keys from the saved Dragon Shire listing were downloaded.
Four are actual 98348 controls; one dated October 5 is build 98304 and was
excluded. The current cohort now contains 12 recordings and still supports
33 pairs with 17 unresolved types. See the expanded-current observations.
The historical mod-layer diagnosis is in `LEGACY_MOD_METADATA_2026-10-18.md`.
Attribute-layer CI 39152968629 passed both platforms at f928ec7; this result
predates the separately added mod audit. Full replay recovery remains open.
