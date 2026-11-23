# Dragon Shire camp captures on build 41810

After matching each initial camp beacon to its map point, a transition to owner pair (11, 11) predicts a team-1 capture on the next loop. A transition to (12, 12) predicts a team-2 capture on the next loop. Only the beacon identities and their recorded ownership transitions enter the prediction. The checker reveals the capture stats, flag owners, minimap icon owners and allied-unit births afterward.

The rule accounted for all 13 captures in TEN_GREYMANE. Frozen before testing three further matches on the identical 41810 map, it accounted for 16, 6 and 4 additional captures. All 39 predictions matched the recorded loop, camp and team. Each had an independent matching flag, icon and complete mercenary wave. There were 112 allied mercenary births across the four matches. Predicting the capture on the beacon's transition loop gave zero matches.

The three additional matches also reproduced the 172 startup births and all sixteen defenders at their authored positions at loop 2532. Each has a different replay, tracker and game-event digest. [Capture comparisons](../observations/dragonshire-legacy-camp-captures.json) · [Independent build-41810 startup and first-wave checks](../observations/dragonshire-41810-camp-controls.json)

```sh
python predict_camp_captures.py --map original.s2ma \
  --replay TEN_GREYMANE.StormReplay control1.StormReplay control2.StormReplay control3.StormReplay \
  --output camp-captures.json
```

These checks establish observable requirements for the historical-layout simulator. To predict captures from player commands alone, the simulator still needs the logic that changes the beacon owner, including defender deaths and capture-point eligibility.
