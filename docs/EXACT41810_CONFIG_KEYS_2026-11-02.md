# Exact historical41810 BuildConfig and CDNConfig lookup keys

The preserved NGDP versions snapshot identifies exact41810 configuration lookup
keys. This replaces the earlier absence of a specific BuildConfig key; the
referenced config bodies and their binding to TEN_GREYMANE's root remain missing.

| Identifier | Value |
| --- | --- |
| BuildConfig | f22332dbb7eb19a46c3c3c2292cdb226 |
| CDNConfig | 056112531a93ecd8acd48168fb45f51d |
| Original replay root, a distinct namespace | 83d43a8647bb5ca5caa6f2f09064da55 |
| Original fixed-file hash, another distinct identifier | c585f3548fb8f9776fa1fba4dfec2b9a |

## Preserved source identity

The third-party mdX7/ngdp_data archive's exact path isUS/hero/41810/versions.
The body from commit7508618ff97997fe89c34b5489bbeca6385865f9, whose recorded
author date is2016-03-30, is byte-identical to the current pinned copy at
d8bcfafa67e7408c95d33caa3733729aff17c6fe. The entire603-byte body has SHA256
997a03d0ef02436ea6d040811201a4cf94e4807d7d019288b605199a1a229fc8 and Gitblob
5078a196309cf80e1b7c4520d914c34c4345bc94. Both exact one-file subtree hashes
were independently reconstructed in the acquisition lane.

All six rows(us/eu/cn/kr/tw/sg) declare BuildId41810, literal VersionsName
17.0.41810 and the same two lookup keys. The literal version string is preserved;
no replay tuple or executable version was rewritten from it. Earlier regional
rollout snapshots also contain41504 rows, which are excluded from this mapping.
The source is an immutable third-party preservation, not Blizzard attestation.

[Original snapshot](https://github.com/mdX7/ngdp_data/blob/7508618ff97997fe89c34b5489bbeca6385865f9/US/hero/41810/versions)
and[current pinned snapshot](https://github.com/mdX7/ngdp_data/blob/d8bcfafa67e7408c95d33caa3733729aff17c6fe/US/hero/41810/versions).

## Exact-key follow-up and limits

Six current-host and18historical-host config requests returned URL-specific
404s,403s or transport/DNS errors. No response supplied a config body matching
either expected MD5 key. GitHub exact-key content searches found only the six
region versions copies; exact-key filename searches found no body. The exact
version directories contain only versions. Two bounded IA CDX queries returned
empty arrays. These scoped outcomes do not establish global deletion or absence.

Preserved2016cdns/game/install product settings identify hosts and launcher
configuration, not the CASC encoding/install manifests. A separate IA software
metadata route made16requests/102784response bytes and inspected six new file
lists without establishing an exact41810client or config. No large payload was
downloaded; opaque or mislabeled archive contents remain uninspected.

## Controlled next CASC route

The existing277504-byte managed CascLib was inspected through signatures/static
IL, without invoking storage APIs. Its BLTEStream,EncodingHandler,MNDXRootHandler
andInstallHandler stream primitives can consume already acquired blobs in an
isolated task cache. Each object still requires expected length/CKeyMD5 and
encoded/decodedSHA256 checks. Compatibility with actual2016formats remains
unproved until those blobs exist and are parsed.

The convenience online loader is unsuitable as proof of an explicit old build:
it performs direct Ribbit requests before overrides; its override properties
have local-file/File.Exists behavior, and ActiveBuild initially selects index0.
Its CDN index initializer also visits every configured archive. Do not feed a
bare historical key into that route and label any fallback live data as41810.
The installed98348storage was never opened or changed by this research.

The next acquisition must obtain actual hash-verified BuildConfig/CDNConfig
bodies, then encoding/root/install data. The current source supplies lookup keys,
not an old client, gameplay catalogs or a safe conversion mapping.

## Ability351 follow-up

The cached author-labelled41810 Tyrande publication was compared with94recorded
commands in the original and new reference. Three original and nine new unit
commands precede the recorded level4choice; both regular Tyrande players chose
Pierce rather than the published level4ProtectiveShield/HealingWard talents.
This conditionally conflicts with interpreting351universally as those unlocked
abilities, under metadata applicability, actual-caster and valid-cast assumptions.
Raw attempts can fail. Baseline LightofElune remains compatible with descriptions
and targets; its numeric351identity is not established. No name, current ID,
clone label or flag/replay rewrite was admitted.

See observations/exact41810-config-key-mapping-2026-11-02.json and validation
receipt for whole-source pins, route outcomes and assumptions. No game, Computer
Use, native target execution/emulation, replay edit or synchronization change
occurred. Full upgrade and current-client playback remain unproved.
