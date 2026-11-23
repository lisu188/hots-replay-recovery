# Camera and ping fixes in a private R8 checkpoint

The offline builder produces a separate partial replay from the original TEN_GREYMANE match and the pinned R8 checkpoint. Its output retains R8's build 98285 header, map dependencies and recorded historical tracker. Both input files are identified by byte length and SHA-256.

The builder generates 81 corrected ping inputs and compares each original event 36 frame with its native encoding at its actual position among the 104,257 game events. It replaces 25 unit fields, changing 56 bytes in the 1,148,436-byte member. A second pass compares every decoded event, including frame lengths and user IDs. The 118 smart-camera rows use the same recorded unit generations. The only archive member differences were the game events, smart-camera events and regenerated MPQ attributes. All 308 sync records preserved their original bytes.

Two builds produced the same 3,030,798 bytes, SHA-256 `152f510b0cf30bf200d58b33877de1a7ee2fa63762dc03dff3369efa9a3da740`. Verification covered every live archive block using an independent Python reader and StormLib, along with all available native archive integrity checks. Dynamic allocations under a regenerated build-98348 simulation, destination checksums and native playback remain unverified.

~~~text
python integrate_r8_camera_pings.py --source ORIGINAL.StormReplay --r8 R8.StormReplay --output R8_CAMERA_PINGS_PARTIAL.StormReplay --stormlib /path/to/libstorm.so
~~~

Use the repository's pinned protocol modules, Python 3.11 and StormLib. Use a fresh output path. Keep the derived replay private.
