# Controlled R4: investigate the replay-open rejection

Date: 2026-09-29.

## User observation and its limits

After the instruction to test NATIVE_R3, the user supplied a screenshot reading `Unable to open replay.` No filename or build is visible in this screenshot. Association with R3 is inferred from the conversation sequence, not independently established from the image. It is a failed opening attempt, not evidence of a new process crash or of successful loading followed by simulation desynchronization.

The OneDrive GameLogs search returned no new explanatory log after the ordinary 08:11:46 launch of build 98285. The 06:30 crash records still refer to the earlier first 98285 candidate, not R3. Do not recycle that crash as proof of what rejected R3. The search does not establish that every possible local log was available on OneDrive.

## Evidence found

Additional native StormLib checks were performed on the immutable source, R3 and the user's private unmodified 98285 Braxis reference. Header, HET, BET, hash, block and high-block raw checks returned zero errors. Per-member CRC, MD5 and available raw-MD5 checks reported no error bits. Absence of a checksum on a particular internal or empty member is not represented as a verified absent digest. These findings do not prove that the HotS engine accepts the archive.

The migration of `m_allowedControls` used the serialized four-bit length limit (15) as its target logical mask length. A full reinspection of the real 98285 reference instead observed ten bits in every one of its sixteen slot descriptions:

| Slots | R3 mask (length, value) | Genuine reference (length, value) |
|---|---|---|
| 0-9 | (15, 32767) | (10, 1023) |
| 10-15 | (15, 896) | (10, 28) |

The original 41810 masks had 255-bit lengths. The 15-bit R3 masks are serializable under schema 96477. We have not proved that the engine forbids them or that their width is responsible for the rejection. A single real donor does not establish a universal mask-width rule for all game modes.

## Deliverable and scope

`TEN_GREYMANE_client98285_CONTROLS_R4_EXPERIMENTAL.StormReplay`

- SHA-256: `edd690c6956b48c1592edf946bc8e01e012220c961b04cf3d86ec983c808367c`.
- Size: 1230829 bytes.
- Public checkpoint: `client-checkpoints/98285-controls-r4/`.
- Publication commit: `f6ea8daec7e0473fb94ba4cbc5b227d6d271a73c`.
- Status: experimental; actual client opening and playback are not validated.

R4 changes only the sixteen allowed-control mask values in `replay.initData`, from the measured R3 values to the measured reference values. This retains the leading ten bits and removes five trailing bits per mask. Those removed bits are set for the ten player slots and zero for the six observer slots; this is therefore not described as lossless preservation of all possible permissions.

The lobby payload changes from 4232 to 4222 bytes. The larger overall archive size comes from the native append/update process, not from additional gameplay events. Header bytes, version 98285, root/hash identity, matchmaking ID 50001, every other lobby field and every other replay member payload remain unchanged. All event streams are byte-identical to R3: 104257 game events, 155 message events and 6614 tracker events. Dragon Shire, recorded commands and timing are preserved. Native HET/BET and the 16384-byte raw-chunk setting remain present.

The generator fails closed on a different R3 source digest, a changed mask pattern, missing native verification, invalid reference observation or existing output path. It records the removed bits explicitly. It never overwrites a source or previous candidate.

## Validation completed

- The actual private Braxis source was inspected locally with the preserved official 96477 schema, including complete observed-payload decode/re-encode. Only allowlisted mask observations and its digest are published; the donor binary is not.
- 28 new tests passed locally, with no failures or skips. These include detection of deliberately corrupted header and raw-member checksums, immutable-source guards and tests proving that only the sixteen intended masks change.
- Two local R4 generations, one deriving observations from the actual donor and one using the saved observation, are byte-identical.
- CI run `36533659969` completed successfully at code commit `216034d389ef2dffeb53cd3b19adb24cea742829`: 124 tests passed, no failures or skips.
- CI fetched pinned official Blizzard schemas at `9af3ea7150f1a8acb53464c92519a9bbcc7a3594`, used native StormLib and independent mpyq, generated the candidate twice, verified the source-code digest and matched the local artifact SHA-256.
- All 22 Base64 parts reconstruct the same candidate. The downloaded CI artifact also matches the locally produced replay exactly.
- Neither local validation nor CI ran a HotS executable. These checks are structural and semantic invariants, not an engine playback test.

## Remaining work

The old `replay.server.battlelobby`, resumable/smartcam/synchronization members and map dependencies remain preserved rather than transcoded. Their compatibility with current engine code is unresolved. A public community battlelobby parser explicitly skips very old builds; that is an implementation limitation of that parser, not proof that a migration is impossible.

The next user test is CONTROLS_R4. If the same rejection remains, record it against this exact filename and preserve any new log. That outcome would show the mask-only change was insufficient; do not keep retargeting version numbers without new version evidence. Further isolation should focus on native initialization and dependencies while comparing an unmodified current replay and a container-only control when those playback observations become available.

## Preservation

The R4 binary was uploaded under a distinct filename to both the existing OneDrive project folder and Multiplayer folder. The CI bundle preserves complete Git history through the R4 artifact publication; this document and the subsequent progress snapshot are also included separately in the dated delivery package. Raw private donor data, account paths and crash memory are excluded from public Git.
