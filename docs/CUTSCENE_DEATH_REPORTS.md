# EndSceneFired and hero deaths on Dragon Shire

In TEN, **all 121 EndSceneFired reports come from the player who just died**. They cover all 47 recorded deaths. Fifteen genuine build-98348 Dragon Shire controls use a different number and a different schedule. Substituting the retail number would incorrectly attribute 93 delayed TEN reports to a pattern absent from the controls. The present evidence admits zero converted event-98 inputs. [Replay counts](../observations/cutscene-death-reports.json)

| Evidence | TEN, build 41810 | Dragon Shire controls, build 98348 |
| --- | ---: | ---: |
| Matches | 1 | 15 |
| Victim deaths | 47 | 326 |
| Physical reports and unique handle | 121 using 131196 | 209 using 131187 |
| Reports 1–3 loops after that player's death | 28 | 2 |
| Reports 88–94 loops after that player's death | 93 | 0 |
| Distinct deaths with any report within 96 loops | 47 | 7 |

The source-side comparison uses the affected player's tracker setup and game-event user. Within the same 96-loop window only eight reports follow that player's regeneration-globe pickup, two follow a talent choice and 16 follow credited participation in somebody else's death. Other 41810 controls have additional handles and timings. The two windows characterize this recording.

## Where the number comes from

Both native emitters at `1F376F9` and `1F381C1` pass the 32-bit value from scene instance `+28` to `203EBD0`. Both skip the local-frame namespace `0x30000`. The submission helper copies its argument unchanged into event offset `+30`. A fresh UI frame gets `0x30000 | low16(local counter)`. Attaching a supported Galaxy control writes `0x20000 | low16(control ID)` to frame `+1F8` and updates any existing scene instance. The constructor for a new instance takes the same ID from its creation request. [Native verification](../observations/cutscene-control-98348.json)

The next Galaxy control ID lives at RVA `2F6FBC4`. A successful child lookup can return an existing control for the same canonical path. A miss consumes the next ID before initialization is tested. The standard-path hookup and other creation routines use the same counter. Main dialogs have a separate counter at `2F6FBC0`. The last control visible to Galaxy comes from the returned object's `+10` field and the per-context `+44` slot.

Before hooking the death overlay, five synchronous UI initialization triggers perform 9, 23, 19, 4 and 6 hookup calls, respectively. The on-fire portrait frame is call 47, the special fullscreen overlay is call 60 and the death overlay is call 61. On an uninterrupted sequence of 61 previously unseen, successful control creations, the last would take the entering next ID plus 60. Other initialization occurs earlier, including camp beacon status-bar hookups. Older and adapted camp code also differ in the timing of their camp-panel creation. The complete entering counter, cache hits and failures for the adapted match are unresolved. Event 55 exposes historical control 125 and retail Dragon controls 61, 96 and 97 below 160. Those report numeric IDs without frame names.

## Restored map and UI behavior

The signed adapted map includes no layout or cutscene asset override. Its script does not explicitly alter the death overlay. The 98348 GameLib shows the overlay for the victim. The helper checks for a custom-death behavior first. UILib hooks `DeathOverlayCutscene`, which the Core layout binds to `Cutscenes/GameUI_DeathOverlay.StormCutscene`. Its start animation seeks the Start bookmark. The scene's Loop End jumps to Loop Start, its Death End pauses, and its End Scene Markers node contains zero elements. Native scene-ending callbacks can still run through other paths.

Timing supports a death-related origin for the historical reports. Exact attribution to the historical overlay still requires a matching 41810 asset or equivalent producer evidence. Recovering the target control ID alone would not establish the historical two-window behavior on the adapted UI. A faithful UI change would need the original start, stop, pause and reporting behavior, with the two target emitters taken into account.

## Dialog state in the synchronization vector

The full primary builder seeds scratch to `0xffffffff` at `970E2E`, calls `9F25A0`, complements the result, then stores at entry `+F0`. The counted vector starts at entry `+8`, so this is slot 58. The prefix is 12 little-endian DWORDs in order, from RVAs `2F6FBC0`, `2F6FBC4`, `2F6FBC8`, then `2F6FBE0` through `2F6FC00` in increments of four. The verifier compares the actual native CRC tables with zlib on three inputs. After that prefix the producer follows the tagged list at `2F6FBD8` and calls `9F1600` for each resolved node.

Fresh initialization `97BAD4 → 9F4BF0` sets both counters to one and all ten remaining prefix DWORDs to zero. The cleanup path `9871AF → 9F57F0` resets both counters. Reading saved state can replace the control counter at `9F29CB`. The receipt's CRC of pristine prefix bytes applies before any linked-node contribution. Under fast mode 4 with world bit 6 clear, slot 58 is zero. Full and deferred modes can include live dialog data. TEN's folded loop-64 record does not expose which history entry was published or the slot value. [History cadence](SYNC_HISTORY_CADENCE.md)

## Reproduce

The manifest uses the same 29 pinned build and SHA-256 pairs as the opening sound checks. The native verifier takes the installed UILib and GameLib scripts, the Core fullscreen layout, the HeroesData death-overlay asset and the signed adapted map. The commands produce aggregate JSON.

```text
python cutscene_death_reports.py REPLAY_MANIFEST --workers 3
python verify_cutscene_control.py EXE STATIC_TEXT SCRIPT_DIR FULLSCREEN_LAYOUT DEATH_CUTSCENE SIGNED_MAP
```
