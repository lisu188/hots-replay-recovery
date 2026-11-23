# Dragon Knight beacon reset using the existing capture index

SignedBeaconReset restores the observed one-second Dragon Knight beacon reset on HistoricalCamps. It uses GameLib's existing capture-point trigger, argument global and index-transfer convention. Two independently built archives matched at **2,171,315 bytes**, SHA-256 `786f04a19c4222d5e81faefd7363c5422c16b49216732c28a773c74d853e10a9`.

## Dispatch and index domain

Camp 1 binds the shared worker when its neutral beacon is created. The call uses the original wrapper’s null guard, trigger global and allocation position. The first-call check reads the enclosing Galaxy dependencies and all 20 physical Dragon Shire recordings. The five historical replays and 15 current controls place all five camp beacons before either shrine beacon. [Shared-trigger evidence](SHARED_BEACON_RESET.md)

The map’s five ordinary disable call sites supply one of two integer fields from the camp and tower records. The only three assignments to those fields take the last-created capture-point index. GameLib increments its counter once on successful creation, stops at 15, and stores that value in the last-created slot. Valid created indices range from 1 through 15. The ordinary argument global appears three times in the stock closure, in its declaration, the wrapper’s assignment, and the worker’s local copy.

The Dragon Knight channel-finish callback sends the negative of its existing beacon index. The argument global carries this signed value during the stock wrapper’s null check and its call to `TriggerExecute`. At worker entry, the worker copies the argument to its own stack, converts it to its positive value, restores the argument global and selects the one-second game-time delay. The conversion precedes the bounds and enabled checks, actor signal and suspension. All ordinary clients send their existing nonnegative values and receive the three-second default. The variant adds zero Galaxy globals and zero runtime trigger allocations relative to the parent’s stock capture-point route.

## Checks

The verifier reads the candidate back from the MPQ and compiles its emitted wrappers, worker and Dragon call with an instrumented C harness. It checks the restored positive index against the exact beacon at the first actor call, the preserved value after a reentrant ordinary call, and restoration on the out-of-range early return. Two Dragon workers suspend on independent stacks. Both own the correct beacons until +15, then write Moon followed by Sun at +16 under the observed wake order. The reentrant ordinary request and a separate ordinary request both write at +48. All 13 dispatches use one shared handle.

All 15 historical activations and 52 current activations supplied the corresponding reset intervals and order. The original HistoricalCamps map has SHA-256 `5c241e8f9f316909ea237e5dd9f1c4d4ec2e7ea3224d383c596588c7eaf1b9ae`. Its 69 content members other than the map script remain byte-identical. The signed script has SHA-256 `5ec2366f97c21b21d00233aa3c078b42f266ef5cce2e9ff5561ccacaca8fcd29`. The POSIX harness supplies same-deadline wake order from the recordings. Native compilation, whole-game synchronization and replay playback remain unverified.

## Reproduction

The builder reads HistoricalCamps as its archive parent and the exact SharedBeaconReset map as its script reference. It also requires the private target script directory with its `member.json` manifest, the public full historical shrine observations, the first-capture-disable receipt and the shared C harness. Invoke the following with the recovery modules on the Python path and a C compiler with POSIX user-context support.

```text
python signed_beacon_reset.py HISTORICAL_CAMPS_MAP SHARED_BEACON_MAP SCRIPT_DIR historical-shrine-start.json first-capture-disable.json shared_beacon_harness.c NEW_OUTPUT_MAP --stormlib LOCAL_STORMLIB --cc cc
```

Both archive inputs are immutable references. Rebuilding to two fresh paths and comparing the whole output files checks reproducibility. The command emits checks and whole-file digests as JSON. The map archive, extracted libraries and input path dictionaries stay in private storage.
