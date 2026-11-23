# Dragon Shire mercenary camp activation

Build 98348 requires a `LootBannerSconce` in each camp’s defender-leash region to schedule its initial defenders. The original Dragon Shire layout contains five `CampOwnershipFlag` units. The current initialization code looks up the literal `LootBannerSconce` type. The original flag type has no lookup, fallback or assignment in the 22 Galaxy files reachable through the map’s script includes.

| 98348 operation with the old layout | Static outcome |
| --- | --- |
| Configure the defenders and mercenary data, register the birth timer, create the camp beacon and its capture point | The initializer does these before the sconce lookup. It explicitly disables the capture point. The caller continues to reveal the area after returning. |
| Initialize the banner, minimap icon and camp panel | A missing sconce sets `lv_stateIsEnabled` to false and returns before these operations. The text-tag updater also checks this flag. |
| Schedule the first defenders | The scheduled game-start trigger checks `lv_stateIsEnabled` for each camp. It skips both the birth timer and the respawn timer for all five original-layout camps. |
| Spawn defenders and enable capture through normal play | The ordinary first-spawn route depends on that birth timer. The defender-death handler enables capture after the defenders are cleared. With the initial timers skipped, this sequence cannot start through its ordinary entry point. |
| Other routes | The timer-expiration handler can call the defender producer with a null icon if the timer fires independently. Ending hibernation can also call the producer for a camp already in the required state. The capture and reward handlers still exist. The debug reset explicitly creates a new sconce. |
| Record `JungleCampInit` | The support library emits this event from the configured camp list without checking the enabled flag. Its presence establishes that the camp was configured. |

The activation check covered every code reference to the enabled field in the map’s Galaxy include closure. `MapMechanicsLib.galaxy` contains the default at line 95, the failed lookup at 694–698, the text-tag guard at 1037, the initialization-loop guard at 4913 and the game-start timer guard at 4992–4994. `MapMechanicsLib_h.galaxy` contains the declaration. The other scripts contain no reference to this field.

## What the old flags prove

TEN_GREYMANE records all five original flags changing to hostile ownership at loop 2530. Five team-color minimap icons first appear in that loop at the five captain points. Sixteen hostile defenders appear two loops later, comprising nine melee knights, three ranged mages and four siege giants. All 13 recorded camp captures coincide with exactly one original flag changing to the capturing team at the same loop. Four of the five camps were captured.

Those observations support reusing an existing flag for ownership in a compatibility implementation. The 98348 script also uses the flag unit for XP, banner actor messages and a dialog attachment. The historical replay provides no equivalence check for those operations. Simply selecting the old flag and continuing the current initializer would immediately create an extra icon for each accepted camp. Preserving the recorded creation order requires separate handling of the historical icon timing. The historical Galaxy library and native behavior of a modified camp remain unverified.

## Reproduction

Run `verify_camp_startup_gate.py` with the directory of authenticated installed Galaxy members and its `member.json`, the original Dragon Shire map, and TEN_GREYMANE. The public receipt contains script hashes, matching line numbers, unit counts and capture observations. For complete loop-zero reconstruction, run `verify_script_startup_cases.py` with the map, authenticated 98348 mechanics library, physical replay files and the build. Run `test_dragon_startup_births.py` for the synthetic input and reconstruction checks.
