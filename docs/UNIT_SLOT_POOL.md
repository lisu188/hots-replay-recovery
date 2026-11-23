# Build 98348 unit slot allocation

The ordinary unit creation caller at RVA `0x996fb8` passes mode 1 and manager `0x2f3d470` to the allocator. Its null result reaches the unique `GameDebug/UnitLimitReached` string. Earlier failure paths in the same function use the ability and behavior limit strings. Static IDA inspection and a separate PE/text verifier identify the 752-byte unit entries, 16 entries per chunk, and the packed tag at offset 16. [Binary and model checks](../observations/native-unit-slot-pool.json)

The allocator first pops the head of the ready list. If that list is empty, it takes the next unused index while the high-water count is below 1,023. Clean entries start at generation 1 and use ten upper bits for the slot and 22 lower bits for the generation. The initial four list heads in the physical PE are all `0xffff`.

Actual retirement increments the lower 22 bits. Ordinary released slots go on the pending list. During the drain, each pending head is removed and prepended to the ready list. Slots in the same drained batch therefore become available in retirement order, ahead of previously ready slots. A slot that reaches generation 4,194,303 moves to a separate list unavailable to the ordinary creation caller. The release dispatcher and the subsequent drain occur at RVAs `0x985a60` and `0x985b0f` in the same function. The release call within the first phase depends on object state.

`UnitSlotPool` accepts explicit allocate, retire and drain operations and returns the resulting pair. Unit death alone does not provide the retirement time, and the tracker may omit allocations. Initial clean-match behavior, ordinary allocations and the model's saturated-pool tests are the scope of this result. Save-load state restoration, the complete operation stream in TEN and full-match simulation remain open.

Run `python verify_unit_slot_pool.py ORIGINAL_EXE PINNED_STATIC_TEXT` to check the original file and transformed window lengths and SHA-256 values, PE function extents, literal references, instructions and the modeled ordering. Run `python -m unittest test_unit_slot_pool` for the reuse, saturation and terminal-generation cases.
