# Gilnean Cocktail on the original Dragon Shire layout

The combined map restores Greymane's base Q cooldown from 9 to 8 seconds. The build-41810 hero export gives 8 for `GreymaneGilneanCocktail`. Blizzard raised the cooldown from 8 to 10 in July 2016 and lowered it from 10 to 9 in June 2018. The pinned 98348 Genn XML declares 9 at `CAbilEffectTarget/Cost/Cooldown.TimeUse`. [Build-41810 hero export](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [Blizzard July 2016 notes](https://news.blizzard.com/en-us/article/20164442/heroes-of-the-storm-patch-notes-july-12-2016) · [Blizzard June 2018 notes](https://news.blizzard.com/en-gb/article/21905928/heroes-of-the-storm-patch-notes-june-27-2018)

Both Greymanes in the source replay selected Incendiary Elixir at loops 4275 and 4561, then Concentrated Blast at 11489 and 11908. The historical description gives Concentrated Blast an 80% damage bonus during Inner Beast. Blizzard recorded its removal in July 2016. The installed hero catalog has no matching talent declaration. The historical tooltip reports 59 initial and 177 explosion damage. The installed damage effects declare 55 and 220. The two historical talent interactions, damage scaling, and modifier order remain unresolved. On the target catalog Incendiary Elixir separately reduces Q cooldown on selection and quest completion. The restored 8 is the base value before those modifiers.

Run `build_cocktail_cooldown_map.py` with the same arguments as the Greymane cooldown map builder, passing the v2 map at `--source-map` and a fresh output. Two independent archive readers checked the resulting 70 content members, including the single amended ability catalog. The other 69 match v2 byte for byte. On the released Heroes.XmlData 1.1.1 reader the Q ability and four earlier Greymane records pass all 20 direct and parent-expanded comparisons across the two maps. The result is 2,131,152 bytes with SHA-256 `e6167145ee82e6c139f07336cd65fced5c86d162da19baad57a2d3e82b3a455e`. Native playback and effective match cooldowns remain unverified.

The portable PowerShell verifier takes the base, intermediate and final maps, the stock Genn XML, and pinned reader libraries. It compares both direct and parent-expanded records. Supply the rejected indexed-Cost map with the optional NegativeMap parameter to repeat the negative control.

~~~powershell
./verify_greymane_cooldowns.ps1 -BaseMap $baseMap -CandidateMap $greymaneMap -CocktailMap $cocktailMap -GennXml $heroXml -MpqToolDll $mpqDll -CascLibDll $cascDll -LibraryDirectory $readerDirectory
~~~

[Archived build receipts](../observations/greymane-cocktail-map.json) · [Independent full-record comparisons](../observations/greymane-catalog-comparison.json)