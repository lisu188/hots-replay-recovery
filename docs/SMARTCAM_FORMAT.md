# Dragon Shire smart-camera member

The 1,534-byte `replay.smartcam.events` carried into TEN_GREYMANE R8 still uses build 41810's unit-tag packing. The complete replacement generated for R8's recorded tracker is 1,534 bytes, SHA-256 `c3dd2875353f18c2cf62ee2a79e1641eb6a800aba88a6b45bd50287884043f35`. All 236 endpoint words change across 118 records. The replacement preserves their selection, ordering and loop numbers. Reversing the conversion recovers every original byte.

## Physical format

Every sampled record occupies 13 bytes. Offset 0 is always 0x08. Its meaning is unresolved. Offsets 1, 5 and 9 are little-endian unsigned 32-bit values. The first is a nondecreasing game loop bounded by the replay header. The two remaining values identify tracker units by index and recycle. The observed packing is `(index << 18) | recycle` on build 41810 and `(index << 22) | recycle` on 98348. No endpoint was zero or 0xffffffff. The supplied Blizzard 96477 schema’s standalone `unit_tag` helper uses shift 18. The 98348 physical samples require 22 for this member.

| Input | Records | Fields resolving to actual tracker births | Hits with other build's shift | Whole members restored through both packings |
|---|---:|---:|---:|---:|
| Four genuine 41810 games | 434 | 868/868 at 18 | 52 | 4/4 |
| Fourteen genuine 98348 games | 1,198 | 2,396/2,396 at 22 | 7 | 14/14 |
| TEN R8 partial, header 98285 | 118 | 236/236 at 18 | 15 | 1/1 |

Both columns independently admit only the indicated shift when testing all 31 splits in every file. A same-loop tracker record credits the left endpoint with killing the right in 31 historical and 58 current records. Zero cases reverse this relation. A unique recorded death at that loop identifies the ordered pair in only 24 of 58 attempts on 41810 and 42 of 148 on 98348. Moving that test to the previous loop gives zero matches out of 31 and 94 attempts. Only one historical record and four current records share a loop with any message event. These comparisons support the temporal interpretation while leaving the camera's endpoint-selection policy open.

Hero identities were joined through the tracker birth, named `PlayerSpawned` stat and `SPlayerSetupEvent` slot. On 98348, 1,081 left and 531 right occurrences were primary hero bodies. The counts were 367 and 237 for the historical cohort. Both columns also contain map structures and dynamically spawned units. In the current recordings all 1,198 left references were strictly within tracked lifetime intervals. Of the right references, 1,139 were inside and 59 at a birth, death or revival boundary. Two old left references occur after recorded death, a Sgt. Hammer body 20 loops later and a Dragon Knight vehicle 29 loops later. A dead endpoint can still address the original full unit generation. The constant first byte supplies no observed per-record user identity.

## Complete member for the carried tracker

The R8 archive has the stock map handle and preserves TEN's entire original 328,838-byte tracker member byte-for-byte (SHA-256 `1a9a556f9f1fde466d17c4a3a3fbb31cbec8d8086bef97efeb796f1f5175245f`). It preserves the original smart-camera member as well (SHA-256 `290cdc9f59d6ea5e7c0c6cdfe52b7c8f21164be2599b8b3507eebe01f435cdea`).

`match_tracker_identities(keys, source_tracker, destination_tracker)` joins full source (index, recycle) keys to destination tracker births by birth loop, named event, type, initial control/upkeep and XY. The entire tracked live/dead sequence must match. It requires a one-to-one association and rejects ambiguous or absent matches. Target packed tags and camera data play no part in this join. All 71 distinct TEN endpoint identities were unique on birth signature alone. In five genuine current field occurrences, duplicate birth signatures required the independent lifetime comparison. The reciprocal packing check preserves the original endpoint choices.

The generator changes 471 bytes, confines all changes to endpoint words and resolves all 236 projected fields at shift 22 in the carried tracker. The complete result is conditional on those recorded logical unit identities. It does not establish allocation during an independent 98348 simulation of TEN, or an end-to-end playable replay.

## Map-backed partial projection

`smartcam_startup.py` independently joins original and selected target map placements by object ID, type and authored XY, then uses the destination author's object rank and initial recycle 1. It accepts only references strictly within the tracked first source lifetime. With the historical-layout talent package, six original fields qualify across four authored objects, including three references to the original Dragon Knight vehicle. With the stock-layout talent package, two tower references qualify. The corresponding startup identities, types and XY were verified independently in all four old and all fourteen current trackers. This comparison verifies starting allocation. Runtime survival of these objects at later loops in a converted simulation remains unverified. The other 230 TEN references occur outside map-authored startup. A hero spawn or roster ID alone cannot resolve them.

## Run offline

Put the existing recovery repository, its pinned Blizzard schemas and the project dependencies on Python's import path. Provide original input archives. The generation command writes a new member to an unused file path.

```text
python smartcam_tags.py audit --replay CONTROL.StormReplay --sha256 CONTROL_SHA256 --build 98348
python smartcam_tags.py generate-r8-tracker-member --source TEN_GREYMANE.StormReplay --r8 R8.StormReplay --output TEN.smartcam.private.bin
python smartcam_startup.py --source TEN_GREYMANE.StormReplay --original-map dragon-41810.s2ma --target-map historical-talent-layout.s2ma
python -m unittest test_smartcam_tags
```

[Cohort verification](../observations/smartcam-cohort.json) · [Complete member for the retained tracker](../observations/smartcam-r8-member.json) · [Map-backed endpoint offsets](../observations/smartcam-initial-endpoints.json)
