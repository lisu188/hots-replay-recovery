# Tyrande's opening Seasoned Marksman

TEN user 7 plays Tyrande as player 8. Original game input 1547 at loop 364 selects index 2. Original tracker record 251 then awards `GenericTalentSeasonedMarksman` at loop 365. No item unit is born with this purchase. The receipt is `observations/seasoned-marksman-opening.json`.

## Evidence

- **41810 catalog.** The pinned export (`aaf264de…`, nydus heroesjson at `bd17236`) lists Tyrande's tier one as Celestial Attunement, Ranger's Mark, **Seasoned Marksman** and Empower. Index 2 is therefore Seasoned Marksman. Its 41810 rule reads: "For every 6 enemy Minion kills near your Hero, gain 1 Basic Attack damage. Hero Takedowns count as 3 Minion kills."
- **98348 catalog.** The 98348 shared catalog still defines `GenericTalentSeasonedMarksman`, but the 98348 Tyrande tree no longer contains it. Its tier one is TyrandeRanger, TyrandeMoonlitArrows and **TyrandeTrueshotAura** (index 2, column 3).
  - The shared talent grants a damage carry behavior, a token counter and an activatable item, and declares a 40-stack quest.
  - Its token effects add 0.2001 per minion credit and 0.5 per takedown.
  - Both files are MD5-verified extracts from the installed 98348 storage, taken before the 98785 patch.
- **Dated change.** [Blizzard's May 17, 2016 notes](https://news.blizzard.com/en-gb/article/20120032/heroes-of-the-storm-patch-notes-may-17-2016) added a reward to this questing talent, which postdates build 41810. After 40 bonus Attack Damage, it activates for 30% Attack Speed for 3 seconds, with a 60-second cooldown.

## Candidate map

`build_seasoned_marksman_map.py` derives a separate package from the combined first-talents map (`13493e67…`). It appends exactly one map-local record:

```xml
<CHero id="Tyrande"><TalentTreeArray index="2" Talent="GenericTalentSeasonedMarksman" /></CHero>
```

This relinks only tier 1, column 3.

- **Checks before building.** The builder checks:
  - the historical slot and its rule text;
  - the target row and its absence of children;
  - the shared talent's exact 98348 definition;
  - that no map-local Tyrande or Seasoned Marksman definition exists;
  - that the catalog change is a single append.
- **Result.** Only `HeroData.xml` changes. The other 72 content members, the 75 live blocks and the table checks are unchanged. Two native StormLib builds produced the identical 2,204,442-byte package `fa349ed928b649ea203133237999e8d4202a6e13b328224619eb1399cff23d6c`.
- **Behavior left unchanged.** The talent's 98348 behavior is not changed. The post-2016 reward and 40-stack completion point therefore remain in the candidate. The 41810 tooltip implies 1/6 damage per nearby minion kill against the target's 0.2001, and the exact historical stack representation is unrecovered. These differences affect later damage and stay open.

## Projection

`seasoned_marksman_opening.py` re-derives the source input and award from the original, and checks the target opening's player, hero and level. It then makes two additions.

- **Input.** It adds the translated choice to the combined sparse input stream. The parent's 17,712 rows re-encode byte-for-byte before insertion. All 17,386 later rows are camera, map or no-target pings, recorded chat, final departures, or the other Kael'thas's unchanged first purchase, so none depends on Tyrande's talent state. The new stream has 17,713 inputs (142,594 bytes, `8560be8f…`); 86,544 source inputs remain unrepresented.
- **Award.** It appends the award frame to the 272-frame prefix ending at loop 355. The result has 273 frames (16,598 bytes, `8d037868…`), and re-encoding it reproduces every byte.

Seven genuine 98348 recordings of Tyrande's stock first purchase reproduce the native frame grammar byte-for-byte (selection loop plus one, tree-resolved name): selector 0 three times, selector 1 three times, and the restored selector 2 once. A repeat run on the independently rebuilt map produced identical outputs and receipt. The next original tracker record is ordinal 252 at loop 610.

## Not established

- Native catalog loading of the candidate.
- The historical talent behavior and stack rounding.
- Later combat outcomes.
- Unit allocation, simulation and every target synchronization check.

```sh
python build_seasoned_marksman_map.py COMBINED_MAP TYRANDE_98348_XML SHARED_98348_TALENTDATA HISTORICAL_HEROES_JSON NEW_MAP --stormlib STORMLIB
python seasoned_marksman_opening.py ORIGINAL_TEN NEW_MAP TYRANDE_98348_XML PREFIX_THROUGH_355 COMBINED_GAME_DIR PRIVATE_TYRANDE_CONTROLS NEW_PRIVATE_DIRECTORY
```
