# Live target 98785 and the 98348 client restore — 2026-11-28

## Observed state

A read-only snapshot is recorded in `observations/live-target-refresh-2026-11-28.json`. The collector source is retained in the task workspace with its SHA-256. Nothing was launched and no installation file was modified.

- **Live build.** Blizzard's EU and US version servers both report sequence 4160002, with build **2.57.1.98785**: BuildConfig `4e1fa2fae363e4c561fa8b038970389b`, CDNConfig `c34b1c630a1834ea835e6401212eebed`. The installed `.build.info` active row agrees.
- **Installed clients.** `Versions/Base98348` and `Versions/Base98746` are empty directories. Only two directories still hold a client:
  - `Base98285`: 53,592,272 bytes, SHA-256 `440c7e1b…`
  - `Base98785`: 53,571,792 bytes, SHA-256 `e85cd9bd…`
- **Switcher.** The installed switcher changed to SHA-256 `d7976f63…`.
- **Pinned 98348 client.** The pinned client (53,573,840 bytes, `efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9`) is no longer present in the installation. The task workspace keeps only derived `Heroes98348.patched-analysis.exe` copies (`5ae49a50…`). Those are not the original PE.
- **CDN availability.** Blizzard's CDN still serves the 98348 build configuration `a64c9b7ebf1c6a811ffefad97865ed80`. It names build B98348, root `c3b3c8bc82e3a5a62e550fdde9a40c28`, encoding `0fe63ea1…`/`e6f9f577…` and install `0c1a67ff…`/`e35645bc…`. The CDN configuration `9575c98a819e557a3e6ec7b003428124` lists 187 archives, archive-group `dd1337c9…` and file-index `6cfbf829…`. Both bodies MD5-verify against their keys.
- **Replay schema.** The newest published Blizzard heroprotocol commit is still `9af3ea7` (2026-02-20, schema 96477).
- **Patch content.** Secondary sources report that 2.57.1 went live as 98746 on 2026-11-23, followed by the 98785 hotfix on 2026-11-25. The reported balance changes include Greymane, one of TEN_GREYMANE's heroes. The official notes were not read.

## Decisions

The user reconfirmed the 2026-11-16 offline-only rule:
- No HotS, Battle.net, HeroesSwitcher, replay or map launch.
- No Computer Use or substitute UI automation.
- No attaching to a game process.

The conversion target stays **2.57.0.98348**, where the existing schemas, controls, catalogs and native analysis are pinned. A 98348→98785 lift will be measured later as a separate stage. To keep identity-pinned static analysis possible, the user approved restoring the original 98348 client from Blizzard's official CDN. The restored file will never be executed or placed in the game installation.

## Hazards for later work

The installed CASC storage now holds 98785 data. Reads from installed storage must not be labeled 98348. The installed-CASC 98348 research readers pin VersionName, BuildName, root and BuildKey, so they fail closed on the new storage. Catalog work must use pinned cached 98348 extracts or the CDN.

Static analysis must pin the restored client's whole length and SHA-256. The empty installation path is no longer a valid input.

## Superseded native-control attempt

The 2026-11-04 attempt (`work/current98348-native-control-20261104/`) never launched anything. It contains three helper scripts and an empty screenshot directory. Its preflight stalled and was stopped before writing a report. A `SUPERSEDED-20261128.json` receipt now records this. Its helpers must not be reused without new authorization.

## Not established

- No conversion, replay, map or synchronization data changed.
- Native playback, the full-match conversion and all 308 target synchronization checks remain unverified.
