# Dragon Shire defender lifetimes in build 41810

The offline model predicts 162 neutral defender births, including 98 returned defenders in 34 later camp waves. Every predicted loop, camp, unit type and integer X/Y matches its recording. Removing all neutral defender birth records before generating the prediction leaves the result unchanged. The thresholds were fixed on TEN_GREYMANE before scoring the three other recordings.

| Recording | Initial defenders | Later waves | Returned defenders | Waves delayed by Dragon Knight | Observed neutral deaths |
| --- | ---: | ---: | ---: | ---: | ---: |
| TEN_GREYMANE | 16 | 10 | 30 | 4 | 38 |
| Control 7efa1c33 | 16 | 16 | 48 | 5 | 48 |
| Control 2fca3c78 | 16 | 4 | 12 | 0 | 18 |
| Control 8c4fb839 | 16 | 4 | 8 | 0 | 8 |

The first wave appears 1,922 loops after the gates open. A later capture is predicted one loop after its capture beacon changes to team ownership. The timer becomes ready 2,832 loops after a siege capture or 3,792 after a knight capture. Under ordinary conditions the neutral defenders appear two loops after that deadline. If the Dragon Knight is active at the ready deadline, the model waits for the active vehicle's death and emits the wave three loops later. The initial wave has its own timing, including when a Dragon Knight is already active.

Ignoring the Dragon Knight gives 24 false and 24 missed unit births across these four games. The full rule gives zero of each. The host supplies `DragonKnightActivated` and the death of that specific `VehicleDragon`. The map supplies each camp's defender slots. These data do not establish how the original engine handles a Dragon Knight transition on the exact timer-ready loop, a shortened cooldown, or different maps and builds.

The separate lifetime check binds each defender's observed tag and recycle at birth to an authored slot. Its recorded death removes that slot from the active group. In all 39 captures every slot had already died. The 112 deaths and the exact surviving slots at each replay end agree with the state model. Individual combat-death times remain observed inputs. Timers that extend beyond the replay header's elapsed loops are censored.

For diagnostic runs that omit combat deaths, `WaveClock.event` still starts the cooldown on a capture signal. It records `capture_without_complete_observed_defeat` if any prior defender slot is still alive. A respawn emitted after such a fault is a conditional forecast from the supplied capture. All four complete inputs had zero state faults.

The independent prefix check erases every neutral defender birth and every capture statistic, discards all remaining inputs from the assessed loop onward, and advances the model to that loop. It recovers all 54 initial and returning camp waves. Separately, each camp's unique authored `CampOwnershipFlag` changes to hostile ownership exactly two loops before every one of those waves, with zero extra transitions. The prefix checker scores all observed and forecast wave times and saves the per-recording counts in `legacy-wave-prefix-check.json`.

## Reproduction

With the recovery repository and pinned Blizzard protocol dependency on `PYTHONPATH`, run

```text
python -B legacy_camp_wave_model.py --map ORIGINAL_MAP --replay TEN_GREYMANE CONTROL_3 CONTROL_4 CONTROL_5 --output legacy-camp-wave-lifetimes.json
python -B -m unittest test_legacy_camp_wave_model
python -B check_wave_prefixes.py --map ORIGINAL_MAP --replay TEN_GREYMANE CONTROL_3 CONTROL_4 CONTROL_5 --output legacy-wave-prefix-check.json
```

The output contains aggregate scores and file digests. The module also exposes `WaveClock.event` for chronological gate, capture, neutral-death, and Dragon Knight signals, and `WaveClock.advance` to emit waves due through a specified game loop.
