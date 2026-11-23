# Command sequence numbers in TEN_GREYMANE

The build-41810 updater and its command manager sometimes record the same optional sequence twice. For a point or unit target update, inspect the next command-related event from the same wire user. If it is a manager record on the same loop in state 0, 1 or 2, its optional sequence reconstructs the update field. The predictor returns an entry for a witnessed absence and omits an ordinal when it lacks a companion. Reset, issue and intervening target updates terminate the pairing.

| Build and sample | Paired updates | Exact optional fields | Updates without a companion |
| --- | ---: | ---: | ---: |
| 41810, TEN_GREYMANE | 24,019 | 24,019 | 19,740 |
| 41810, three independent controls | 73,887 | 73,887 | 87,654 |
| 98348, fourteen independent recordings | 117,047 | 116,374 | 484,449 |

For the four historical recordings the verifier removes every target-update sequence, derives the paired values from manager records, retains the source value for each unresolved ordinal, then reproduces each complete game member byte for byte. In TEN_GREYMANE this recovers all 15,469 nonempty target-update sequences and 8,550 encoded absences. In two other historical recordings, 24 point updates carry an explicit sequence without an eligible manager companion. Inferring absence for every unpaired update would lose those values.

All 601,496 target updates in the 98348 samples carry a sequence. Applying the historical pairing to those controls would assign a wrong number to 673 updates. The current checker scores the prediction and uses original values to confirm the contemporary codec round trip. The destination sequence for a converted historical command still needs the current command producer.

Run `python legacy_command_sequences.py REPLAY --sha256 DIGEST --build 41810` with the repository's pinned protocol dependencies. Use build 98348 for a contemporary control. The [per-recording comparison](../observations/legacy-command-sequences.json) includes input hashes, manager states and counts of matched and unresolved fields.
