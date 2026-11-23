# Dragon Shire intro soundtrack completions

The build-98348 candidate for the 46 `STriggerSoundtrackDoneEvent` records in TEN is `m_soundtrack = 195`. It replaces the historical value `96` and preserves each recorded user, game loop and physical delta from the immediately preceding source event. The frames span loops 887–1130. Their 322 sparse bytes have SHA-256 `522bc5077b1ec41a874dcb5bd5918616a3b006d0456a860f4c25b642337bd1f9`. The receipt lists all 46 zero-based event ordinals.

The original Dragon Shire map, current stock map and GateOrder each set soundtrack slot 0 to `MX_Dragonshire_Intro`. The installed HeroesLib starts the intro and SoundLib plays and waits on the track in that slot. In native build 98348, event constructor RVA `0x77bbe0` takes the catalog object's 16-bit link at `+0x40`, or 65535 for an absent object. The event encodes an unsigned 32-bit field. The listener at `0xc28198` resolves its low 16 bits through the catalog table at `+0x228`. Pending soundtracks of kind 4 require equality between the expected and reported catalog links before setting the user's bit. Four original recordings contain 218 acknowledgements for link 96.

The numerical prediction uses two other maps. Their exact scripts select `MX_SkyTemple_Intro` and `MX_RavensCourt_Intro`. Their build-98348 recordings carry links 145 and 203. The script computes relative first-appearance positions from named Core soundtracks, HeroesData game-UI music references, and HeroesData soundtrack declarations and their `Next` links. It applies each anchor separately to the Dragon role.

| Relative index rule | From Sky Temple | From Cursed Hollow |
| --- | ---: | ---: |
| Soundtrack declarations | 201 | 195 |
| Include `Next` links | 196 | 195 |
| Include game-UI music and `Next` links | 195 | 195 |

The last rule gives positions 116, 166 and 174 for Sky, Dragon and Cursed respectively. Its calibration uses the two non-Dragon recordings. All 794 acknowledgements in 15 additional stock Dragon recordings carry the predicted 195. This was a retrospective comparison. Two other maps also independently illustrate the role binding. Tomb of the Spider Queen and Lost Cavern share `MX_LuxCrypt_Court_Intro` and all 134 of their acknowledgements carry 273.

These relative positions cover three specified source assets. The full catalog loading order and the game's absolute soundtrack table for GateOrder remain unresolved. The two anchors support the projection when GateOrder retains the stock link for this role. Replaying the recorded users and times adds a further condition because their audio-completion schedule under the target executable is unverified.

`verify_soundtrack_done.py` reads the 28-replay manifest, local map depot, GateOrder package, three catalog XML members, SoundLib and HeroesLib, and the pinned executable and static text. The manifest maps replay SHA-256 to a local path. The three catalog arguments are Core `SoundtrackData.xml`, HeroesData `GameUIData.xml` and HeroesData `SoundtrackData.xml`, in that order. The verifier reads each map by the handle in the recorded details and hashes the whole archive. It checks all 1,246 native frames against both codecs. `--frames` and `--rows` optionally save the TEN projection to new private files. The aggregate receipt includes the source ordinals, per-map counts and artifact digest.
