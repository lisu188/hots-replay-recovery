# Opening spatial descriptor bit 30

In build 98348, bit 30 records the selected unit type's `FlagArray[Missile]`. All 45 types assigned to the 172 GateOrder opening slots resolve to zero. On the branch where the selected type is the recorded birth type and the live catalog radius applies, the descriptor ledger now determines 93 of 96 bits for every slot. Bits 28, 29 and 31 still depend on other state. [Catalog results](../observations/opening-missile-flag.json)

## Native field and default

The PE's 71-entry flag enumeration puts `Missile` at index 19. RVA `B0AE41` registers the Galaxy constant `c_unitFlagMissile` as 19 and the adjacent name as `Missile`. Galaxy dispatch arm 1671 calls `205AEB0` for `UnitTypeTestFlag`. Its indexed test uses shared record offset `DC + (i >> 3)` and mask `1 << (i & 7)`. Index 19 gives byte `DE` and mask 8, exactly the operand at `9A88AA` that sets descriptor bit 30.

The CUnit reflection record registers a nine-byte `FlagArray` at offset `4C`. The shared CUnit constructor applies `617F10` at shared base `+90`, zeroing those nine bytes. The CUnit copy path at `587F17` calls `58BD30` with both shared subrecords. Its eight-byte copy at `58BDA4` and one-byte copy at `58BDAE` preserve all nine bytes. Independent XML cases exercise an explicit set, inheritance of that set, an explicit clear on a missile-derived type and the native zero default.

At spawn, `9BB030..9BB052` assigns the creation request's type handle to both unit fields `+18` and `+20`. The descriptor chooses between them using unit byte `+3A` bit 2. Its flag comes from the selected **shared** catalog object. Per-player catalog rows and per-instance collision overrides feed other fields.

## Evidence at insertion

Every opening type resolves to the same Missile flag in Core, HeroesData and GateOrder as it does across the wider pinned projection of 1,997 installed CUnit declarations plus the map declarations. TEN has 172 loop-zero units and 24 target recordings have 4,211. None of those recordings emits a unit-type change through loop 64. Tracker data describes visible type changes. A transient replacement inside a creation callback before spatial insertion remains unobserved. The 93-bit projection is qualified on the selected type carrying the resolved flag. The 92-bit live-radius ledger is available independently. [Tracker comparison](../observations/opening-type-history.json)

The independent byte comparison found identical descriptor values, slot order and handle hypotheses in both ledgers. For every row the masks differ by exactly bit 30. The checks also reject the candidate ledger as a baseline, a changed type assignment, and evidence for another build. The spatial operation history and first fast CRC remain open. [Differential results](../observations/recorded-type-ledger-check.json)

```text
python opening_missile_flag.py EXE DECODED_TEXT CATALOG_PROJECTION CATALOG_DIRECTORY_OR_ZIP GATEORDER_MAP OPENING_WITNESSES --spatial-ledger PRIVATE_92_BIT_LEDGER --private-output NEW_PRIVATE_93_BIT_LEDGER
python check_recorded_type_ledger.py PRIVATE_92_BIT_LEDGER PRIVATE_93_BIT_LEDGER observations/opening-missile-flag.json
python check_opening_type_history.py TEN CONTROL_PATHS
```

The first command prints the public catalog receipt. Omitting both optional arguments runs the catalog check alone.
