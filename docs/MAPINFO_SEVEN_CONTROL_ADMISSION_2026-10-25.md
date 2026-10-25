# Exact seven-record MapInfo control admission — 2026-10-25

The strict MapInfo framing converter now admits one additional, exact battlelobby member from an independently acquired build-41810 control. Admission requires its complete SHA-256 and all seven saved record spans. The three earlier source tuples remain unchanged. The limit becomes seven records; the same explicit profile now lists four source members and 23 record spans.

This extends the data-specific [empty-count framing converter](LEGACY_MAPINFO_FRAMING_2026-10-20.md). It preserves the current [native MapInfo schema](NATIVE_MAPINFO_2026-10-19.md), its 191 reachable types, and the 32 named fields of root 5852. The sole legacy schema hypothesis remains type 1828 with a 7-bit count instead of the current 31-bit count. Every admitted legacy count must equal zero. Nonempty permissions remain unsupported; no element values or defaults are inserted.

The control came from the [Inven source post](https://www.inven.co.kr/board/hos/4200/2520?category=%EC%82%AC%EA%B1%B4&my=opi&p=3) and its fixed [ZIP attachment](https://upload2.inven.co.kr/upload/2016/04/12/bbs/c13569754257.zip). The acquired replay has 774,134 bytes and SHA-256 `3a33d012a9d47dc1e66595398c2f3dd75cbc9240762996cf52c9c6ad8337e869`. Its battlelobby member has 43,534 bytes and SHA-256 `9536a8f9204fa141ae71a8a25a5f207030165611328579a1daefb747f326cb56`. Neither payload is included in this source milestone.

The new source ID is `public41810control`. Record spans use physical bit offsets with exclusive ends; each permission-count span ends at the record end.

| Record | Source start | Source end | Empty 7-bit count start |
| --- | ---: | ---: | ---: |
| 0 | 215435 | 216696 | 216689 |
| 1 | 216696 | 218336 | 218329 |
| 2 | 218336 | 219624 | 219617 |
| 3 | 219624 | 221814 | 221807 |
| 4 | 221814 | 223622 | 223615 |
| 5 | 223622 | 225430 | 225423 |
| 6 | 225430 | 227810 | 227803 |

The guarded actual-control check used the staged production API, with admission enabled solely by the added tuple. `convert_mapinfo_framing(raw, PROFILE)` produced a private RAM member of 43,555 bytes: seven 24-bit count expansions add 168 bits, or 21 bytes. Its SHA-256 is `2c770fb59f7a64734752b10858de4746af270a63b1ebfa1b02e6094c493a9e6f`. All 224 root-field comparisons and 1,816 comparisons across all native fields passed. Current record boundaries, values, and read-only reencoding matched; every non-count token and outside bit remained exact. `inverse_mapinfo_framing(value, PROFILE)` reproduced the entire original member byte for byte. The temporary converted member was not written to disk.

The baseline module's strict refusal of this source was reproduced before testing the new admission. A one-byte mutation and a mutation making one permission count nonzero were both refused by the whole-member digest before schema or framing work. Existing synthetic tests separately continue to reject nonempty counts even under test-only digest admission. There is no admission for the build-42273 control.

Focused validation ran 38 tests from the existing framing and native-MapInfo modules plus two new synthetic boundary tests, with zero failures, errors, or skips. The new tests check seven-record bit preservation and inverse, and refusal of eight records even under test-only admission. The existing offline runner discovers root `test_*.py` modules, so no workflow change is needed. This records local validation; exact-head remote CI remains unverified for this change.

The module delta is restricted to the fourth tuple, `MAX_RECORDS=7`, and the admission-count docstring. An AST comparison verifies that the first three tuples, profile identifier, baseline receipt constant, and all remaining code are unchanged. The earlier private seven-record candidate proof is pinned separately rather than replacing the original baseline constant.

This verifies a reversible framing conversion for one precisely identified member. It does not authenticate the complete historical schema, supply historical ClientInfo values, convert another replay stream, establish current-client compatibility, or demonstrate playback. The converter API still returns private RAM bytes and provides no replay/header/body file writer.
