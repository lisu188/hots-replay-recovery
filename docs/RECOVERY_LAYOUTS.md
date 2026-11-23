# Offline recovery on the original Dragon Shire layout

The historical two-talent map, its Greymane cooldown update, the subsequent Gilnean Cocktail update and the respawn-curve map share the original match geometry and map-authored startup units. The snapshot, ping, camera and camp checks accept the four verified archive digests. Each output records the digest of the supplied package.

With each package the independent paths reproduce the same 2,179 target-command snapshot points and their original event ordinals, 59 map-qualified ping inputs, 26 camp tracker records and six map-backed camera endpoints. [First three maps](../observations/historical-layout-compatibility.json) · [Respawn map](../observations/respawn-layout-compatibility.json)

The respawn map also reproduces the preceding map's 72-ping stream, including 13 primary-hero pings. Its Objects and Regions members match the original map. Removing the 899-byte callback and 82-byte registration from its map script reproduces the original script byte for byte. Historical hero lifetimes and map-authored placements support these projections. Target simulation checksums remain open.

~~~text
python verify_recovery_layout.py --source TEN_GREYMANE.StormReplay --original-map ORIGINAL.s2ma --map RESPAWN_CURVE.s2ma --mechanics MapMechanicsLib.galaxy
~~~
