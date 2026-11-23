# Restoring Kael’thas’s Mana Addict threshold

The original match has two Kael’thas players who bought Mana Addict. Build 41810 required 25 Regeneration Globes to unlock Arcane Barrier. Blizzard later reduced the requirement to 20. The pinned 98348 hero file still declares 20. [March 2016 patch introducing the quest](https://news.blizzard.com/en-us/article/20063493/heroes-of-the-storm-patch-notes-march-29-2016) · [April balance update changing the threshold](https://news.blizzard.com/en-us/article/20102776/heroes-of-the-storm-balance-update-notes-april-27-2016)

The converter restores two fields in a separate in-memory copy of the target XML. The token counter’s greater-than-or-equal condition triggers the unlock effect. The talent’s quest target advertises the required count. Changing only the advertised count would leave the reward available at 20. In the 276,044-byte result, only offsets 93,302 and 241,028 change. The resulting SHA-256 is `8f4c47489e5dac39a364f245370c7cdddee628366333d8d76756607cdea6d1aa`. [Two-field converter](../restore_mana_addict_threshold.py) · [Change accounting](../observations/mana-addict-threshold-correction-98348.json)

The source tracker contains 220 named globe credits among 6,614 events. It distinguishes the two owners and preserves multiple credits in a single loop. Neither owner had a credited globe before purchasing the talent. Assuming one quest stack per credited globe gives the following results. [Original match trace](../observations/mana-addict-source-windows-41810.json)

| Purchase loop | Subsequent credits | Reaches 20 | Reaches 25 |
| ---: | ---: | ---: | ---: |
| 355 | 21 | 18032 | Never in the recorded credits |
| 1217 | 39 | 9704 | 11332 |

For the second player the original threshold delays eligibility by 1,628 loops on this sequence. Feeding the corrected XML threshold back into the projection removes both early unlocks. In 98348 a qualifying globe impact increments the talented recipient’s token by one. The same impact also increments the owner’s globe score. The 41810 tracker records globe credits but supplies no direct token counts or shield activations. The change produces a standalone catalog member. Integration into the resolved map catalog and full-match simulation remain open. [Target effect and scoreboard bindings](../observations/mana-addict-credit-basis-98348.json)

Run these commands with the preserved source replay, the build-41810 community hero export and the pinned 98348 `KaelthasData.xml`. The first command uses the Python standard library and emits a JSON receipt. Its `--emit-xml` option writes the corrected bytes to standard output. The second uses the repository’s replay decoder. [Tracker projection](../trace_mana_addict.py) · [Historical hero catalog](https://github.com/nydus/heroesjson/blob/bd1723601cc1a7c05e9417bf76b7fe10297e7ba8/heroes.json)

```text
python -B restore_mana_addict_threshold.py --target-xml KaelthasData.xml --historical-catalog heroes.json
python -B trace_mana_addict.py --source TEN_GREYMANE_source_41810.StormReplay --catalog heroes.json --hero-xml KaelthasData.xml
```
