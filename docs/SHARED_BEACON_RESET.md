# Dragon Shire shared capture-point trigger

HistoricalCamps first calls `libGame_gf_CapturePointDisable` while initializing camp 1 at captain point 244, coordinates (101, 76). The SharedBeaconReset derivative binds the one-second Dragon Knight behavior when that existing trigger is first allocated. Ordinary calls retain the three-second delay. Two builds produced the same 2,171,327-byte map, SHA-256 `2d5cba9c5fd8276ae62468533fae558222730d55b146d41b7ebb7d30532e70b7`.

## First construction

The map configures five enabled camps and registers its map-mechanic initializer before starting the Storm mod. HeroesLib dispatches game systems before map mechanics. GameLib initializes lanes, watchtowers and towns before jungle camps. The map contains no watchtower placement. The verifier walks the local Galaxy callees of these three prerequisites, all three town-initialization event listeners, and the camp prefix. They contain no explicit wait or nested trigger execution. The camp loop creates a neutral beacon and capture point, saves the returned index, and calls the disable helper before looking up the camp sconce.

The 22-file Galaxy dependency manifest supplies five call sites for the stock disable helper. MapMechanics line 4946 is the camp initialization loop. Line 1681 is reached on a team capture. Lines 3547 and 3580 follow the Sun and Moon beacon births in shrine initialization. Line 7549 follows a Dragon Knight activation. The HistoricalCamps map script contains no additional call. At loop zero, all five build-41810 and all 15 build-98348 Dragon Shire recordings put the five camp beacon births before either shrine beacon. The first recorded camp position agrees across all 20.

## Shared dispatch

The marker variant assumes the worker enters before its caller clears the marker. The original worker already reads a shared index at entry. The harness exercises immediate entry and timed suspension. The exact native dispatch boundary remains unmeasured.

The derivative registers the camp and Dragon Knight callbacks in the original two trigger slots. The camp initializer uses a copy of the original lazy wrapper. Its global capture-point argument, null guard, shared trigger handle, creation site and asynchronous dispatch are identical. The wrapper supplies the name of the map-local worker when it first allocates the handle. Other capture-point clients continue to call the stock wrapper, which reuses that handle.

The Dragon Knight callback sets a one-shot boolean immediately around its existing disable call. The worker first copies the capture-point index, consumes the marker before any guard or native call, and stores the selected delay on its own stack. This preserves the ordinary three-second behavior if another capture-point call occurs while the Dragon worker is suspended or inside its hide signal. Only the map script differs from HistoricalCamps. Both readers agreed on the script and the other 69 content members matched.

The source tracker and all four independent build-41810 replays record Sun then Moon shrine resets at activation, followed by Moon then Sun beacon resets 16 loops later. All 52 build-98348 activations record the same two orders, with 48 loops between them. The four original TEN cycles and all other cases were checked using the birth coordinates and generation of each specific shrine and beacon.

The C harness extracts the actual startup wrapper, ordinary wrapper, worker and scoped call. Seven ordinary startup disables share one trigger. Two Dragon workers suspend on separate stacks at loop 2514. One ordinary request is reentrant during the first worker’s hide signal. A second ordinary request follows the two Dragon dispatches. Both Dragon owners persist through +15, then change at +16 in Moon–Sun order. Both ordinary owners persist through +47 and change at +48. Disabled and out-of-range requests produce zero writes. All 13 dispatches use the same single trigger. The harness schedules equal-deadline workers in the order observed in the recordings. Native Galaxy compilation, scheduling against the camp timers, and full replay playback remain unverified.

## Reproduction

Run `verify_first_capture_disable.py` with the HistoricalCamps parent, target script directory and member manifest, historical shrine observations, and the two private replay path dictionaries. Supply its JSON result and the historical observations to `build_shared_beacon_reset.py` and `verify_shared_beacon_reset.py` with the parent and the target GameLib and MapMechanicsLib. The verifier also requires the adjacent `shared_beacon_harness.c`, StormLib and a C compiler with POSIX user-context support. The command-line tools accept `--help`.
