# TEN opening event admission in HotS 98348

The first 30 reconstructed TEN game records pass the native pre-CRC tests on a clean startup with TEN’s recorded roster. The original 41810 archive and the 98285 R8 candidate both carry ten controlled slots with user IDs 0 through 9 and observer class 0. Six unoccupied slots follow. This proof applies when that roster is committed to the target context. Resumed state, additional producers in the global dispatch queue, and the full simulation checksum remain open.

| Native RVA | Verified operation |
| --- | --- |
| `0x1353a78`, `0x132d99b–0x132da04` | Each physical event ID selects its constructor and primary vtable. For IDs 5, 7, 27, 28, 56 and 104, virtual method +40 returns 2. All six enter G+BFDD8. IDs 101 and 102 have a separate queue branch. |
| `0x133b890`, `0x133b9d0–0x133ba08` | The setup scan marks a bit for each controlled slot’s user ID below 16. TEN supplies a mask of 0x03ff. |
| `0x133dd60–0x133df22` | The native lookup scans slots, compares control 2 and the requested user ID, and returns the matching slot index. The 0xf28 stride matches the slot descriptor. |
| `0x645aa4–0x645b0c`, `0x97d44b–0x97d5de` | Slot copy preserves the optional user ID and its dword at +0xC. Setup copies that dword into the role byte at user object+0x32. The native type 730 offset table and the named protocol agree on the observer field at declaration index 8, tag −18. |
| `0x9d1df0`, `0x9d1e00` | The writer and reader use distinct getter entry points. Both return null for user 16. For indices below 16 their complete manager functions, including the jump tables, match byte-for-byte after resolving code and data addresses. |
| `0x132e2e4–0x132e350` | Types 5, 43 and 102 bypass the active-user bit. A missing user object passes the role test. Otherwise the virtual +58 role mask must include the object's role bit. The six event masks in the order above are 7, 7, 1, 7, 1 and 1. |

TEN’s first and 22nd records are type 5 from physical user 16. The mapped-user getter at 0x1327810 returns 16 directly. Its first event has loop 0 and an empty standalone payload. With a clean 0xffffffff seed, the nine CRC input bytes are `000000001000000000`, producing raw G+A13C0 = `0x79167cd3`. The native loop-zero early return for type 5 occurs after the CRC stores.

Run `verify_dispatch_admission.py EXE VERIFIED_TEXT ORIGINAL R8 GAME_PREFIX` using the repository's Python dependencies. Compare its output with `native-dispatch-admission.json`. It authenticates every native and replay input by SHA-256, checks the six constructors and vtables, checks both full getter bodies, decodes both replay rosters and parses the reconstructed game prefix with the pinned native graph. No game execution is involved.
