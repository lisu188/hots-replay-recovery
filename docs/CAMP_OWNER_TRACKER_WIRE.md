# Dragon Shire camp beacon tracker records

`camp_owner_wire.py generate` writes a separate, versioned tracker stream for the 13 recorded TEN_GREYMANE camp captures. The historical-layout output contains 13 transfers and 13 neutral resets, totals 558 bytes, and has SHA-256 `b1e10df5fb6534fa52d5a5eae7adb5d85984ce3d6894b4ce256311cd991ed3b0`. It is a partial input for replay recovery. It lacks every other tracker event, the other replay members and the enclosing archive.

The generator consumes the recorded `JungleCampCapture` loop, `CampID`, fixed-point `TeamID` and replay header horizon. It derives each beacon tag from map objects, regions and startup script through `dragon_startup_births.predict` with the pinned MapMechanics library. Each transfer occurs one loop before its capture stat and sets both controller and upkeep to player 11 or 12. The recorded timing profile places each neutral reset 16 loops after the historical stat, or 48 on the stock 98348 layout. Both reset fields become zero. Historic and stock map profiles have different startup indices. An unmodified release map and its corresponding two-talent package produce identical sparse bytes for each layout. The stock-layout counterfactual retains TEN's recorded captures.

The writer uses the named Blizzard 96477 tracker schema verified against physical build 98348. Event ID 3 selects `NNet.Replay.Tracker.SUnitOwnerChangeEvent`. The official decoder checks all four fields, event IDs, loop numbers and full bit consumption. The standalone stream measures loop deltas from zero and then from its preceding emitted record. Two projected beacon transitions on the same loop cause generation to fail because their relative order is unknown.

## Recorded checks

| Physical recording cohort | Captures | Matching physical frames | Frames sharing a loop with other events | Whole tracker members byte-equal after substitution |
|---|---:|---:|---:|---:|
| TEN and three other 41810 recordings | 39 | 78/78 | 13 | 4/4 |
| Fourteen genuine 98348 recordings | 246 | 492/492 | 112 | 14/14 |

Each verification first freezes the projected stream. It then locates the physical beacon records in the original tracker and generates their full target frames using the immediately preceding physical event loop. It compares the bytes at the recorded decoder offsets and checks byte equality of the entire tracker after substituting only those event dictionaries. Mixed same-loop order comes from the recorded tracker. Ten target frames shared a loop with another owner change and were located by their previously projected map tag. No two generated beacon records shared a loop. All unselected event dictionaries come from the recording. Capture prediction, ordering against independently generated unrelated events and playback remain unverified by this experiment.

## Reproduce

Use the recovery repository modules and its pinned Blizzard protocol files on Python's import path. Supply your own hash-matched replay, map and extracted MapMechanics library. Historical and stock layouts accept their verified release map or matching two-talent package. The output path must be new.

```text
python camp_owner_wire.py generate --source-replay TEN_GREYMANE.StormReplay --layout 41810 --map historical.s2ma --mechanics MapMechanicsLib.galaxy --output historical-owner.private.bin
python camp_owner_wire.py verify-control --replay control.StormReplay --sha256 CONTROL_SHA256 --build 98348 --map stock-98348.s2ma --mechanics MapMechanicsLib.galaxy
python -m unittest test_camp_owner_wire
```

The [source results](../observations/camp-owner-source-wire.json) record both layout outputs. The [layout comparison](../observations/camp-owner-layout-wire.json) covers both release maps and their two-talent packages. The [per-replay results](../observations/camp-owner-cohort-wire.json) list tracker digests and physical byte comparisons.
