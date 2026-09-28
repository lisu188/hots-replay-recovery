# Chat context and decision log

Date: 2026-09-28
Project: upgrade `TEN_GREYMANE` Heroes of the Storm replay for playback in newer/current clients.

## User requirements

1. Update the uploaded `.StormReplay` so that it can be played in the newest possible Heroes of the Storm version.
2. The user explicitly prefers an aggressive approach: reaching the newest possible build matters more than minimizing implementation effort.
3. OneDrive is the persistent storage/checkpoint location for this work.
4. Git is the source of truth for version control and change history.
5. The binary replay must have a deterministic JSON/JSONL semantic projection so migrations can be reviewed with ordinary `git diff`.
6. Preserve intermediate checkpoints rather than overwriting the only working state.

## Source replay

Source artifact in this repository: `artifacts/TEN_GREYMANE_source_41810.StormReplay.base64` plus SHA-256 sidecar

Decoded header:

- signature: `Heroes of the Storm replay\\x1b11`
- version: `1.0.17.0`
- build: `41810`
- baseBuild: `41810`
- dataBuildNum: `41810`
- elapsedGameLoops: `19732`
- ngdpRootKey: `83d43a8647bb5ca5caa6f2f09064da55`
- fixedFileHash: `c585f3548fb8f9776fa1fba4dfec2b9a`
- source SHA-256: `e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824`

Decoded event counts:

- game events: `104257`
- message events: `155`
- tracker events: `6614`
- `SCmdEvent`: `4558`

The original replay decodes cleanly with the build-41810 protocol implementation in this repository.

## Protocol investigation already completed

The Blizzard `heroprotocol` schemas were compared across later builds.

### 41810 through 42590

Protocol files are identical for the relevant replay structures. This is the lowest-risk upgrade region.

### 42742

The first observed relevant protocol change is `SCmdEvent.m_cmdFlags`, changing from 25 bits to 24 bits.

The concrete replay was checked, not just the schema. None of its 4558 `SCmdEvent` values uses the removed high bit, so the conversion is information-preserving for this replay.

### 43905

The next observed structural change adds optional `m_ammId` to game options/lobby data. Existing 41810 data can map this to an absent optional value.

### 44256 and later

This is the first substantially larger game-event format transition. In particular, `SCmdEvent` gains optional `m_vector`, `m_cmdFlags` later uses 26 bits, and type IDs shift. This requires semantic decode/re-encode rather than patching bytes in place.

The event types actually present in this replay were compared to a much later protocol (96477). All 20 game-event types used by the source still have modern equivalents, including command events, selection changes, target updates, talent selection, camera events, pings, dialog/sound/cutscene events and leave events.

### Important simulation constraint

Protocol compatibility is not the only problem. HotS re-simulates the match from player commands and game data. A syntactically modern replay can still desynchronize if the current game data differs from the source build. Therefore each generated binary checkpoint must be tested by encode -> decode validation first, and client playback/desync testing second.

The final target previously discussed in chat was a current-client build around the 2.55.17 line. The exact target build must be re-verified before the final conversion rather than hard-coded from an earlier web lookup.

## Repository representation

`decoded/<build>/` is the reviewable semantic representation.

- `header.json`
- `details.json`
- `initData.json`
- `attributes.events.json`
- `game.events.jsonl`
- `message.events.jsonl`
- `tracker.events.jsonl`
- `manifest.json`

Large event streams are deterministically generated as JSON Lines. To keep GitHub history compact, Git stores their hashes and explicit changed-event deltas under `migrations/`; full streams are regenerated locally when needed.

Binary values are represented deterministically rather than being silently decoded as text.

## Validation policy

For every migration checkpoint:

1. Start from the committed semantic representation.
2. Apply an explicit migration to the target protocol model.
3. Review `git diff`.
4. Encode a target `.StormReplay`.
5. Decode that generated replay again using its target protocol.
6. Compare the re-decoded semantic state to the intended migrated state.
7. Record hashes, event counts, any lossy/defaulted fields and validation results.
8. Commit the checkpoint.
9. Create a Git bundle and upload the bundle plus binary replay to OneDrive.

A binary is not marked successful merely because its header says a newer build.

## Storage

OneDrive working folder created by this project:

`HotS Replay Upgrade - TEN_GREYMANE`

The OneDrive folder already contains a copy of the original replay and a progress manifest. Git bundles and generated `.StormReplay` checkpoints should continue to be uploaded there.

## Conversation requests, chronological

- User: update the replay so it can be played in the newest HotS versions.
- User: the result matters "at any cost"; determine the maximum version reachable.
- User: use OneDrive as the base for saving progress and implement the conversion.
- User: use Git for version control; convert the binary replay to JSON so changed fields are easy to diff.
- User: continue and save details of the chat in Git.

## Current implementation state

Commit `3b985a4` imported the build-41810 replay, a deterministic decoder and JSON/JSONL projection. A fresh decode was independently rerun after that commit and matched the committed projection.

Next implementation milestone: semantic + binary migration to build 43905, followed by encode/decode round-trip validation. After that, cross the 44256 structural boundary.

## GitHub publication decision

The user requested that binary files be represented as Base64 text because the GitHub connector cannot upload arbitrary binary content. The source replay and each generated replay checkpoint therefore use `.base64` plus `.sha256` sidecars.

## GitHub publication checkpoint

The user selected `https://github.com/lisu188/hots-replay-recovery` as the remote repository. The repository is public and the connected account has push/admin permissions.

Because the GitHub connector only accepts text payloads, replay binaries are never committed as raw `.StormReplay` files. Each replay is Base64-encoded, wrapped at fixed width, and split into deterministic `*.base64.partNNN` files small enough for connector uploads. The corresponding `.sha256` file is authoritative for reconstruction validation. `scripts/restore_artifact.py` transparently concatenates parts, decodes Base64 and optionally verifies SHA-256.

The first remote snapshot was published to `main` as GitHub commit `4248b86f194d08205d0168747a5629dbef4eaf89`. It contains the decoder/encoder toolchain, semantic projections, migration deltas, chat context, source replay Base64 parts and the build-43905 replay Base64 parts.

The build-43905 checkpoint has passed protocol encode/decode round-trip validation but has not yet been proven playable by a real HotS client. The next engineering task remains crossing the larger build-44256 protocol boundary.
