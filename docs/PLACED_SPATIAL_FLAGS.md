# First spatial insertion of 98348 map units

The GateOrder map has 165 authored units. All 165 contribute **zero** through the native `UnitHidden` placement flag when their first spatial descriptor is built. The same check gives zero for the 165 historical and 158 retail placements. The verifier identifies the flag in the original PE, checks 22 code windows in the pinned 98348 static text, and reads the three map archives.

| Map | Authored units | ForcePlacement set | UnitHidden set |
| --- | ---: | ---: | ---: |
| Dragon Shire 41810 | 165 | 107 | 0 |
| Dragon Shire 98348 | 158 | 111 | 0 |
| GateOrder overlay | 165 | 107 | 0 |

## Placement data and insertion order

The active parser record starts at parser offset `+60`. Constructor `A2A290` zeros the eight bytes starting at record `+24`, covering its DWORD flags at `+28`. `A316B6/C2` initializes and copies a fresh record when starting an object. `A29FE0` resolves an index by comparing with 14 counted strings in the original PE table `2F709D0`. `UnitHidden` is index 4 and `ForcePlacement` is index 5. `A2EF71..95` uses the parsed boolean to set or clear that index at parser `+88`, which is record `+28`. Both record-copy routines preserve this DWORD.

The preplaced-unit loader at `A2E3DF..42E` copies flag 4 to bit 8 of the unit creation request. The actual flag-name lookup, independent masks and all three whole-map hashes are part of the verifier. The source map and GateOrder have the same physical `Objects` member digest despite their different whole-archive hashes.

1. The ordinary mode-1 pool allocation clears all 752 bytes before calling the unit constructor. The constructor additionally zeros `unit+38..43` and both 32-bit collision overrides at `+2E4/+2E8`. These are allocation-time values.
2. On a request with bit 8, `9BB3D3 → 99E2B0(mode 0)` increments the byte at `unit+4C`. The initial spatial descriptor is inserted at `9BBB89`. The same request bit then enables the matching decrement at `9BBB9E`. After the spawn returns, placement flag 4 independently gates `A2E4A8 → 99E2B0(mode 1)`, which sets `unit+3C` bit 4. All three updates from the placement flag are skipped for these maps. Other producers of the live counter and flags remain possible.
3. At `9BB9E1 → 99AC00`, the native code recomputes the state feeding descriptor bit 29. A missing selected catalog row or its backing pointer clears the bit. With `unit+39` bit 2 set, the backing pointer is row `+10`; otherwise it is the first nonzero pointer of `unit+200` and row `+18`. Any of the three live conditions for descriptor bit 31 also clears bit 29. Two more disqualifiers are `unit+3F` bit 0 and unsigned `unit+A3 >= 9`. With the guards passed, bit 29 is true if `unit+46` bit 0 is set, `unit+3D` is negative as a signed byte, or the dwords at `unit+6C` and selected base `+14C` are equal. The routine changes `unit+38` bit 6 via `990E90` or `9977E0`.

**The mutual exclusion between bits 29 and 31 holds at the recomputation.** The subsequent interval through `9BBB86` contains calls with the unit or its subobjects, including `A40480` and conditional `BE0BF0`. Preservation across that interval has not been established. The XML check specifically eliminates the authored hidden contribution. Live bit 31 at insertion, effective collision bit 28 after callbacks, and shared catalog bit 30 still need independent inputs.

Run `verify_placed_spatial_flags.py EXE STATIC_TEXT MAP_41810 MAP_98348 MAP_GATEORDER` with the recovery repository and its Python dependencies on the import path. The JSON records each map's whole hash, member hash and placed-unit counts.
