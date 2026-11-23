# Opening hero targets in TEN_GREYMANE pings

The roster, original Dragon Shire opening order, player death and level statistics, and respawn times recovered from three other historical matches identify 13 unit-targeted pings across six opening hero identities. One occurred during the hero's first life and 12 after a revive. All ten predicted hero histories match the independently observed born, died and revived records through the core's destruction at loop 19521. The projection excludes ambiguous identities, events at a life boundary, and pings outside a confirmed live interval.

Combining these 13 with the 59 previously generated map-backed inputs yields 72 of 81 source pings, 1,409 bytes, SHA-256 `508fe29ab13ab7857790a571f897d1530f1147e5bddc570c26eb8a38adee01d3`. The named target reader recovered the selected rows in source order, including their original loops, user IDs, coordinates, options and minimap flags. An additional comparison to the retained tracker independently reproduced those same 72 rows. The tested package retained the historical map layout. Target simulation remains conditional on the reconstructed opening and historical lifetimes. Nine other unit-targeted pings fall outside this projection.

~~~text
python primary_hero_pings.py --source TEN.StormReplay --original-map ORIGINAL.s2ma --historical-map GREYMANE_COCKTAIL.s2ma --reference CONTROL_1 SHA1 --reference CONTROL_2 SHA2 --reference CONTROL_3 SHA3 --output map-and-hero.private.bin
~~~

Each control digest is a SHA-256 identified in the observation. The output is a private sparse stream of event 36 frames.
