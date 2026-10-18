# Static registries and current access APIs

The installed `2.57.0.98348` HeroesLib source implements access checks through
reward catalog links. It does not establish how to translate the old name
registry into current License IDs, or what the per-entry 32-byte records mean.

The fresh package check confirms original HeroesData field23 has264 raw strings
and263 first-occurrence names, exactly matching the original/R8 catalog-only
observation. Current exact US HeroesData field24 has5497 raw integers and5418
first-occurrence IDs, exactly matching two current catalog-only observations.
The requested examples `NovaHoloCloneCloaked`, `AbathurEvolvedMonstrosity` and
`TownCannonTower` are **absent** from the authenticated old263 registry. Do not
use those examples to infer the registry's meaning.

Disjoint lexical counts over the actual263 names are145 containing the literal
`Skin`,8 other names containing `Mount`, and110 remaining names. Examples from
the source order are `LunaraSkinMaster`/`StitchesSkinPsycho`,
`AzmodunkMount`/`2015WorldChampionshipMount`, and
`Reigndeer`/`GoldenLunarTiger`/`Kaelthas`. These are spelling rules, not recovered
historical catalog types or ownership categories.

Four functions in current HeroesLib are material:

- `libCore_gf_MetagameIsHeroInRotationForPlayer`, lines2344–2377, counts additional
  rotation slots through `PlayerHasReward` and `Config.FreeToPlayRewardArray`.
- `libCore_gf_MetagameDoesPlayerHaveAccessToHero`, lines2403–2438, checks required
  rewards and also has AI/human, rotation, practice, freebie, TryMe and offline
  branches.
- The corresponding skin and mount functions, lines2440–2467 and2469–2495,
  check required rewards with first-entry/free-play and debugging branches.

The API receives reward catalog strings. These script bodies do not implement
the native reward check or bind it to a particular availability bit/slot.
Access and personal purchase/ownership remain separate questions. No old alias,
207-name mapping, ownership projection or default value is added.

The complete installed HeroesLib bytes have Git blob identity
`0cf700ed3ae8e5b6dff5c812d2de9bddd7899b0b`, equal to the blob returned for
[the pinned public source](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/e3e57cb640f18002a4feebe3872cefe04072d814/mods/heroesdata.stormmod/base.stormdata/triggerlibs/heroeslib.galaxy#L2403).
Installed ConfigData likewise matches public Git blob
`f63298d1a04a7148ca6b32cc161a2eed82da5152`; its
[four rotation reward links](https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/e3e57cb640f18002a4feebe3872cefe04072d814/mods/heroesdata.stormmod/base.stormdata/gamedata/configdata.xml#L1065)
are directly observed. This is an actual installed-file binding, rather than
assuming that the public repository's branch denotes the installed build.

Bounded exact-symbol searches found no qualifying HotS41810 CUnitLicense or
native implementation. Separate SC2 game data declares integer License,
string entity-access and string reward functions; those declarations are not
evidence for an exact historical HotS transition. The three Core helper texts
contain none of the searched license/reward/entitlement/collection terms; they
are not the complete engine-native declaration inventory.

## Read-only acquisition and limits

The unchanged managed CascLib DLL and previously staged configuration copies
from `work/casc-feasibility` were reused. The reviewed parent workflow lives in
`research/installed-casc-98348` in the repository. Separate derived helpers are
saved here with their actual executed hashes. They retain machine-specific
paths and partial internal MNDX setup and are research sources, not a portable
supported CLI. Do not overwrite or rerun them against existing result names.

Each filename inventory examined1,208,637 MNDX names. Only six confirmed text
members were subsequently read, totaling779,428 bytes against limits of8 files
and2MiB total. Their complete MD5 values match CASC CKeys. All four operations
matched decoded root `c3b3c8bc82e3a5a62e550fdde9a40c28`, passed the denying-HTTP
canary, recorded zero transport attempts, disabled cache/fallback, and retained
installed configuration hashes. Loader ReadWrite access is confined to the
existing small task configuration copies; installed data/index streams use
explicit read access. Logs, temporary state and outputs are task-local.

The known partial-private-path `Clear()` NullReferenceException is retained in
each operation report. It is not reported as a successful normal public
storage lifecycle. No client was launched, replay read or modified, player or
availability value examined, or further header recipe attempted.

Publish only the allowlisted research sources, operation digests and sanitized
findings. The six extracted game text files stay private. The report generator
also reads already existing private static headers to reproduce the registry
checks; it creates no header body and exports no complete registry or account
data.
