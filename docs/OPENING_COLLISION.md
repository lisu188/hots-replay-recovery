# Dragon Shire opening collision

Descriptor bit 28 is zero for all 172 opening slots on the recorded-type, live-radius branch when any collision overrides come from the registered behavior modifiers and unmodified catalogs. The projected ledger resolves 94 of 96 bits on that branch. Bits 29 and 31 still depend on instance state. [Per-type results](../observations/opening-collision.json)

The descriptor reads the effective mask as `(Collide | unit[0x2e4]) & ~unit[0x2e8]`. It sets bit 28 if the high byte is nonzero and the low 24 bits are zero. The build-98348 enum assigns bits 24–31 to flying categories. CUnit's per-player constructor clears the catalog mask at offset 0x48. Both instance override fields also start at zero. Resolving the recorded types against Core, HeroesData and GateOrder yielded the following counts. The full installed package superset gave the same values.

| CUnit base mask | Slots |
| --- | ---: |
| 0 | 28 |
| 2 | 2 |
| 16 | 1 |
| 32 | 87 |
| 35 | 54 |

## Override sources

The native modification constructor binding at RVA 0x440C13 invokes 0x607260, which zeroes the eight bytes at 0x15B0 covering both collision masks. A nonempty enable or disable field invokes the collision update at 0xA97DE6. The worker starts the two result words at zero and dispatches modifier category 5 through the behavior list's virtual slot 0x160. At 0xA97E35 it writes both results to the live unit. The catalog aggregation at 0xA9A35D independently ORs the enable and disable masks.

The ordinary provider registration routine at 0xB1D4F0 installs classes 1–17 in a single table. Their slot 0x160 entries point to seven distinct functions. Five implementations handle other categories or delegate to the base implementation, which handles category zero. For category 5 the two remaining classes, 3 and 12, use the catalog aggregation. The class 3 switch at 0xC17D7F falls through its default path for category 5. Class 12 calls the same aggregator at 0xBFE92E. The registration and switch targets are checked against the pinned image.

Two local scans verified each of the 5,575 installed XML files against its independent SHA-256 and byte count. One examined the decoded bytes, the other the parsed XML. Both found the same 12 members, with 48 explicit disable entries and zero enable entries. The GateOrder map adds neither field. This eliminates an air-bit addition through ordinary authored modifiers even if unknown modifiers are active. Any combination of low enables and arbitrary disables leaves all 172 base masks without a high bit. Positive controls include a Medivac with only the flying bit and a Mutalisk with both flying and ground-category bits.

This result covers the identified catalog and modifier path. A runtime edit to the selected catalog row or an independent producer of high enable bits would require separate evidence. The recordings do not contain the physical descriptor and the result does not determine the sync CRC. The independent comparison checks that the 172 values and all unrelated fields are identical, with only bit 28 added to each mask. [Differential](../observations/opening-collision-check.json)

```text
python opening_collision.py EXE TEXT PROJECTION UNIT_XML MODIFIER_XML GATEORDER_MAP OPENING_BIRTHS BASELINE_93 --private-output NEW_PRIVATE_94
python check_opening_collision.py BASELINE_93 NEW_PRIVATE_94
```

The two XML arguments accept the complete projection directory or the respective pinned private subsets. The baseline is the recorded-type 93-bit ledger. The generator emits the public aggregate receipt on stdout.
