# Native control and publication recovery, 2026-11-15

The user's explicit authorization permits Battle.net/HotS Computer Use, the
unchanged98348 control, diagnostics and continued TEN_GREYMANE conversion.
Older no-game instructions are superseded. Authentication remains manual.

## Current native observation

The control remains 978482 bytes, SHA256
`a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4`.
The installed Base98348 executable remains 53573840 bytes, SHA256
`efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`.
The fresh preflight found 359551361024 free bytes and 64.03% disk utilization.

Computer Use found the Battle.net window and obtained accessibility text showing
Europe, version2.57.0.98348 and the Play button. Its screenshot showed the desktop,
so it supplies no game frame or visible replay proof. The Play action failed with
`failed to activate captured window`; fresh window selection and one activation
recovery returned the same error. No HotS process or replay launch was observed.
The user was asked to restore the Battle.net window; no readiness reply has yet
been observed. Do not bypass a tool access/permission denial. A routine activation
failure may be investigated through another authorized UI surface using fresh
observations; the separate Explorer attempt is recorded in the later frontier.

Exact comparison with the saved November2 local HotS metadata found no changed
entries:33 local GameLogs,0 local UserLogs,1785 cloud stubs skipped,0 body bytes
read. A bounded475-entry export-name search found no dedicated HRC/J2 export.
These are scoped findings, not an exhaustive absence claim or a playback failure.
Private metadata, accounts and desktop captures are not published.

## Fresh online target

The [official EU](https://eu.patch.battle.net/hero/versions) and
[US](https://us.patch.battle.net/hero/versions) manifests still advertise
2.57.0.98348 with BuildConfig `a64c9b7ebf1c6a811ffefad97865ed80`.
Their874-byte bodies have SHA256
`9d9a857134fb0cc2fc0eb1b53985a654b2475681f4616c595c3fe7649081a490`.
The CDNConfig is now `5146a61f539c29687d886efcc8de1e2d`, different from the
November2 snapshot. One bounded request acquired that newly advertised config:
7897 bytes, MD5 equal to its key, SHA256
`7e659d39537fb2661afe6510c0a048f8e5c0a1a6290cc48e18b206c2093ba0ea`.
No archive/index fanout or historical-config request was made. This is current
delivery metadata; it establishes neither a new client build nor41810 rules.

## R5 publication regression

Remote main advanced from9adb728 to2576bac through13 commits and40 changed paths.
All260 non-CI checkpoint Git objects are unchanged. The five checkpoint CI
receipts change only run/tested-commit metadata. No converted replay or new
conversion semantics were introduced.

Repeated `dragon-dependencies.yml` runs nevertheless replaced the R5 progress
object and selected R5 as latest. They deleted its known map-visible/desync status,
tested flag,0:04/20:33 clock and observation reference. The immutable observation
`observations/r5-desync-2026-09-29.json` remains unchanged. The R5 artifact is still
1255308 bytes, SHA256
`f5eac2c4de55db9cc834c97825ac89d5fc0bb4807a2b216ba5ca7fbc63e45f11`.

`progress.json` restores those facts from9adb728 after checking identical build,
name, size and digest, while retaining the newer R5 CI run43387752059. R8 is again
the latest partial candidate; the immediate experiment is the unchanged98348
control. The publisher guard preserves existing same-artifact native/user state
and active next-step selection while refreshing CI verification. A different
artifact identity must be refused before publication changes any file.

The publication helper also reconstructs and hashes all23 ASCII Base64 parts in
RAM for both generated and retained/prospective artifacts. Sixteen CLI integration
tests passed locally and in independent review, including the exact workflow
command, real checked-in R5 compatibility, preservation of native/unknown fields
and R8 selection, idempotent reruns, and byte-identical refusal on corrupt input.
The workflow refuses publication code changed by its pre-publication rebase.
These tests do not launch HotS or supply new converted replay bytes.

## Validation boundary

All17 jobs in the three historical9adb728 runs are now terminal. The complete
offline run41506969221 passed1107 cases on each lane:38 Linux skips and4 on each
Windows lane. Static run41506969764 is green overall but its advanced CodeQL
Python upload failed because default setup was enabled; continue-on-error masks
that job failure. Separate default CodeQL run41506967394 completed Actions and
Python successfully. These results belong to9adb728 and do not prove current-head
tests, clean security findings, native playback or historical equivalence.

The full original41810 match is still not converted and verified on98348. R8
still declares98285. The next runtime evidence remains an observed unchanged
control, followed by same-session diagnostics and the preserved J2 investigation.
