# TEN opening unit radii

The build 98348 catalog specifies a live Radius for all 172 opening TEN units on the GateOrder map, across 45 unit types. In the generated JSON, look up `by_unit[unit].radius_fixed4096` and check that the target slot appears in `slots`. The integer is the exact catalog value multiplied by 4,096. Each entry names its field owner, XML source and inheritance chain. The 160 rows in the separate opening spatial table match by both slot and type.

| Units | Radius |
| --- | ---: |
| Shrine Sun and Moon | 0.0625 |
| Ownership flags, shrine targets, healing-pad search units and TheLittleKing | 0.5 |
| L2 and L3 gates | 0.75 |
| Cannon towers and both startup pathing blockers | 1 |
| Moonwells and VehicleDragon | 1.5 |
| Walls | 2 |
| L2 town halls | 2.5 |
| Mercenary camp capture beacons | 2.75 |
| L3 town halls | 3 |
| KingsCore and Dragonball capture beacons | 4 |

The local scan read all 5,575 XML files in the pinned catalog projection, totaling 79,556,009 bytes, and verified each size and SHA-256. It found 1,997 CUnit declarations. The GateOrder map names HeroesData as its direct dependency, adds four CUnit declarations, and gives all 165 authored units scale 1,1,1. Seven scripted beacons complete the opening set. The map-only HealingPadSearchUnit inherits the Core class default. Both node removals on this record address BehaviorArray.

For each opening type, resolving all published packages together reproduces the same live radius and inheritance path after excluding the single-player Try Mode map, whose KingsCore radius is zero. The local install could not resolve the separate DocumentInfo lookup for Core, HeroesData or Heroes. Agreement across this broader package set allows the scalar to be resolved without relying on the ordering of hero packages.

The scan found zero explicit DeadRadius fields across these installed CUnit declarations and the four map declarations. Its native default is unresolved. Using the supplied Radius for an individual simulation record requires evidence for the live branch and any per-instance adjustment.

`opening_unit_radii.py` accepts `--projection`, `--archive`, `--gate-map`, `--opening` and `--output`. The archive argument accepts a full extracted catalog directory or the verified private ZIP of CUnit and Includes XML files. The opening argument is the privately generated `TEN.opening.frames.private.json`. The script emits only map unit identifiers, public catalog paths, slot numbers, scalar values, hashes and aggregate counts. The CASC XML, ZIP archives, extraction logs and scan scripts stay in local evidence storage. The generated receipt has SHA-256 `0baee44fc09a7071c9a85df1dbb12ee6d47c67dc45b99b0ee2c591facbfaa4b8`.
