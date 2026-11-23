# Original Dragon Shire camps

TEN_GREYMANE records five camp initializations at loop 0. The original map preloads `CampOwnershipFlag` and places one near each camp. At loop 2,530, exactly 1,920 loops after the gates open, all five flags change to hostile owner 15 and five map icons are born. Sixteen defenders appear at loop 2,532, including a group of knights at camp 2, which remains uncaptured throughout this recording.

| Camp | Defender group | Capture loops |
| --- | --- | --- |
| 1 | Siege giants | 9017, 13819, 18731 |
| 2 | Knights | — |
| 3 | Siege giants | 5343, 9172, 13757, 19012 |
| 4 | Knights | 6909, 11604, 16096 |
| 5 | Knights | 4217, 9828, 14346 |

At every capture the camp beacon changes to the capturing team's owner one loop before the `JungleCampCapture` stat. On the capture loop the flag and icon take that owner, and the corresponding allied wave is born nearby. Seven siege captures produce 14 giants. Six bruiser captures produce 18 melee knights and six ranged mages. Camp assignment uses a unique nearest map point within eight units and the camp ID in the stat record. The stored negative-diamond geometry leaves containment of camp 3’s flag uncertain under the available polygon interpretations. Four captures independently tie that flag's owner changes to camp 3.

The original map archives only `MapScript.galaxy`, which includes the external `TriggerLibs/MapMechanicsLib`. Its other four dependency cache entries are short standard-data references. The installed 98348 library disables a camp when it cannot find `LootBannerSconce`. Its timer startup checks the enabled flag before scheduling defender births. Blizzard documented the introduction of player-selected banners on mercenary captures in 2017. The published game-script archive starts at build 71138. The exact 41810 library branch remains unverified. [Blizzard 2.0 launch notes](https://news.blizzard.com/en-gb/article/20721900/heroes-of-the-storm-2-0-launch-notes-april-26-2017) · [Game-data version index](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/master/VERSIONS.md)

Use these tracker events as acceptance criteria for a future original-layout camp implementation. Binding the five historical flags alone would still leave icon timing, initial defenders and captured waves to reproduce. The current evidence verifies an incompatibility and its effects on the recorded match. [Machine-readable results](original-camp-events.json)
