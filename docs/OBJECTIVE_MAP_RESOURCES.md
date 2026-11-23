# Replay resources for the historical map derivatives

Each verified map derivative supplies its own SHA-256 resource handle. The recovered resource writer changes the selected map in replay details, in the setup handle array, and in both the Battle.net lobby prefix and its corresponding cache filename. The four named standard-mod handles and their cache paths agree with the original TEN replay. The default CLI still selects GateOrder. Each other map requires its expected whole-archive digest. [Resource declaration and stock checks](DECLARED_MAP_CHECKSUM.md)

For SignedAnnouncer, the derived details, lobby prefix and standalone setup handles bind to `150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791`. All seven reviewed maps declare `0x2d44411f` in DocumentHeader. The separately computed file CRC differs. These checks concern local content and serialization. Availability in Blizzard’s depot and engine validation of a modified map remain open. [Per-map fragment sizes and digests](../observations/objective-map-resources.json)

On the frozen partial R8 setup, the 4,222-byte SignedAnnouncer resource projection gives the CRC constant `0x81fb7fdd` when the unknown mod checksum is algebraically zero. The 32 one-bit contributions allow evaluation once that mod checksum is recovered. Two independent writers agree on each probe. The private directory contains the three resource fragments per map. The actual TEN setup CRC and first gameplay sync remain unresolved.

```text
python objective_map_resources.py TEN R8_SELECTION_COPY GATEORDER_MAP CACHE_ROOT HISTORICAL_CAMPS_MAP DRAGON_BEACON_MAP SHARED_BEACON_MAP SIGNED_BEACON_MAP SIGNED_ANNOUNCER_MAP SHARED_ANNOUNCER_MAP --private-dir NEW_DIRECTORY
```
