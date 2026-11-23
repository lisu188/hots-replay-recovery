# Restoring Anub’arak’s Bed of Barbs slow

Anub’arak selected Bed of Barbs at loop 4582 of TEN_GREYMANE. The tracker names the purchase on loop 4583. The 41810 hero catalog records a 30% movement slow. Blizzard’s later balance notes confirm the change from 30% to 25%. [Historical catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [Blizzard balance notes](https://news.blizzard.com/en-us/article/20749068/heroes-of-the-storm-patch-notes-may-31-2017)

The 98348 tooltip computes the percentage as `-100` times the `UnifiedMoveSpeedFactor` of `AnubarakImpaleBedOfBarbsSlow`. The converter restores that field to `-0.30` in a separate XML member. Two bytes change at offsets 72159 and 72160. The result is 234,204 bytes with SHA-256 `657b41695ad027b345f4db1c2007e536b3208b0e1e26eba33d9c36a621e5de6e`. Historical raw damage, effective talent selection and native playback remain unverified. [Tagged current tooltip](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/v2.57.0.98348/mods/heroesdata.stormmod/enus.stormdata/localizeddata/gamestrings.txt)

Run the following with Python 3.11. It verifies both input hashes and writes a change report to standard output. Add `--emit-xml` to emit the corrected member bytes.

```text
python -B restore_bed_of_barbs.py --target-xml AnubarakData.xml --historical-catalog heroes.json
```
