# Offline recovery on the original Dragon Shire layout

The historical two-talent map, its Greymane cooldown update and the subsequent Gilnean Cocktail update share the original match geometry and map-authored startup units. The snapshot, ping, camera and camp checks accept the three verified archive digests. Each output records the digest of the supplied package.

With each package the independent paths reproduce the same 2,179 target-command snapshot points and their original event ordinals, 59 map-qualified ping inputs, 26 camp tracker records and six map-backed camera endpoints. These outputs cover selected input fields. The independently generated post-startup unit lifetimes and the target simulation checksums remain open. [Per-map results](../observations/historical-layout-compatibility.json)

~~~text
python verify_recovery_layout.py --source TEN_GREYMANE.StormReplay --original-map ORIGINAL.s2ma --map GREYMANE_COCKTAIL.s2ma --mechanics MapMechanicsLib.galaxy
~~~
