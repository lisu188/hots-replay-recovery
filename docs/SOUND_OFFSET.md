# First remaining sound input

TEN records two sound offset acknowledgements for user 1 at loop 68. The original first handle is 0x003a0c7b, followed by 0x00360c7c. In the first physical record, the preceding game input is three loops earlier. Event 46 carries one unsigned 32-bit object handle.

In build 98348, the sound initializer at RVA 0xac6280 appends the word from object +8 to the active sound list. The periodic callback 0xac6080 reads the low 16 bits of an entry to select a 16-byte slot, checks class 15 and passes the live object to the offset test at 0x6899e0. The event constructor at 0x77bb60 copies object +8 to event +0x30. The event codec at 0x77ab10 uses native schema root 441 for that payload.

The listener registers 0x3002e at ordinal 5. The handler at RVA 0xc28157 uses the low 16 bits to select a class-15 slot and marks the reporting user's bit on its live object. It also passes the full word to 0xa8f5b0. That function checks pending entries for kind 3 and exact 32-bit handle equality before marking their reporting-user bit. The full target handle therefore matters. The high half's allocation rule is still open.

Through loop 1024 inclusive, the 24 native recordings contain 25,610 physical event-46 frames. The pinned native codec reproduced all of them. Every recording has a different first handle. Fifteen stock Dragon Shire files have the same set of sound-length descriptor values as TEN, with 15 distinct first handles. Ten have exactly the same ordered descriptor events as TEN through loop 64, including loops and users. Two of those ten report their first offset at loop 68 for user 0 with different words, 0x000352cf and 0x000d52da. The original TEN first word occurs in zero of the 25,610 native offsets. This rules out deriving the word from these descriptors, map, first loop and reporting user alone.

The target engine's allocation history for this sound instance on the TEN roster and map remains the missing input. Static inspection established where to look for its full handle. There is no verified target loop-68 sound frame for TEN.

Run `verify_sound_offset_native.py PE DECODED_TEXT` against the pinned target and `sound_offset_evidence.py --case BUILD SHA256 REPLAY ...` with the repository and its Python dependencies on `PYTHONPATH`. The two JSON receipts contain the verified native constants and per-replay observations.
