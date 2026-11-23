# Follow-ups to TEN's 68 recovered commands

The 51 point casts and 17 commands directed at moving heroes add zero verified follow-up records to the existing sparse projection. All 53 point updates and 53 state transitions between one of the recovered casts and that user's next issue or reset carry a different explicit sequence.

For the 17 hero commands, the first uninterrupted part of each user's sequence through the earliest manager contains 14 unit updates, one point update and 12 state transitions. All 27 lack sequence values in the historical file and in the build-98285 partial archive. The sparse 98348 assembly omits these ordinals.

| Prior target for the same command key | First 8 physical 98348 controls | Other 16 controls |
| --- | ---: | ---: |
| Different unit | 890 | 2,029 |
| Point | 386 | 863 |
| Same tag, changed position | 6 | 20 |
| Same tag and position | 0 | 0 |

All 26 same-tag cases have a sentinel tag and target flags 175. The TEN candidates with independent same-loop positions use tracked hero tags and flags 111. Four repeat the creator's whole target, and one changes its position. Two other historical updates switch to a RangedMinion whose target allocation remains unresolved. The 4,194 physical unit-update frames reproduced 109,044 bytes with the native writer. These observations leave the corresponding semantic projection open.

Manager records also require a command key. In the 24 controls, the usual latest-issue prediction failed 70 times even with a sole state-0 record between consecutively numbered hero issues. The historical point candidate has a point update one loop after its creator followed by a same-loop state 0. Three first-eight examples of this pattern reference a different sequence for the point, and the other 16 controls contain four where the manager references a different sequence. Prior issue creation alone also leaves command-object lifetime unresolved.

Run `python creator_followups.py TEN GATEORDER_MAP SPARSE_DIRECTORY PROTECTED_R8 CONTROL_PATHS`. The checker verifies the original recording, the map, the actual sparse bytes and ordinal ledger, the protected partial archive and all 24 target references. It produces aggregate evidence and reads each input file without modification.
