# Build 98348 map placement coordinates

The native ObjectUnit importer resolves all ten previously uncertain X/Y components on the GateOrder map. The values below are the initial placement inputs in units of 1/4096. Each final pair gives bits 10–12 of each coordinate for the spatial descriptor.

| Object ID | Unit | X | Y | Quarter-cell X, Y modulo 8 |
|---:|---|---:|---:|---|
| 22 | TheLittleKing | 442490 | 655810 | 0, 0 |
| 477 | CampOwnershipFlag | 413165 | 320829 | 3, 1 |
| 478 | CampOwnershipFlag | 602077 | 322626 | 3, 3 |
| 718 | GardensDragonShrineTargetMoon | 493258 | 446222 | 1, 3 |
| 760 | GardensDragonShrineTargetSun | 523280 | 445352 | 7, 2 |

The classifier at RVA 0xA30A80 recognizes ObjectUnit. The reader's tail jump at 0xA2EAF1 passes the recognized type to 0xA31680. This routine passes position attribute selector 0x14 and a pointer to placement+0x0C to 0xA297C0. Its two spellings `position` and `Position` lead to the same three-component parser at 0x28A310. That parser splits on commas, calls 0x2D14E0 per token and copies three signed 32-bit results into the placement. The unit creation path at 0xA2E3DB reads X and Y from placement+0x0C and +0x10.

For the map's ordinary decimal notation, the converter shifts the absolute whole part left by 12. The table at 0x2F2F7E0 supplies the powers from 10¹² down to 1. For the fraction, the converter adds half the denominator to the numerator multiplied by 4096, performs unsigned integer division, adds the whole part and applies the sign. Each resulting coordinate differs from the XML literal by at most 1/8192 world unit. The standalone helper checks the bounded map input grammar and preserves signed 32-bit range. The native parser also contains exponent and whitespace paths.

The original TEN file and 24 pinned 98348 recordings were checked against their own cached map packages. Matches use unique birth and placement signatures (unit type and tracker X/Y), the full unit tag, and the initial lifetime. Sixteen command snapshots on an independent map matched both inexact axes of WaygateEntrance 1223 at `191.6435,85.9755`. Both axes distinguish rounding from truncation. On stock Dragon Shire, 79 target snapshots matched VehicleDragon's initial position and 710 differed later in the match. The five historical objects had no direct TEN target snapshots. Applying an initial placement to a later simulation object requires its own lifetime and movement evidence.

`verify_placement_xy.py` verifies the PE and text section hashes, eight native code windows, ten transfers, the decimal table, attribute names, and the five GateOrder rows. `placement_xy.fixed_coordinate(value)` returns a signed integer. `placement_xy.generate(gate_map)` returns the five rows. [Native parser receipt](../observations/placement-xy.json)

Run `python check_placement_snapshots.py TEN CONTROL_PATHS MAP_CACHE` to check the original recording and all 24 build-98348 controls across nine maps. The manifest maps replay hashes to local paths. The checker verifies the recordings and map packages against their hashes and reports aggregate snapshot counts. [Physical snapshot receipt](../observations/placement-snapshots.json)
