# Current client-list receiver selection — 2026-10-25

The selected native getter at RVA `CBF6D0` returns `P+4430` when `DWORD[P]==2`, and `P+1C0` otherwise. IDA decoded six instructions covering 20 bytes through RET, with no calls or memory writes. The preparation checked two existing E8 call sites and a 128-byte callee window: 138 new saved-patch bytes in total, without PE, exception-table or full-file hash reads. All four source-identity checks matched. The selection is an entry prefix; exact RuntimeFunction bounds are not claimed.

The code comes from the existing analyst-derived, statically transformed 98348 text patch. It is not a runtime capture or unaltered on-disk PE text. The pinned observation records the preparation, actual IDA output, successful exit, and saved caller/copier sources.

## Receiver arithmetic and separate backing lists

In retained DFE7D0, let A be the pointer read from post-prologue RCX+8. The code forms P=A+28 and supplies it to CBF6D0 at DFF506 and DFF8F4. Therefore a discriminator value2 selects A+4458; another value selects A+1E8. The caller treats the result as a count followed by records at +8 with stride360. This does not observe the runtime discriminator or establish A's identity in another function.

The retained consumer reads InfoHero voice flags at record+2C1/+2C2 and ORs them into one slot bit. It copies staff+2C3 and boost+35C separately. These operations explain current consumption; they do not recover historical values. A true voice result cannot distinguish the three true input pairs.

A separate retained 6BEF94 path uses Q=B+8088, where B is loaded from a global owner pointer. Its guard requires DWORD[Q]==0 before the getter. That result is B+8248, arithmetically (B+8090)+1B8. The same function also has calls based at B+28, whose guard admits0or2. Keep those receiver bases distinct.

In recorded-loader CFE3B0, use a third owner symbol C. Metadata success stores a discriminator at C+8088 and calls 6BA2B0 with destination C+8090. The saved copier supplies its source and destination +1B8 subobjects to 6B5BA0. This anchors a metadata copy field. It does not show that the separate discriminator2 list at A+4458 was populated there. Equality of offsets does not prove that A, B and C denote one actual instance.

## Next producer boundary

The next useful step is an authenticated call and receiver chain for DFE7D0's A+28 object, followed by one real producer or copy into its discriminator2 list. No direct population of that list was authenticated in these retained named caller/copier windows. The metadata copier must not be promoted into that missing witness.

This milestone changes no codec or replay and supplies no old-to-current field defaults. Player/account level, boost, separate voice flags, staff state and the historical SharedPlayerInfo branch remain unresolved. No game or Computer Use was used, and native playback, full conversion and synchronization parity remain unproved.
