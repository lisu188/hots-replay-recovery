# Opening birth frames for TEN_GREYMANE

The offline converter generates 172 map births at loop 0 and ten primary hero births at loops 50–82. It allocates the tags through the recovered 98348 unit slot pool. Map objects, regions and initialization rules supply the placements. Lobby teams, MapInfo player slots and StartLoc points supply the hero order and positions.

The target decoder consumed all 182 frames and all 9,757 bytes. The sparse stream SHA-256 is `b734159317370c86aee3561c319dd50b629b779612037036213f50d065a89dd4`. The private map was KeepCatapults, SHA-256 `58874aca37caeacaf42789a7e90fd2da830559f6cd744c32f5724e4477a6fcb3`.

| Physical checks | Matches | Exact map frames | Exact complete hero batches | Exact hero frames in those batches |
| --- | ---: | ---: | ---: | ---: |
| Original 41810 Dragon Shire, including TEN | 4 | 688 | 2 | 20 |
| Stock 98348 Dragon Shire | 15 | 2,550 | 14 | 140 |

All 182 predicted TEN frames matched the physical 41810 bytes when encoded with the preceding event's tick. For current Dragon Shire, the independent comparisons cover 137,970 map bytes and 5,929 hero bytes, including each event's position in the birth order, both owners, coordinates, index and generation. Two original Xul openings created an extra item, and one current D.Va opening created a pilot. The converter withheld the entire hero batch in each case.

Three of the 182 TEN frames recur byte-for-byte in stock Dragon Shire, and 165 have a current same-map witness for the unit type. Seven of nine current replays on other maps matched a complete sequence of ten primary heroes for type, owners, loop and order. Together the controls witness all eight TEN hero types. The other-map check reads the local coordinates and tags from those recordings. The target client has yet to produce an independent trace on the historical layout. Later allocations, slot reuse, other tracker event types and replay playback are outside this result.

Run the generator with the repository's usual protocol-loader environment.

```text
python opening_birth_wire.py SOURCE_REPLAY KEEP_CATAPULTS_MAP MAPMECHANICS_GALAXY --build 41810 --sha256 e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824 --out opening.private.bin
python test_opening_birth_wire.py
```

The aggregate receipt contains reference hashes and no player identities. The private frame ledger records the source offset, enclosing delta context, sparse offset, frame hashes and observed target witnesses.
