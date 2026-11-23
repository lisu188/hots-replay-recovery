# Known bits in the fourth fast-sync operand

After normal setup applies TEN's recorded user options, `u32(world+4) & 0x1f8 == 0`. This follows from six options for all ten actual TEN users. The same six bits were false in all 254 opening option records from 24 other build-98348 matches.

| Bit in `world+4` | Type-7 field | Native setter RVA |
| --- | --- | --- |
| 3 | `m_developmentCheatsEnabled` | `0x97a970` |
| 4 | `m_testCheatsEnabled` | `0x97aa60` |
| 5 | `m_multiplayerCheatsEnabled` | `0x97a9c0` |
| 6 | `m_syncChecksummingEnabled` | `0x97aa10` |
| 7 | `m_isMapToMapTransition` | `0x986070` |
| 8 | `m_debugPauseEnabled` | `0x97a920` |

The receiver maintains six 16-bit user masks at offsets `+44h` through `+4eh`. The aggregate checks each active user's bit. A missing user bit on these inputs takes the clear branch even for options whose enabling paths have additional predicates. All six setters act on the same DWORD consumed by the fast CRC. The bit-7 setter also has a distinct Galaxy caller, native 740 `GameSetTransitionMap`.

The recorded event fields establish these six bits after option application. The full flags value and the sample at loop 64 still depend on other native writers and timing. The verifier leaves the sampled value open. No checksum words from controls enter the calculation.

Run `python verify_world_startup_flags.py ORIGINAL_EXE STATIC_TEXT TEN_REPLAY CONTROL_PATHS_JSON` with the repository modules on the Python path.
