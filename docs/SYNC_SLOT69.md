# Sync vector slot 69 in build 98348

**A freshly computed mode-0 history vector has value zero at slot 69.** The zero comes from an explicit engine write, independently of the allocation's previous contents. Vector index 69 maps to the four bytes at entry offset `0x11c`.

| Native path | Effect on slot 69 |
| --- | --- |
| Default entry creation, `0x988da4` | Calls `0x989cc0` on the new entry. |
| Builder entry, `0x987d5a` | Calls the same helper on its argument before checking the mode. The helper fills `0x3fc` bytes at `entry+8` and `0x170` bytes at `entry+0x408` with zero. |
| Full mode 0 | `0x9707a0` retains the entry pointer in RDI. Its 70 DWORD stores skip slot 69. The first subcall overwrites the residual incoming R8 before using it. The outer builder writes slot 3, the separate 92-word array, and the processed flag. |
| Fast branch of mode 4 | After the reset, this branch writes slot 0 and returns. |
| Deferred refresh, `0x989810` | With at least two entries and the preceding entry unprocessed, recomputes that entry in mode 0, then copies it into the latest one. The counted copy preserves slot 69 whenever count exceeds 69. The other branches preserve the existing latest entry. |
| Stream-fed path, `0x9773c0` | When its supplied word count reaches index 69, the loop at `0x9774d0` can replace the word with the next DWORD from the input stream. The update retains the entry's existing word if the read returns no pointer. |

The clean value follows from the builder. Applying it to a particular recorded first sync requires evidence that the selected history entry came through that clean path or a copy of it. The mode-0 call, the copied vector and the absence of subsequent stream-fed replacement remain unobserved for TEN at loop 64.

Run `python -B verify_sync_slot69.py ORIGINAL_PE PINNED_STATIC_TEXT` with the project's existing `verify_sync_vector_source.py` on the Python import path. The verifier rechecks both entire input hashes, the previous 70 destination checks, the zero-fill and copy instructions, and the two CPU fill implementations. All 32 combinations of native fill length and address alignment matched the expected write ranges.
