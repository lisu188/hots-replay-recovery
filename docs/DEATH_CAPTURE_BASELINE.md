# Camp timing predicted from the last defender death

The build-41810 baseline predicts capture 25 loops after the last living authored defender slot dies and assigns it to the credited killer’s team. This gives the right camp and team for all 39 captures in four Dragon Shire replays. It gives the exact capture loop for 27. The other 12 forecasts are 2–15 loops early.

| Replay | Exact capture loops | Correct camp and team | Exact later neutral waves | Exact individual return births |
| --- | ---: | ---: | ---: | ---: |
| TEN_GREYMANE | 11/13 | 13/13 | 10/10 | 30/30 |
| Control `7efa1c33` | 12/16 | 16/16 | 12/16 | 34/48 |
| Control `2fca3c78` | 3/6 | 6/6 | 2/4 | 4/12 |
| Control `8c4fb839` | 1/4 | 4/4 | 1/4 | 2/8 |
| Total | 27/39 | 39/39 | 25/34 | 70/98 |

The forecast starts each camp’s `WaveClock` cooldown from its predicted capture. Nine early capture predictions made the next observed wave early by exactly the same number of loops. The other three early predictions had no subsequent return within the replay horizon, including both early predictions in TEN_GREYMANE. All 64 first-wave unit births matched. Together the initial and later waves give 134/162 exact neutral birth tuples (loop, camp, unit type and position).

Inputs are the authored neutral slots, the recorded gate opening, observed neutral tags/deaths and killer player IDs, player teams, and Dragon Knight activation and death. Neutral birth records bind each observed death to a named slot. Only the observed deaths drive elimination. The model withholds every capture statistic, ownership change and allied mercenary birth from scheduling. Removing those records before prediction left the driver streams identical for all four cases. Exact tuples and downstream births are scored afterward against their separate recorded outcomes.

The 25 loops combine the shortest observed 24-loop delay to beacon ownership and the one-loop delay from ownership to the capture statistic. Arena occupancy, contested progress, and individual combat-death generation are unresolved. The four recordings establish a baseline and its measured timing errors.

```sh
python death_capture_baseline.py --map original-41810-dragonshire.s2ma \
  --replays TEN_GREYMANE.StormReplay control1.StormReplay control2.StormReplay control3.StormReplay
python -m unittest test_death_capture_baseline
```

The CLI writes aggregate JSON to standard output. It requires the recovery repository’s camp-wave clock, map-slot verifier and replay codec modules on `PYTHONPATH`.
