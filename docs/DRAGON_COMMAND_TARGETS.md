# Dragon Shire command targets

The authored transfer plan predicts 1,279 target tags among 12,465 original TEN_GREYMANE target commands. It reads the original replay and the two stock map archives. It joins unique placements by numeric object ID, unit type and exact decimal X/Y, then assigns the destination's zero-based rank in numeric object-ID order. Initial recycle 1 comes from the established startup rule for these builds. Each accepted source command falls strictly inside the original object's first lifetime and its raw snapshot X/Y equals the placement times 4,096.

All 997 earlier integer-coordinate projections agree. The 282 additional targets comprise 212 healing-well commands and 70 wall commands. Ranks change in 1,222 fields and packed tags change in 1,275. The inverse mapping restores all 1,146,911 original game-member bytes. The source tracker and XML agree on all 165 authored startup owner pairs. For all accepted commands the recorded pair still equals the authored pair before any source owner transition, and the target map specifies the same pair. Future target ownership, lifetimes and deterministic playback of this historical match remain open.

## Blind validation of the 92 integer-coordinate placements

The predictor withholds the actual command tag. It uses the exact snapshot X/Y, an unambiguous loop-zero placement, the first-lifetime bounds in that recording, and an observed command flags value. The XML placement supplies the index. The blind-control checker validates that index against a separate startup event and takes its initial recycle. The authored transfer plan uses its fixed startup rule and requires no target replay.

| Stock 98348 sample | All target commands | Predicted tags | Wrong tags | True anchor targets missed | Whole game members byte-equal |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12 recordings, training on the other 11 | 69,274 | 4,489 | 0 | 0 | 12/12 |
| Two newly downloaded recordings | 13,107 | 954 | 0 | 0 | 2/2 |

Exact X/Y without the flag check produces 166 false positives in the twelve recordings and another 26 in the two new recordings. The discovery run prompted examination of `m_targetUnitFlags`. Every training fold retained only the full integer value 111. Each retained value had to appear with non-sentinel tags in at least two other recordings and have zero sentinel observations across the training recordings. The subsequent replication fixed 111 before downloading either new replay. Selection used the first two new public NGS Dragon Shire keys ordered by date and key on or after October 17, 2026. Both were October 20 games with authentic build, root, map and mod identifiers. The game-member comparison re-encodes every event after replacing the predicted fields; other commands retain their original data.

The follow-up on these same two recordings extends the test to all 118 authored placements shared by the maps. It adds 154 and 59 correct fractional-position predictions to the 954 integer-position cases. All 1,167 predicted tags and both authored owner fields match the recorded commands, and both full game members re-encode byte-for-byte. The checker abstains on ambiguous placement bounds and on the full tracker-coordinate tile of any startup unit it could not identify from XML.

## Reproduce offline

Use Python 3.11 with the repository root, the pinned Blizzard heroprotocol checkout and `six` on `PYTHONPATH`. The authored planner additionally imports the sibling `map_startup_identity.py` module. The game archives are read-only inputs. Supply the 12 originals in the paths recorded relative to the control root in the public roster. For the independent run, place the two public downloads under lowercase SHA-256 filenames with the `.StormReplay` extension. Their URLs and digests appear in the independent receipt.

```text
python -B check_blind_target_tags.py --anchors observations/dragonshire-common-anchors.json --roster observations/expanded-current-catalog-comparison-2026-10-18.json --control-root CONTROL_ROOT --output new-blind.json --compact-output new-compact.json
python -B replicate_control_tags.py --anchors observations/dragonshire-common-anchors.json --roster observations/expanded-current-catalog-comparison-2026-10-18.json --control-root EXTERNAL_ROOT --selection observations/dragonshire-independent-control-tags.json --output new-independent.json
python -B check_fractional_controls.py --source-map SOURCE_MAP --target-map TARGET_MAP --control-root EXTERNAL_ROOT --selection observations/dragonshire-independent-control-tags.json --output new-fractional.json
python -B plan_authored_targets.py --source SOURCE_REPLAY --source-map SOURCE_MAP --target-map TARGET_MAP --output-dir PLAN_OUTPUT
python -B -m unittest discover -s . -p "test_*.py"
```

The planner outputs zero-based ordinals and an aggregate receipt. The optional `--compare-prior` argument accepts the integer-only ordinal table and checks every previous projection. Regenerating the blind reports with equal outputs is permitted. A differing existing report makes the checker stop.
