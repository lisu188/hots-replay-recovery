# Joining the gate opening to the continuous tracker

With Tyrande's award at loop 365, the continuous TEN prefix reaches original tracker ordinal 251. The next original records, ordinals 252–316, all fall at loop 610:
- `GatesOpen`;
- ten per-player `GatesAreOpen` upgrades;
- 54 gate-blocker removals.

The sparse MercCapture tracker (`assemble_signed_tracker.py`, documented in `SIGNED_TRACKER.md`) already projects this block from the recorded gate clock and the ordered blocker placements. `join_sparse_tracker_range.py` appends that block to the prefix. The receipt is `observations/gate-opening-join.json`.

## Checks

- **Map dependence.**
  - The candidate package `fa349ed9…` differs from MercCapture `54e1a8fb…` only by appended talent-catalog records (92 records across six catalog members) and appended localized text.
  - No existing record changes.
  - The map script, unit data, placements and the other 65 members are identical.
- **Ledger.**
  - The sparse ledger maps source ordinals 252–316 to consecutive target frames 267–331, all produced by `gates_open`, `GatesAreOpen` or `gate_blocker_removal`.
  - The prefix's last frame equals original record 251, so the block starts exactly where the prefix ends.
- **Source agreement.**
  - Every target frame equals its original record field by field, with one exception.
  - For each of the 54 blocker deaths, the target writes killer player 0 where the historical file omitted the value, as documented by the blocker-death reconstruction.
- **Physical bytes.**
  - The joined stream re-encodes byte-for-byte.
  - All frames after the first are byte-identical to the sparse fragment's physical frames; only the first frame's clock delta is recomputed from loop 365.

The new private prefix has 338 frames (18,753 bytes, `acfb5db5…`). A repeat run produced the identical file and receipt. The next original record is ordinal 317 at loop 682: Abathur's first talent purchase, `AbathurMasteryEnvenomedNestsToxicNest`. It is followed by ten `MinionsAreSpawning` upgrades at loop 690 and the first-wave births at loop 691, which need verified tag allocation.

The join adds no new semantic projection. The gate clock, retirement order, simulation and every target synchronization check remain under the conditions stated for the sparse tracker.

```sh
python join_sparse_tracker_range.py ORIGINAL_TEN PREFIX_THROUGH_365 MERC_AWARDS_PRIVATE_DIRECTORY MERC_CAPTURE_MAP SEASONED_MARKSMAN_MAP NEW_PREFIX
```
