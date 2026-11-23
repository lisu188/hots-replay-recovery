# Do equal bracketing commands predict a 98348 update sequence?

Among 601,496 target updates in 14 build-98348 replays, 192 had an immediately preceding issued command and immediately following command-manager state for the same user in the same game loop, with equal numeric sequences in those two records. The shared value predicted 177 updates correctly and missed 15. All 192 following manager records had state 0. At loop 9486 of replay `882f4895…`, both bracketing sequences were 820 and the recorded point update was 822.

| Numeric predictor | Eligible current updates | Exact |
| --- | ---: | ---: |
| Equal, adjacent issue and manager | 192 | 177 |
| Nearest issue and manager agree, allowing intervening command records | 236 | 221 |
| Nearest issue and manager disagree, use the issue value | 20 | 1 |
| Same 20 disagreements, use the manager value | 20 | 19 |

The comparison removed each update’s own sequence before selecting candidates. It counted every point and unit update. Adjacency considers reset, issue, manager, point-update and unit-update events for one user. The nearest alternative permits other command events, including resets, between its anchors. Equal brackets cover about 0.032% of current updates under the adjacent rule. In four 41810 recordings, none of the 205,300 updates had equal numeric brackets. These results establish counterexamples to substituting a bracket value for an arbitrary modern target-update sequence.

Run `score_sequence_brackets.py --manifest legacy-command-sequences.json REPLAY ...` with all 18 physical replay files from that manifest. The script matches files by SHA-256 and emits compact aggregate JSON to standard output, including the first adjacent counterexample encountered in manifest order.
