# Historical talents on Dragon Shire

`build_dragonshire_talent_map.py` builds a separate MPQ from either the exact Dragon Shire used in TEN_GREYMANE (41810) or the stock 98348 map. Both variants set Kael'thas's Mana Addict completion gate and quest target to 25. Supplying the build-98348 Anub'arak catalog also restores the Bed of Barbs slow to 30%. The original-layout variant retains the match's terrain, placed objects and map script.

## Reproduce the two-talent variant

Use Python 3.12 and the repository modules. The byte-identical CLI rebuild used Ubuntu amd64 `libstorm9` version `9.22-1build1`, with `libstorm.so.9.22.0` SHA-256 `d21b125a4dbeb8d5e52771c1a4a49ee12e7fa19bc2ddd600e31265f73cdc38ba`. The destination directory must exist, be writable and support hard links. Use a new output filename. The program checks each input digest and prints a JSON receipt after validating the archive.

```sh
python build_dragonshire_talent_map.py \
  --source-map DragonShire.stock.s2ma \
  --hero-xml kaelthasdata.xml --anubarak-xml anubarakdata.xml \
  --historical-catalog heroes.json --stormlib /usr/lib/libstorm.so.9.22.0 \
  --output DragonShire.historical-talents.s2ma
```

The hero XMLs come from the 98348 data. `heroes.json` is the [build-41810 historical catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json). All input hashes, including both stock maps, are in the [four build receipts](../observations/dragonshire-historical-talent-maps.json). Omit `--anubarak-xml` to reproduce the two quest-only controls.

| Map layout with both talents | Bytes | SHA-256 | Original content members preserved byte for byte |
| --- | ---: | --- | ---: |
| 41810 | 2,130,235 | `662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800` | 66 of 67 |
| 98348 | 2,228,782 | `2de7e30ecf97cb975f483e8dc33ec05035d5b42d1e45a9a011dfecb4984b1632` | 73 of 75 |

On the 41810 layout, the builder updates the empty `BehaviorData.xml` and adds `TalentData.xml`. On the 98348 layout it appends the quest include after the existing doodad include and updates `BehaviorData.xml` for the slow. The gate override selects `ConditionalEvents` index 0, retaining its existing `GE` comparison, quest event and shield-unlock effect.

## Verification and remaining work

The builder reads each content member with StormLib and a separate Python MPQ reader, accounts for all live blocks, checks the v4 header and asks StormLib to verify available raw and member checksums. Both full archives and both quest-only controls reproduced byte for byte in separate CLI builds.

Heroes.MpqTool 1.4.0 and Heroes.XmlData 1.1.1 independently loaded all six physical archives against the same selected 98348 catalog records and two parents. The stock maps yielded 20/20 and a 25% slow. Quest-only copies yielded 25/25 and a 25% slow. Both final copies yielded 25/25 and a 30% slow. All 36 complete XML record comparisons passed across ordinary and parent-expanded lookup. [Reader observations](../observations/dragonshire-historical-talent-reader.json)

The stock `DocumentHeader` survives byte for byte in each copy. Its advertised checksum therefore cannot establish a newly computed content-sync value for the modified map. The replay's target map handle, reconstructed simulation checksum and native playback remain unverified. These packages are inputs to further conversion work.
