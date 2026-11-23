# Public Quick Match fixture search

Four public GitHub replay archives were downloaded from immutable commit URLs on 2026-11-23. Each archive passed a SHA-256 check, agreement of all three build fields and byte-for-byte re-encoding of its physical loop-zero tracker window under the corresponding schema.

| Public project | Physical build | Map | Matchmaking ID | Opening frames |
| --- | ---: | --- | ---: | ---: |
| HeroesReplay/HeroesReplay | 75589 | Garden of Terror | 50001 | 198 |
| Arthrose/HotsReplayReader | 95301 | Hanamura Temple | 50001 | 188 |
| astefanski1/storm-parser | 94786 | Dragon Shire | 50091 | 245 |
| matella/storm-codex | 93810 | Silver City | 50101 | 141 |

The two recordings with matchmaking ID 50001 are physical Quick Match controls for their respective older builds. They provide no build-98348 wire evidence. The accompanying JSON gives the raw URLs, full archive hashes and opening fingerprints. Reproduce by downloading those exact URLs under the filenames in the verifier and running `python public_qm_fixtures.py PRIVATE_FOLDER`.

The spectator's README describes requesting Quick Match through Heroes Profile. At repository commit `57d9ddec37245ac3068b7a39b5bf795806735d99`, its 1,994-entry tree supplied one replay fixture. Its latest 30 releases listed application ZIPs. [HeroesReplay documentation](https://github.com/HeroesReplay/HeroesReplay/tree/57d9ddec37245ac3068b7a39b5bf795806735d99)

MercStats listed 2,459 build-98348 recordings and 791 Quick Matches across all builds at 08:15 UTC. Those are separate aggregate counts. No publicly offered raw sample was found on its tools, about or FAQ pages. The hotsbuff Go parser reports build-98348 testing and instructs users to supply replay files for its golden tests. [MercStats coverage](https://mercstats.com/tools) · [MercStats FAQ](https://mercstats.com/faq) · [Go parser testing](https://pkg.go.dev/github.com/hotsbuff/stormreplay#readme-testing)
