# Opening hero tags on Dragon Shire

The TEN_GREYMANE roster contains ten player slots and eight distinct heroes. A prediction using the initial lobby teams, slots, hero names and known map startup count reproduced its ten opening hero births. The same prediction matched all ten rows in **2 of 4** historical recordings and **14 of 15** stock build-98348 recordings. A new Tyrande recording selected by its retained attribute member matched all ten rows on its first test.

Build 41810 starts with 172 map-created units and stock 98348 starts with 170. Within each team, take the physical lobby slots in increasing order. The observed ordinary case creates the first hero on each team at loop 50, starting with team 0. It then creates the next pair every eight loops through loop 82, starting each remaining pair with team 1. The prediction assigns consecutive indices starting at the map startup count and recycle 1. Both owners use the physical slot number plus one under the lobby's zero-based slot convention. These results compare the exact event order, loop, index, recycle, control owner, upkeep owner and unit type against all opening tracker births and initializations through loop 82.

Two historical rosters containing Xul emitted an additional `NecromancerTalentBoneArmorItem` at loop 50 or 58, moving the indices of later heroes up by one. A stock D.Va roster had a mech and a different same-loop allocation order. The rule recovered 26 of 40 historical rows and 140 of 150 stock rows overall.

| TEN hero key | Stock Dragon Shire appearances | Exact predicted rows |
| --- | ---: | ---: |
| Abathur | 0 | 0 |
| Anubarak | 4 | 4 |
| Barbarian | 2 | 2 |
| FaerieDragon | 4 | 4 |
| Greymane | 2 | 2 |
| Kaelthas | 0 | 0 |
| Nova | 0 | 0 |
| Tyrande | 1 | 1 |

Each of those 13 stock appearances had one expected birth with no additional birth credited to its owner in the eight-loop window beginning at the spawn tick. A separate nine-replay set on other maps contained Abathur once, Kaelthas twice, Nova twice and Tyrande three times. Each had one recorded hero birth and no other birth credited to that owner in the same window. This second check used each observed spawn tick and measured no Dragon Shire-specific allocation ranks.

## Current spawning code

The installed game data for 2.57.0.98348 yielded 215 named Galaxy scripts under `mods/`. All 215 passed their CASC content key and file size checks. Only the D.Va and Cho'Gall libraries called the helper that adds a manual-spawn hero. They register D.Va and Gall respectively. Each library initializer installs a trigger for the core's mod-initialization event. HeroesLib sends that event at line 4927 and writes the registry at line 415. The two registration calls appear at `LibHDVA.galaxy:480` and `LibHCHO.galaxy:1263` in the pinned scripts. GameLib checks the registry in each team's asynchronous spawn loop, creates an ordinary hero via the default branch and then waits half a game second. See `GameLib.galaxy:10686–10774` and `GameLib_h.galaxy:449`.

The checked recordings establish source and stock behavior. The recovered historical-layout package has no observed build-98348 hero startup, and these checks do not establish its allocation history or subsequent unit lifetimes. Keep target tags conditional when that history is required.

## Reproduction

Run `python check_roster.py --case REPLAY SHA256 BUILD` with one repeated option per case. The nineteen case digests and builds are recorded in `dragon-hero-ranks.json`. The separate `check_cross_map_births.py` takes repeated `--case REPLAY SHA256` options for the nine digests in `cross-map-births.json`. Both tools print aggregate evidence without player names, replay paths or per-player event logs. Use the repository's pinned replay readers. The manual registry summary is in `manual-hero-registry.json`.
