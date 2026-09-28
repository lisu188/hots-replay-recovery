# Client 98285 experiment — 2026-09-28

## Result

The user reported that a replay from the latest installed client had appeared on OneDrive. The new Braxis Holdout replay, saved at 21:40:35 Europe/Warsaw, declares **2.57.0.98285**, base/data build **98285**. This supersedes the previously observed installation 2.55.17.98025. The donor has 980725 bytes and SHA-256 `05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75`.

A separate **TEN_GREYMANE_client98285_EXPERIMENTAL.StormReplay** has been generated and uploaded to both the existing OneDrive project folder and the user's normal Replays/Multiplayer folder. No original or donor was overwritten. After desktop synchronization the new candidate can be tested in HotS.

Candidate: **670388 bytes**, SHA-256 `2ecb09f353a30363ad59d04b04d439bb7f0ee623d832000d8d13f7a05dbb0486`.

**Actual HotS playback and deterministic simulation have NOT been tested.** The highest exact official protocol checkpoint remains **96477**; **98285 is a client-metadata candidate, not a newly established complete protocol schema**.

## Actual reference evidence

The donor and generated candidate both passed full header, details, lobby and all-event decoding using the unmodified official Blizzard 96477 schema and decoder. Each observed payload was encoded back byte-for-byte. The official files were checked against their Git blob hashes before execution. See `client-checkpoints/98285/report.json` for exact runtime hashes.

- Donor: 121743 game events, 241 messages, 5979 tracker events.
- Candidate: all 104257 game events, 155 messages and 6614 tracker events from TEN_GREYMANE were retained.
- All 20 candidate game-event types, 3 message types and 10 tracker types also occur in the donor. This is event-type coverage, not proof of all field variants or simulation rules.
- Dragon Shire, the original map, remains unchanged. The donor's Braxis Holdout map was not transplanted.
- Compared with checkpoint 96477, there are 24 semantic metadata changes. Only 40 bytes of the 1148436-byte uncompressed game-event stream changed, corresponding to build/base-build fields in ten player-option events. The remaining changes are in the replay header and regenerated archive integrity metadata.
- Independent mpyq reading matched all 14 archive members. MPQ v4 bounds, table/header hashes and unchanged member comparisons passed.

The donor contains a **16-byte all-zero replay compatibility hash**. The validator incorrectly required this hash to be nonzero. It now accepts the observed value while still requiring a nonzero, correctly sized root key. Separate regression tests cover zero hashes, zero root keys, wrong identifier lengths and invalid types. No hash was fabricated.

The donor header is not an authenticity signature. Its provenance is the user's newly supplied replay. The exact `protocol98285.py` was not available in the inspected Blizzard repository. Successful 96477 decoding of these observed payloads does not establish the entire 98285 schema.

## Tests and publication

`PYTHONPATH=work/offline:. python -m unittest -v test_reference test_client_binding test_reproduce_client`: **36 passed, zero failed, zero skipped**.

Those unit/integration tests use previously committed local schemas for old fixtures. The real 98285 donor and candidate were separately inspected with freshly obtained, hash-verified official 96477 source files. Native StormLib was not executed locally for this candidate.

The generated replay also reproduced exactly from a small Base64 member-patch recipe and reconstructed exactly from its 12 full Base64 parts. The recipe and `reproduce_client_candidate.py` are already on GitHub; the raw private donor is not published. Full candidate Base64 parts are in the local/OneDrive backup. `.github/workflows/client-candidate.yml` additionally reconstructs the candidate, requires native StormLib, and publishes full Base64 parts only after successful verification. At initial inspection run **36478033637** was **queued**, not passed.

Reproduce without the private donor:

```bash
python reproduce_client_candidate.py client-checkpoints/98285/recipe.json --output work/client-98285-reproduced
```

The exact expected output checksum is required. Reproduction refuses overwritten output directories and modified, overlapping, out-of-bounds or invalid Base64 patches. A different compression runtime that produces different bytes fails checksum validation rather than silently publishing a different replay.

## Next client test

Open `TEN_GREYMANE_client98285_EXPERIMENTAL.StormReplay` in the installed HotS client after OneDrive synchronization. Record whether it appears in the list, loads the map, starts the match and reaches its ending. Preserve the exact error or screenshot and new game logs on failure.

Do not set `client_playback_validated` to true merely because the replay loads or the parser accepts it. The complete match, original outcome and meaningful timeline must be compared before claiming faithful recovery. Old map dependencies, ability/unit catalogs, talents and synchronization data remain possible incompatibilities.

The Windows reference collector is no longer needed for this checkpoint: the real donor has been acquired and validated. Continue with client observations and catalog/simulation investigation, not another blind build-number increase.

## Recovery storage

Keep earlier bundles and checkpoints. The container workspace started from the local recovery bundle at `011d8ecf5190b3429133e02be5d786cb7cfa1578`, not the latest remote main history. A new local workspace bundle must be labeled accordingly and must never replace or force-push GitHub main. The new CI workflow is configured to produce a complete remote-history bundle if its run succeeds.
