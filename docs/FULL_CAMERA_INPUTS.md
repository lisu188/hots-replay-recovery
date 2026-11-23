# TEN camera updates

The original game member contains **17,593** `SCameraUpdateEvent` records from loop 71 through 19,555. The build-98348 native-layout writer reproduced their 140,418 enclosing bytes exactly. The standalone target-format stream uses the elapsed time since the preceding camera record and occupies 140,419 bytes. Its SHA-256 is `fcf418fed5f099e1f763193422bfb7d1ae47563903f59ce5165879219351f68c`. The original partial R8 also retains every one of these records at its original game ordinal, with identical preceding loop, fields and physical frame bytes.

The two pinned Blizzard schemas define the same ordered payload. The target contains optional unsigned 16-bit X and Y together. Distance, pitch and yaw are independently optional unsigned 16-bit values. Reason is an optional signed byte. Follow is a Boolean. The converter preserves every value and its presence bit, together with the physical user and absolute loop. The separate smart-camera replay member is outside this projection.

| Original shape | Events |
| --- | ---: |
| Target only | 17,424 |
| Distance and pitch | 81 |
| Follow enabled, all optional values absent | 79 |
| Distance only | 5 |
| Pitch only | 2 |
| Target and distance | 1 |
| Target and pitch | 1 |

All seven shapes occur in the 15 authentic build-98348 Dragon Shire controls, where 406,717 camera frames matched 3,252,218 physical bytes. The historical overlay and modern stock map both have a 248-by-208 terrain extent, independently confirmed by each lobby and by the loop-zero tracker map statistic. At 256 coordinate steps per map unit, four historical and 47 native target positions exactly coincide with authored player starts. All observed camera targets lie inside the corresponding terrain extent. Only one of the 77 distinct historical distance/pitch pairs recurs exactly in the controls. The projection preserves those pairs directly. Rendering and the identity of the unit followed on the 79 follow-only updates remain unverified.

Run `full_camera_inputs.py ORIGINAL_TEN SOURCE_SHA256 41810 GATEORDER_MAP --private-output NEW.bin` to generate the camera stream. Add `--private-ledger NEW.json` for the original ordinal, absolute loop and preceding game loop of every frame. Run `verify_full_camera_inputs.py ORIGINAL_TEN GATEORDER_MAP STOCK_DRAGON_MAP CONTROL_MANIFEST --retained-r8 ORIGINAL_R8` to reproduce the aggregate. The private manifest maps the pinned SHA-256 values to local replay paths. The public verifier reads the existing Dragon Shire reference pins from `observations/unit-generation-evidence.json`.
