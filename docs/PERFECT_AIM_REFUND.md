# Greymane’s Perfect Aim refund

TEN’s second Greymane chose selector 1 at game ordinal 1286, loop 241. Tracker ordinal 248 recorded the `GreymaneGilneanCocktailPerfectAim` purchase for player 3 at loop 242. The original header identifies build 41810 and the match date in `replay.details` is April 12, 2016 UTC. The archived build-41810 talent description specifies a 50 Mana refund for hitting an enemy Hero. Blizzard set the refund to 50 on January 27 and fixed refunds from the far edge of the explosion on March 29. The match took place after that fix. [41810 hero export](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [January 27 balance update](https://news.blizzard.com/en-us/article/20021838/heroes-of-the-storm-balance-update-notes-january-27-2016) · [March 29 patch notes](https://news.blizzard.com/en-us/article/20063493/heroes-of-the-storm-patch-notes-march-29-2016)

In build 98348, the talent enables two effects by raising both of their chances from zero to one. The first puts a 1.25-second refund token on the caster. Direct and spread impacts invoke the second effect, which checks the caster’s token and `TargetIsHero`, removes the token, then restores energy to the caster. The installed healer specifies `RechargeVitalRate=45` and inherits `RechargeVital=Energy` from `StormManaRestore`. The map adds one field to the healer to set the rate to 50. The recorded selection establishes the purchase. Individual casts and amounts actually received would also depend on the hits, token state and available mana capacity.

The 98348 missile projection and guide each start at 8.5 and gain 2.55 with the talent, reaching 11.05 in their catalog fields. The historical export reports a 30.3571% range increase. It supplies neither absolute missile distances nor the collision or explosion geometry. The map uses the stock 98348 distances and target search. Exact historical impact locations remain unresolved.

The private child of ExtendedSpikesRange is 2,198,586 bytes, SHA-256 `9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870`. Two fresh builds matched byte for byte. StormLib and a second MPQ implementation checked the 71 content members of both packages. Only `Base.StormData\GameData\EffectData.xml` changed. An independent Heroes.XmlData 1.1.1 read of the actual parent and child packages resolved the caster’s refund to 45 and 50 respectively, including the inherited energy field. This test used the relevant selected stock records. Native execution and end-to-end replay compatibility remain unverified.

Run the builder twice with distinct, fresh output paths and the same pinned inputs, then pass those maps to the independent reader. The builder uses the repository’s Python modules and StormLib. The repeat used Ubuntu amd64 StormLib 9.22. The PowerShell verifier takes the released reader libraries and the installed 98348 common effect catalog and Genn hero catalog.

```sh
python build_perfect_aim_map.py EXTENDED_SPIKES_RANGE HISTORICAL_HEROES_JSON GENN_XML ORIGINAL_TEN NEW_MAP --stormlib STORMLIB
python build_perfect_aim_map.py EXTENDED_SPIKES_RANGE HISTORICAL_HEROES_JSON GENN_XML ORIGINAL_TEN REPEAT_MAP --stormlib STORMLIB
```

```powershell
./verify_perfect_aim_map.ps1 -ParentMap $base -CandidateMap $candidate -RepeatMap $repeat -GennXml $genn -EffectXml $coreEffects -MpqToolDll $mpq -CascLibDll $casc -LibraryDirectory $readerLibraries
```

The NGS Infernal Shrines recording from November 7 confirms the current talent selector and award at loops 265 and 266. The converter uses TEN's first purchase for its second Greymane at loop 241 and projects the award at 242. The resulting 142,573-byte sparse stream joins 17,710 original inputs through loop 19,732. Removing this input recovers the full parent stream byte for byte. The separate projected award is 112 bytes. All 17,453 later retained inputs are camera, departure, chat, zero-target ping or previously checked Kael'thas selections. The rest of the match remains subject to the parent omissions, historical spell geometry and simulation checks. [Public Greymane control](https://s3.amazonaws.com/ngs-replay-storage/ngs_11-7-2026_Roll1Esports_vs_COSMOS_Infernal_Shrines.stormReplay)

```text
python perfect_aim_control.py NGS_PERFECT_AIM_REPLAY GENN_XML
python perfect_aim_inputs.py ORIGINAL_TEN HISTORICAL_HEROES_JSON GENN_XML EXTENDED_SPIKES_RANGE PERFECT_AIM_MAP COMMON_STARTUP_PREFIX NGS_PERFECT_AIM_REPLAY EXTENDED_WAR_PAINT_INPUT_DIR EXTENDED_WAR_PAINT_RECEIPT NEW_OUTPUT_DIR
```
