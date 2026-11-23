# Opening unit footprints in 98348

On the ordinary creation path, **18 of 172 opening slots** have zero for descriptor bit 29 when the absent catalog link resolves to a null pointer and the initial footprint state persists through the sample. This leaves one unknown bit in those 18 descriptors and two in the other 154. The input ledger already carries conditions on recorded unit type, live radius and collision overrides. [Per-type results](../observations/opening-footprint.json)

| Source of the creation request | Slots with both catalog links absent |
| --- | ---: |
| Map placements, comprising the king, vehicle, five camp flags, two shrine targets and two healing search units | 11 |
| Galaxy creation, comprising five camp beacons and two shrine beacons | 7 |

### Catalog lookup

The 98348 CUnit constructor clears the live and dead links at relative offsets `+568` and `+570`. Reflection identifies them as `Footprint` and `DeadFootprint`. After the shared type's `+90` base is included, `9A0080` uses the fields at `+5F8` and `+600` to populate two resolved pointers. `99FE80` returns a view at shared type `+888`. Its `+18` is the live footprint, and `+10` is the dead footprint. A third pointer derived from `PlacementFootprint` has a different destination.

Core, HeroesData and GateOrder yield eight opening unit types with both links absent. Checking the full package superset preserves this absence for all eight. The installed projection contains 203 named `CFootprint` declarations and one class default across 22 XML members. GateOrder adds none. The native lookup at `98C5A0` compares the key length and bytes and returns null on a miss. An empty key cannot match any of the 203 named declarations. Whether the runtime registry installs additional unnamed entries remains open.

### Per-instance override

The map reader recognizes `footprint` and `Footprint` at parser `+590`, equivalent to placement record `+530`. All 165 GateOrder placements omit the override. The loader at `A2E20F` takes the empty-name branch and stores zero at `A2E2CF` into creation request `+58`. A subsequent catalog fallback in this routine serves placement geometry. The spawn routine at `9BB2CF` copies request `+58` into unit `+200`.

The two target script calls that create shrine beacons use `UnitCreate`. The camp beacon helper selects a facing and forwards to the same native. Galaxy slot 1453 calls `204DCA0`, which forwards to `205DF30`. There the frame base is `rsp+100` and the unit creation request starts at `rsp+40`. The zero store at `205E024` goes to `rbp-68`, exactly request `+58`. The normal allocation at `205E602` passes the request to `996D90`, which forwards it at `99705A` to `9BAEF0`.

### Bit 29 and remaining runtime conditions

Both identified direct routes to setter `990E90` check that a selected footprint exists. Ordinary recomputation at `99AC00` selects the dead catalog pointer when the dead flag is set. Otherwise it selects the instance override or the live catalog pointer. The alternate type-update path at `9BA19B` uses predicate `991660` with the same pointer tests. The setter sets the bit before its own pointer checks, so the preconditions at both callers matter. Named links also face visibility, instance and height tests.

The ledger assumes the empty key misses in the engine registry, the recorded type and initial override persist, and only the identified setter paths can enable the bit before the sample. Whole-text rel32 scanning covers direct calls and tail jumps to the setter. Indirect dispatch, other direct writes of the underlying instance flag and mutations after ordinary creation remain open. The projection does not establish a first-sync CRC.

### Reproduce

With the recovery repository on the Python import path, run the following commands. `FOOTPRINT_XML` accepts the full projected XML tree or the checked 22-member archive. `SCRIPT_DIR` supplies the pinned target MapMechanicsLib and NativeLib files. The producer writes private unit rows only when the optional output is supplied.

```text
python opening_footprint.py EXE TEXT PROJECTION UNIT_XML FOOTPRINT_XML GATEORDER_MAP SCRIPT_DIR OPENING_BIRTHS BASELINE_94 --private-output NEW_PRIVATE_LEDGER
python check_opening_footprint.py BASELINE_94 NEW_PRIVATE_LEDGER
```
