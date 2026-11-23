# Full-length R8 archive with repaired command sequences

The generated private archive retains build 98285 and all 104,257 game records. Compared to the protected selection-link draft, it fills 688 omitted point-update sequences and 20 omitted state-0 manager sequences. The complete 4,214,430-byte archive has SHA-256 `50328fad2a8e7808b978ace43e30a49ba175515998c83887a93305ca63e5af8d`.

The builder takes the union of original-ordinal predictions from the published opening-session, immediate-update and command-interval rules. It evaluates the same histories independently on the selected R8 archive, requires agreement on the enclosing player, loop, command and point or manager state, and requires exactly one preceding R8 issue from that user with the predicted number. All 708 candidates pass. In two genuine recordings of build 98285, the rules reproduced all 1,302 qualifying physical frames, totaling 18,339 bytes. The short second control supplied four opening-session examples. The first control supplied examples of all three rules.

For every admitted frame, the optional sequence expands the encoding by four bytes. Every other physical game frame is byte-identical to its parent. Both MPQ readers agree on every active member and the native integrity checks pass. The archive replacement regenerates MPQ `(attributes)`. Twelve other members, including the historical tracker, camera and all 308 synchronization records, match the protected parent byte-for-byte. The original TEN replay and protected selection draft retain their pinned hashes.

Two independent complete archive builds produced identical files. The artifact remains a partial build-98285 replay. Target simulation state, the unresolved command creators and successful playback remain open.

Run the builder with the recovery repository and its dependencies on the Python import path and a compatible StormLib library:

```text
python repair_r8_command_sequences.py TEN_41810 SELECTION_DRAFT NEW_OUTPUT --control FIRST_98285 --control SECOND_98285 --stormlib STORMLIB
```
