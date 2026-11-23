# TEN game inputs on SignedAnnouncer

Supply the ordinary assembler inputs, including the positional GateOrder witness, and add `--signed-announcer-map SIGNED_MAP`. The full run also enables `--nova-xml` and `--soundtrack-evidence`. The optional switch checks both physical packages before projection. The default CLI and three-value Python return interface are preserved.

For target `150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791`, the two independent writers and the join against original TEN ordinals verified 21,585 inputs in 194,652 bytes. The stream and ledger matched the all-stage GateOrder reference byte for byte. The first omitted event is sound offset event 46 at loop 68, ordinal 33. This output is a sparse projection, with 82,672 source inputs still omitted.

| Producer | Inputs checked on the chosen target | Conditions for applying the result |
| --- | --- | --- |
| Camera and implicit point commands | MapInfo bounds, authored starts, terrain dimensions and synchronous heightmap | Original camera and command inputs, command flags |
| Selections, unit clicks and unit-target commands | MapInfo, Objects and Regions, opening script setup and pinned MapMechanics; 165 authored and seven scripted modeled births agree in order and payload. Embedded unit data matches | Hero starts also use the TEN lobby. Later selections/clicks depend on lifetimes, ownership, first vehicle activation or trajectory at the original tick |
| Pings | Authored placements for map pings and the original opening heroes for hero pings | Original lifetimes and hero respawn schedule |
| Talent inputs, Symbiote and point casts | Embedded catalogs and dependency declarations match. These producers use separate records or build-specific ability/catalog evidence | Award/selection state, command flags and source births |
| Intro soundtrack | Both map scripts independently resolve to `MX_Dragonshire_Intro`. Embedded sound data and dependency declarations match | Existing calibration assumes the stock catalog and recorded soundtrack schedule |
| Opening prefix, point sessions/intervals, chat and departures | These routines do not open the target package. The verified prefix includes earlier opening selection/command predictions | Their source/control and preceding-input conditions continue to apply |

The comparer reads all 70 content members and accounts for all live blocks. Only MapScript.galaxy differs. The target adds the Lady of Thorns default, changes camp scheduling and changes Dragon beacon resets. These can affect recipients, sound handles, unit lifetimes and later world state. This check does not predict target callbacks or reproduce the match. It retains the sparse candidate payloads and records their conditions in the receipt.

Run the following after assembling, with the ordinary repository modules and protocol dependencies on PYTHONPATH. The optional final argument requires the pinned prior private output from the all-stage GateOrder route.

```sh
python verify_signed_game_inputs.py TEN GATEORDER SIGNED_MAP MAPMECHANICS SIGNED_DIRECTORY SIGNED_RECEIPT --all-stage-gateorder-reference GATEORDER_DIRECTORY
```

The public receipt contains hashes, counts, producer dependencies and conditions. The ordinal ledger, game payloads, recordings, map packages and local paths stay private.
