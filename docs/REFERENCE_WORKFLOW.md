# Reference-driven client binding

Date: 2026-09-28. The highest independently validated protocol checkpoint remains **96477**. No authenticated modern reference or real-client playback result has been obtained in this continuation.

## Implemented and pushed

- `protocol_loader.py` loads an exact Blizzard schema file through importlib without executing the legacy `versions/__init__.py` that imports removed `imp`. It never silently substitutes a different build.
- `reference_replay.py` checks replay/container bounds, decodes the header, lobby, details and every event, compares decoder outputs and requires byte-for-byte re-encoding. The resulting profile contains build identifiers and coverage, not player names, chat messages or local paths.
- `bind_client_metadata.py` revalidates the actual reference bytes, then creates a separate explicitly experimental artifact. Only the version/data identifiers and ten player-version option records are copied. Source gameplay commands, match duration and other archive members are preserved. All changes are recorded in JSONL.
- `scripts/fetch_public_reference.py` attempts a bounded discovery window using documented Heroes Profile OpenAPI endpoints. At most three public donor files are downloaded; unexpected download hosts/redirects are rejected. Access errors, missing data and incompatible replays are recorded, not treated as success.
- `scripts/collect_reference.ps1` collects a compatible reference from the user's Windows replay folders without uploading it or modifying the game installation.
- `.github/workflows/reference.yml` tests with Python 3.13, uses pinned official schemas, attempts public discovery, and publishes only verified text evidence and explicitly experimental candidates. Binary donor files remain CI artifacts rather than Git source files.
- `.gitignore` excludes private work files, raw replays, parser checkouts, virtual environments, bundles and ZIPs.

## Validation actually completed locally

`python -m unittest -v test_reference test_client_binding`: **21 tests passed, zero failures and zero skips**, Python 3.13.5.

The run includes a full binary round-trip of the original 41810 replay: 104257 game events, 155 messages and 6614 tracker events. It also performs a complete metadata binding and MPQ/Base64 reconstruction using the existing 44256 checkpoint and a **synthetic test-only donor**. The synthetic build label 44257 is not a real-client achievement and its temporary binary is not published as a recovered replay.

Independent MPQ comparison used the unmodified `eagleflo/mpyq` source fetched through the connected GitHub reader:

- Git blob: `53f75887a2fb476cbb7f7011baebb756399c4824`
- SHA-256: `e10fa2f422d837345f438934a99a3cdf67fa9148c7106d421408e1ecfa83e239`

Its local bytes were checked against the returned Git blob hash before execution. Local replay schemas are the previously committed 41810/44256 schemas, previously compared against Blizzard in the earlier successful checkpoint CI. **This continuation's local run did not independently execute a freshly checked-out official Blizzard decoder or native StormLib.** Those checks remain in the new CI workflow and must be reported from a completed run.

The integration test initially rejected a 17-byte synthetic hash; the fixture was corrected to the required 16 bytes. No production validation was weakened. Local-provider validation is explicitly distinguished from official-provider evidence in reports.

## Reference search limits

The user's game log already established an observed installation of 2.55.17.98025 on 2026-09-19. That is not proof of the current global latest build or of a valid new replay schema.

OneDrive metadata reports 2079 files in the main Multiplayer replay folder. The available listing action returns a maximum single batch of 200 items without pagination. No modern reference was found in the inspected batch and targeted searches; this is not a complete negative inventory. The desktop `stormreplay` folder contained the original 2016 TEN_GREYMANE replay, not a modern donor.

No actual 98025-or-later reference bytes have passed inspection here. Public discovery from CI must not be claimed executed while the workflow is queued. At the last check, run 36471852198 was queued and the newer run 36472684124 was pending behind it.

## Collect a reference on Windows

From this repository's directory:

```powershell
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_reference.ps1
```

Requirements: Git and Python 3.11 or newer. The script creates an isolated environment under `work/`, installs pinned `six` and `mpyq`, and fetches the pinned Blizzard parser commit if `_upstream` is absent. An existing modified or different upstream checkout is rejected rather than overwritten.

It reads the standard Documents and OneDrive replay locations, searches at most 5000 replay files per root, reports truncation, excludes obvious PTR/previous experimental candidates, and inspects up to five candidates. An alternate location can be supplied with `-ReplayRoot`.

The output is `work/reference-input-<timestamp>.zip` containing one reference replay and its minimal metadata profile. Private scan paths are not included in the ZIP. **Nothing is uploaded automatically.** A replay may contain player names and chat even though its metadata profile omits them. This PowerShell wrapper has been statically reviewed but not executed on Windows in this session.

If no recent replay exists, save a short match replay in the installed live client and run the collector again.

## What reference metadata can and cannot do

A compatible donor can supply real observed values for `m_version`, `m_dataBuildNum`, `m_ngdpRootKey`, `m_replayCompatibilityHash` and player-version options. A successful observed payload round-trip covers only the fields/event types in that donor. Its header is self-declared data, not an authenticity signature.

Copying those identifiers does not port old ability/unit catalogs, map dependencies, hero rules, talents, opaque synchronization records or deterministic simulation. Output remains `EXPERIMENTAL` with `client_playback_validated: false` until a real HotS client is tested. Neither changing a build label nor manufacturing hashes is completion.

## Primary references

- Pinned Blizzard parser: https://github.com/Blizzard/heroprotocol/tree/9af3ea7150f1a8acb53464c92519a9bbcc7a3594
- Heroes Profile Max endpoint: https://api.heroesprofile.com/docs/1.0/Replay/Max
- Heroes Profile replay-list endpoint: https://api.heroesprofile.com/docs/1.0/Replay/Min_id
- Independent MPQ reader: https://github.com/eagleflo/mpyq/blob/master/mpyq.py
