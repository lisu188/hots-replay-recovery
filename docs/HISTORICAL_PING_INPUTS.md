# Unit targets in Dragon Shire pings

The preserved R8 checkpoint carries all 81 original game-event pings unchanged. The 25 explicit unit targets are packed with an 18-bit recycle field. A 22-bit reader interprets every one as a different identity. Two accidentally match unrelated recorded tracker pairs. [R8 and physical-frame audit](../observations/historical-ping-wire.json)

The converter preserves the source event order, game loops, wire user, signed point coordinates, minimap flag and numeric ping option. A zero unit field preserves the absence of an explicit target. Build 98348 can perform a contextual lookup near the supplied point. The build-98348 UI library reads the option, point, unit and minimap flag separately in its player-ping handler (lines 16292–16365). The historical option numbers occur in the target controls. Equivalent in-game UI and visibility behavior remains unverified.

| Target identity evidence | Pings emitted | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Historical map placements and the first recorded lifetime | 59 | 1,156 | `b76ea6aec0b2788e06ee1a4a739a9464f6d1d3ff883cf121ae4f66cf0a61ff2b` |
| Unit generations in the tracker carried by R8 | 81 | 1,586 | `7da30d2ca6ca4444b5c5fb976640697ff3b94872d41dfba7e9a6a039fedf3234` |

The first output includes 56 inputs without an explicit target and three building pings. It reproduced on the two-talent layout and both Greymane cooldown maps. The other 22 inputs reference dynamically created units. The second output matches the corresponding births and lifetime histories in the retained tracker and reverses all 81 inputs exactly. That tracker carries the original simulation. Future target allocations for the 22 dynamic references remain unresolved. Both outputs are separate streams containing only game event 36. [Layout comparison](../observations/historical-ping-layouts.json) · [Retained-tracker comparison](../observations/retained-tracker-pings.json)

Across four original-build recordings and fourteen current-build recordings, only shifts 18 and 22 respectively resolved all nonzero targets against observed births. Three genuine 98348 pings referenced a town hall after its death. A lifetime gate limits the historical-map projection to supported instances. On the modern recordings the native encoder reproduced all 734 game ping frames in their original positions, including frame deltas and alignment, across 13,946 bytes. [Packing observations](../observations/ping-packing-cohorts.json)

~~~text
python convert_historical_pings.py generate --source TEN.StormReplay --original-map ORIGINAL.s2ma --historical-map COOLDOWNS.s2ma --output historical-input.pings.bin
python convert_historical_pings.py retained-tracker TEN.StormReplay R8.StormReplay --output retained-input.pings.bin
python convert_historical_pings.py compare-r8 TEN.StormReplay R8.StormReplay
python convert_historical_pings.py verify-control CONTROL.StormReplay --sha256 DIGEST
python audit_ping_packing.py CONTROL.StormReplay DIGEST 98348
~~~
