# GateOrder's map checksum

For the historical Dragon Shire layout, GateOrder supplies **`0x2d44411f`** for `m_mapFileSyncChecksum`. The build-98348 loader reads this little-endian DWORD at offset 28 of the map's version-8 `DocumentHeader`. GateOrder has the same header as the original TEN package. Its whole-archive CRC32 is `0x6d3ada96`. The native setup writer and the loading comparison both use the header word. This resolves the field on the checked loading path. The rest of custom-map validation remains open.

The same read independently reproduced the physical setup field in all 24 target replays, covering nine distinct map archives, and in the original build-41810 TEN replay. The adjacent DWORD at offset 32 happens to equal the first in the historical archive. All nine target archives distinguish the two offsets. [Control results](../observations/declared-map-checksum.json)

Holding the other partial R8 setup fields fixed and substituting the five GateOrder handles leaves one unknown resource word, `m_modFileSyncChecksum`. The 4,222-byte setup has a CRC constant of `0x078b4076` at the algebraic zero input for this word. The receipt gives its 32 one-bit contributions. The actual mod checksum requires the separately selected pregame history entry. The constant is used only to evaluate the CRC once that input is known.

Run `declared_map_checksum.py CONTROL_MANIFEST ORIGINAL R8_SELECTION_COPY GATEORDER_MAP CACHE_ROOT` to reproduce the observations and coefficients. Run `native_resource_checksums.py PE DECODED_TEXT --map GATEORDER_MAP` for the independently recovered loading and comparison logic.
