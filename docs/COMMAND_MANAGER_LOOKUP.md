# Command objects in build 98348

An issued command can create the per-user object that later updates address. The listener at RVA `0xb58e70` dispatches event 27 to `0xb60920`. Its descriptor copies the event's sequence at `+0x6c` into `+0x48`. The issuer passes that key to `0x2031640`, which searches the user's list of 16-byte entries, reuses a matching object's `+0x50` key, or asks the manager to create and append an entry. The issuer then calls object method `+0x28` with argument 1.

Events 103, 104 and 105 all call `0x2031bf0` after checking the manager. It returns the first matching object or null. When that lookup fails the corresponding handler skips the object action. Events 104 and 105 pass a reconstructed target to method `+0x30`. Event 103 invokes method `+0x28` with 0 for state 0, with 1 then 0 for state 1, and with 1 for state 2. The latter two states have native behavior even though all 24 target recordings used state 0. The ID103 producer can emit states 1 and 2 when its owner and descriptor predicates pass. In that branch one flag bit chooses the state.

| Explicit sequence compared to all issue events for the same user | TEN build 41810 | 24 target recordings |
| --- | ---: | ---: |
| Point update with unique preceding issue | 0 of 10,890 | 1,102,280 of 1,102,280 |
| Unit update with unique preceding issue | 0 of 4,579 | 4,194 of 4,194 |
| Manager transition with unique preceding issue | 0 of 16,434 | 621,682 of 621,686 |

Among target manager transitions, two records have no recorded issuer and two refer to a key issued multiple times. In TEN, 13 point updates, 26 unit updates and 40 manager transitions use a key that occurs in a later issue. All other explicit keys in those rows have no recorded issue. An update with a historical number alone therefore supplies no evidence that the corresponding target command object exists. Other creation paths and event ordering still require reconstruction. [Cross-build counts](../observations/command-sequence-lookup.json)

Run `python verify_command_manager.py EXE STATIC_TEXT` to verify the PE listener pointer, registration, jump tables, field offsets, conditional branches and call targets. Run `python compare_command_sequences.py TEN CONTROL_PATHS_JSON` to reproduce the table. Both tools read their inputs offline.
