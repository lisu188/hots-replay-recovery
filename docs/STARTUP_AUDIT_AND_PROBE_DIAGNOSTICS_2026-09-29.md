# R8 startup audit and probe failure diagnostics

Date: 2026-09-29.

## Current result

This continuation did not create R9 or modify any replay. The latest replay remains `TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay`, SHA-256 `4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19`. Its in-game playback has not been confirmed. The last explicit user outcome remains R5 rendering Dragon Shire and stopping at displayed `0:04 / 20:33` with `Replay Desync!`.

Fresh OneDrive evidence records an actual diagnostic-map launch at local time `2026-09-29 15:46:00.559`: executable and data build 98285, version 2.57.0.98285, the `TEN_GREYMANE_CATALOG_PROBE_98285.StormMap` argument, HeroesSwitcher parent and PowerShell grandparent. This establishes the process launch, not successful Galaxy compilation, map initialization or bank export. Fresh Variables.txt modified at `13:47:01Z` records the R7 replay basename; it does not establish that R7 played successfully or reveal an R8 result. Public observations omit private paths, account fields and full logs.

The scoped searches found no catalog-output ZIP or HRC98285 bank. They are not a complete enumeration of all local/OneDrive files and do not establish the cause of a missing export.

## Read-only first-interval audit

`audit_startup_interval.py` checks the immutable original and R8 digests, decodes and re-encodes every game/message/tracker event, compares its semantic decoder with pinned Blizzard decoders, and inspects the diagnostic interval `0 <= gameloop < 64`. No input replay is written.

The interval contains 29 game events, four selection catalog fields and two point-target commands:

| Loop | Recorded tracker type | R8 catalog link | Independently observed current reference link | Recorded instance index |
|---:|---|---:|---:|---:|
| 52 | HeroGreymane | 807 | unresolved | 173 |
| 59 | HeroFaerieDragon | 64 | unresolved | 172 |
| 60 | HeroAnubarak | 739 | 468 | 175 |
| 60 | HeroKaelthas | 827 | 632 | 174 |

The type/instance association uses a strictly preceding live tracker lifetime, not a future or same-tick identity. It still describes the recorded tracker, not actual object allocation in the new engine. The reference anchors span genuine modern recordings; cross-map catalog-context equivalence is not established, so no automatic replacement is applied.

At loops 61 and 63, the two commands have `m_abil=None`, `TargetPoint`, and flags 524552. There are no explicit numeric-ability commands in this interval. This does not exclude ability definitions or behavior from affecting the initial simulation state.

The original and R8 synchronization payloads are byte-identical: 1540 bytes, 308 observed five-byte records, SHA-256 `62a68b50c8cf0c94da98403dad8cda0f92e02580ec9590b2b32815ee32f8d8ae`. Their count equals `19732 // 64`. The framing/count pattern is an observation, not a measured first failing tick or an identified checksum algorithm. No synchronization check, record or checksum was removed or disabled.

Full report SHA-256: `8a8dd65bc4aab21786eae67848882b096f25e1f708f98b64432adf48130fd171`. A compact public summary is `observations/startup-interval-r8-2026-09-29.json`.

## Diagnostic collection when export fails

The existing launch/capture script throws when it cannot find a probe manifest before writing its normal capture ZIP. That can leave a failed map attempt without a diagnostic package. The cause of this user's missing export remains unknown.

New independent entry point: `scripts/COLLECT_CATALOG_DIAGNOSTICS.cmd`, invoking `scripts/collect_catalog_diagnostics.ps1`.

It does not launch or stop HotS, modify the installation, write a replay, or change the existing diagnostic map. It writes a new `catalog-diagnostics-*.zip` even if no bank manifest exists. It collects only the dedicated HRC98285 diagnostic bank files and bounded selected error/version lines from HotS GameLogs/UserLogs. It retains only the last replay basename from Variables.txt. It masks email addresses and absolute Windows paths in selected lines and omits credential-like lines. Output remains private diagnostic material, not an automatically public artifact.

Limits cover traversal depth, entry count, bank/log count, individual/total bytes and selected line lengths. Existing outputs are not overwritten. Different bank directories remain distinct. A present manifest is explicitly unvalidated; this diagnostic format cannot be treated as an eligible runtime catalog mapping capture.

A review found that treating every Windows reparse point as a link would also skip Cloud Files placeholders. The delivered collector uses read-only FindFirstFileW metadata to recognize the 16 IO_REPARSE_TAG_CLOUD variants and continues to reject junctions, symlinks and unknown tags. The actual Windows junction path and tag classification were tested. No real OneDrive Cloud Files provider was exercised in CI, and this change is not asserted as the user's failure cause.

Microsoft sources for the tag policy:
- https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-tags
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/c8e77b37-3909-4fe6-a4ea-2b9d423b1ee4

## Validation performed

The first-interval suite passed 55 tests locally and in Linux CI: 26 new interval tests and 29 existing catalog/lifetime tests. CI run `36599057470`, tested commit `d5602e9385fb60ff984cc5e1d57335ba229b99d7`, additionally decoded all streams using pinned Blizzard schemas, compared eight payloads across the original and R8 with independent mpyq, and generated the identical audit twice. A local full-stream audit matched that report. An initial local full-stream invocation lacked the official 41810 module; it was rerun successfully after recovering the hash-checked upstream files from CI.

Collector CI run `36600519761`, tested commit `39ed4329996bcfc6d8eda1d7346b31f67714055d`, passed the same 23 distinct tests separately on Windows PowerShell 5.1.26100.33438 and PowerShell 7.6.6. The tests actually executed the collector against synthetic local directories, including zero banks, partial exports, script errors, sensitive lines, size limits, existing output preservation and a real junction. They did not run the game or collect this user's live files. The earlier 21-test collector version also passed; the two extra tests cover Cloud Files tag classification and native junction rejection.

All three downloaded CI archives matched GitHub's reported SHA-256 digests. The downloaded source files matched the reviewed local code after normalizing Windows line endings. There are 49 new distinct tests in this continuation, not 49 tests of game playback. No native StormLib generation was needed for these read-only tasks.

## Delivery and persistence

Small user package: `hots-probe-failure-collector-2026-09-29.zip`, 6731 bytes, SHA-256 `d400827c44771637b6dd0789ff9d35ef2183a0b1c4b23039ae6091cb8f0e96f9`.

The source bundle recovered from the final collector CI preserves complete Git history through `39ed4329996bcfc6d8eda1d7346b31f67714055d`, SHA-256 `6b11ab1661efe9f85d6ca17952ca70c646cfc57048ba1af0c3dca9c1892fcb4a`. Later delivery notes and progress supplements are included separately in the dated backup. Existing replays, probe maps and donor files are left intact.

## Next observation

Extract the small collector package into a new folder in the OneDrive project and run `COLLECT_CATALOG_DIAGNOSTICS.cmd` after ending the earlier HotS attempt. Leave the resulting `catalog-diagnostics-*.zip` to synchronize. No map relaunch is required merely to collect existing diagnostics. Read that package before assigning any failure cause or inventing another numeric catalog mapping. The game can still produce no explanatory log; in that case retain the exact on-screen map/Galaxy error rather than treating the absence of output as a successful capture.
