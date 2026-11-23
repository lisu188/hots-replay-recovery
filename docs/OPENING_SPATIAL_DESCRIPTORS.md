# Opening unit descriptors in build 98348

The first operand of the fast sync CRC depends on an ordered stream of changes to the spatial index. A successful create folds a 12-byte little-endian descriptor and its new four-byte handle. An update folds the descriptor, previous handle and new handle. A gated release folds the previous handle. Even an update that keeps the same handle can change the accumulator. [Fast sync inputs](FAST_SYNC_INPUTS.md)

| Bytes | Meaning from the 98348 image |
| --- | --- |
| 0–3 | Bits 0–9 carry the unit tag index. Bits 10–13 are zero. Bits 14–17 carry the owner. Bits 18–23 hold three coordinate bits per axis. Bits 24–27 hold the low nibble of the radius rounded upward in quarter-world-unit steps. Four final bits depend on the unit's current type and instance flags. |
| 4–7 | Two unsigned 16-bit grid coordinates. Nonnegative positions use two-world-unit cells. The native division by two first truncates toward zero for signed inputs. |
| 8–11 | The current selected CUnit radius in fixed-point units. The field registration binds offset 0xf0 to Radius and 0xf4 to DeadRadius. Unit state chooses the catalog branch. |

The position path in RVA 0x9a8660 uses the same 16 decoders, in the same order, as the live branch of the Galaxy UnitGetPosition handler. The unit lookup checks its full tag at +0x10. UnitGetOwner reads +0x44. The spatial descriptor reads both members. Bit 28 tests the effective collision mask, bit 29 reads unit+0x38 bit 6, bit 30 reads a selected type flag, and bit 31 tests a signed counter and two state flags. The check against the pinned PE tables covers 768 synthetic CRC cases. [Native verification](../observations/unit-spatial-descriptor.json)

For successful ordinary insertion, the two grid coordinates and the occupied slot within its chain of 15-entry buckets determine the handle cached at unit+0x2b4. Large units use a separate list. Small units inserted during deferral use a pending list. The presence of either list, the insertion order and changes between creation and loop 64 affect the actual match. [Opening field checks](../observations/opening-spatial-fields.json)

The GateOrder map and startup rules reconstruct 172 ordered loop-zero births. All 172 have resolved fixed-point X and Y, independently matched integer birth coordinates, owner and tag components. For 167 slots the authored coordinates are exactly representable. For five placed objects the native position parser rounds ten decimal components to units of 1/4096. Sixteen snapshots of a stationary WaygateEntrance on another build-98348 map corroborate rounding on both axes. [Native position parser](PLACED_UNIT_COORDINATES.md) · [Placement checks](../observations/placement-snapshots.json)

A separate comparison reproduces owner, X/Y and the packed coordinate fields on 2,179 historical command snapshots across 68 TEN buildings and 13,192 snapshots in 15 native Dragon Shire recordings. These checks use command targets observed while the selected unit generation was alive. The spatial-cache descriptor itself is absent from the replay streams.

On the unmodified live-radius branch, the private value-and-mask ledger determines 92 of 96 bits for each of the 172 slots. Bits 28–31 of the first word are masked for every slot. The catalog places four slots above the small-unit threshold and 168 on the small side. The candidate handles assume an empty enabled grid, insertion in tracker birth order, and no deferral or intervening release. The first fast CRC still requires the actual create, move, update and release sequence, active branch and instance state. [Resolved live radii](OPENING_UNIT_RADII.md) · [Masked projection](../observations/opening-spatial-radii.json)

```text
python verify_unit_spatial_descriptor.py EXE PINNED_DECODED_TEXT
python verify_placement_xy.py EXE PINNED_DECODED_TEXT GATEORDER_MAP
python check_placement_snapshots.py TEN CONTROL_PATHS MAP_CACHE
python opening_spatial_fields.py TEN GATEORDER_MAP MAP_MECHANICS CONTROL_PATHS STOCK_MAP
python opening_spatial_radii.py TEN GATEORDER_MAP MAP_MECHANICS observations/opening-unit-radii.json --private-output NEW_FILE
```
