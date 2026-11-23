# TEN tracker on MercCapture

The offline assembler writes a private 98348 tracker fragment, its continuous opening, and a ledger mapping each later target frame to an ordinal in the physical 41810 tracker. With the three initial talent awards, MercCapture produces 675 frames in 36,422 bytes. The opening contains 266 frames through the first Greymane award at loop 87. The next uncovered source record is Anub’arak's talent purchase at loop 103. An unresolved game input still occurs at loop 68. Tracker coverage alone cannot establish what the game would simulate beyond that point.

The 235 predicted frames at loop zero replace 213 historical frames. They include the ten player setups, map-dependent startup and the additional team and mastery upgrades. The assembler reconstructs this block from each actual candidate package and compares its complete hash to the separately qualified Quick Match prefix. A build-98348 Quick Match recording with this map and transformed lobby has yet to be verified. Partial frame coverage after startup is 440 of 6,401 source ordinals. [MercCapture receipt](../observations/merc-awards-tracker.json)

| Later events in the fragment | Frames | Evidence used |
| --- | ---: | --- |
| Initial hero births, spawn and level notifications | 30 | Lobby roles, authored starts, ordered unit pool and stock startup callbacks |
| Gates, roster upgrades, first minion upgrades, blocker removals | 75 | Recorded gate clock, historical wave callback and ordered blocker placements |
| Hero revivals | 45 | Recorded deaths and levels, historical timers, lobby starts |
| Camp and Dragon Knight statistics | 17 | Team beacon transfers or Dragon pilot changes, gate clock, roster and map |
| Level notifications after startup | 210 | Recorded team-level times, first and last teammates, complete physical group |
| Opening flag transfers and Dragon resets | 21 | Map-derived generations, gate and activation times |
| Mercenary capture beacons and team flags | 39 | Thirteen recorded captures, fixed map generations and the MercCapture callback |
| Initial talent purchases | 3 | Translated game input, target hero talent columns and physical first-purchase controls |

The physical join independently checks the source and target boundaries, the ordinal order, the target bytes before the first gap and every admitted source payload. For 54 gate blockers the target reports zero for the killer player. The historical file omitted that value. Seventeen objective statistics acquire the target fixed-point GameTime field. Remaining post-start rows share the original tracker payload under the conditions in the table. The sparse stream recomputes event time deltas. Its private prefix and full fragment use the same clocks.

Build the tracker once without optional talents to obtain the startup prefix used by the separate talent verifier. The final pass can consume the independently reproduced three-frame talent stream. Each output directory must be new. Keep both binary streams and the ordinal ledger private.

```sh
python assemble_signed_tracker.py TEN MAP LIBRARY_DIRECTORY historical-hero-timers.json --output first-private
python assemble_signed_tracker.py TEN MAP LIBRARY_DIRECTORY historical-hero-timers.json --initial-talents INITIAL_AWARDS --output final-private > tracker-receipt.json
python verify_signed_tracker.py TEN MAP final-private tracker-receipt.json
```

The SignedAnnouncer parent supports the same assembly without the 39 MercCapture-specific owner transfers. The target XP timing, transient object lifetimes, command execution, full simulation and sync values remain unverified.
