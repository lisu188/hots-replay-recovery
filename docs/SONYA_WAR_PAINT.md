# Convert Sonya's first War Paint choice

In TEN, user 9 selects slot 0 at game ordinal 1171, loop 200. At loop 201 the tracker awards player 10 `BarbarianMasteryWarPaint` (ordinal 247). The 41810 catalog describes healing for 30% of basic attack damage. The installed 98348 Barbarian tree puts `BarbarianWarPaint` in slot 1, tier 1, column 2. The talent grants `BarbarianWarPaintCarry` with life leech of 0.3 for basic damage and a SelfHealing score entry. The two supported map packages have no local overrides of these declarations. Blizzard documented the 30% effect in 2015 and the second-column placement in 2018. [41810 catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json) · [May 2015 update](https://news.blizzard.com/en-gb/article/19067455/heroes-closed-beta-patch-notes-may-13-2015) · [March 2018 update](https://news.blizzard.com/en-us/article/21594628/heroes-of-the-storm-patch-notes-march-6-2018)

The pinned October 15 NGS Infernal Shrines replay uses 98348, has SHA-256 `6987fe1729e6cc3afc272d1089c74d7ef001f5e340b60ac37610132586fb9939`, and shows a first War Paint purchase at loop 973 and its award at 974. The independently encoded 7-byte input and 95-byte tracker event match both physical frames at their recorded deltas. Four other Sonya recordings exercise both neighboring columns. The target choice and award for TEN use TEN's original user, player and clock and take 8 and 96 bytes when encoded separately. Health totals still depend on the damage of each simulated attack. [Public NGS control](https://s3.amazonaws.com/ngs-replay-storage/ngs_10-15-2026_Bork_Side_of_the_Moon_vs_NO_CC_NO_PROBLEM_Infernal_Shrines.stormReplay)

| Map | Assembled conditional game inputs | Remaining inputs | Sparse tracker |
| --- | ---: | ---: | --- |
| MercCapture | 21,586 | 82,671 | 676 frames, including 441 mapped after loop zero |
| ExtendedSpikesRange | 17,709 | 86,548 | Separate Sonya award fragment |

Each join preserves the source ordinal order. Removing the new game event and re-encoding restores the parent bytes on both maps. The same check restores the parent sparse MercCapture tracker after removing the translated award. The continuous tracker opening on ExtendedSpikesRange ends at loop 103. The earlier Nova and Brightwing choices still interrupt the prefix before Sonya. The new data establishes the selection and award conditional on tier availability. The original 308 synchronization records all remain to be verified for the conversion.

Run the commands with the repository and its pinned protocol modules on PYTHONPATH. HEROES41810 is the historical heroes.json, SONYA98348 the installed Barbarian XML, and COMMON_PREFIX the shared pre-award startup tracker with SHA-256 `1073a5bdbffca7d6c50fd4ffe7dcedfe150ea4d2ba4152b4db7b04b357259d86`. CONTROLS is a private JSON list of pairs of local replay path and SHA-256. The verifier requires the recorded War Paint witness and coverage of all three target columns. Each output directory must be new.

```text
python warpaint_control.py NGS_WAR_PAINT_REPLAY SONYA98348
python join_war_paint.py TEN HEROES41810 SONYA98348 MERC_MAP GAMELIB COMMON_PREFIX CONTROLS MERC_GAME_DIR MERC_GAME_RECEIPT NEW_MERC_DIR --tracker-base MERC_AWARDS_DIR
python join_war_paint.py TEN HEROES41810 SONYA98348 EXTENDED_MAP GAMELIB COMMON_PREFIX CONTROLS EXTENDED_GAME_DIR EXTENDED_GAME_RECEIPT NEW_EXTENDED_DIR
```
