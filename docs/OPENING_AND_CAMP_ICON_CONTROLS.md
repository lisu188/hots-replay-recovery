# Dragon Shire opening controls and later icon allocations

Against the original TEN tracker, the MercCapture map and lobby predict all 30 physical frames from loops 1 through 84. The complete 1,903-byte sequence, including each enclosing loop delta, matches. The prediction allocates ten heroes, emits their ten PlayerSpawned notifications, and emits each pair’s LevelUp notifications in reverse order two loops later.

| Physical build | Recordings | Complete windows | Complete bytes | Individually matching frames, including partial cases |
| --- | ---: | ---: | ---: | ---: |
| 41810 | 5 | 1 | 1,903 | 106 |
| 98348 | 15 | 12 | 23,846 | 514 |

The four other historical windows comprised one extra birth, two with different birth payloads plus extra births, and one unsupported lobby roster. Two incomplete retail windows contain all 35 modeled rows plus an extra birth or TalentChosen event. The remaining retail case misses ten predicted birth rows and a PlayerSpawned row. The JSON lists individual digests and counts. Retail openings include five camp ownership transitions specific to the stock map. A partial match contributes no bytes to the complete-window totals.

## Mercenary icon tags

Each historical recording produced five camp icons after the gates. Across five recordings each camp had five different slot/generation pairs. In the fifteen retail controls the stock map instead created icons during loop zero. Its opening model matched all 75 tags.

TEN created its icons at loop 2530. For the build-98348 slot pool to reproduce the recorded source generations, the minimum numbers of intervening same-slot allocations between the preceding recorded birth and the five icon births are 9, 6, 1, 6 and 14. The same-slot lower bound across the visible slots through that loop is 1,129 unreported birth generations. The first gap is at loop 849, where slot 95 advances from generation 1 to 5. These bounds condition on reproducing historical generations under the target’s ordinary allocator. They do not reveal the actual target retirement, drain or reuse order.

The 13 MercCapture post-capture icon transfers remain withheld. The independent capture adapter can already project 39 beacon and flag frames with opening allocation evidence.

```sh
python signed_opening_controls.py PRIVATE_REPLAY_MANIFEST historical-shrine-start.json MERC_CAPTURE_MAP RETAIL_DRAGON_MAP STOCK_SCRIPT_DIRECTORY
python camp_icon_pool.py PRIVATE_REPLAY_MANIFEST historical-shrine-start.json MERC_CAPTURE_MAP RETAIL_DRAGON_MAP MAPMECHANICS
```

Both checks read the pinned recording bytes and compare original versus target-format tracker fields offline. Native client playback was outside the test.
