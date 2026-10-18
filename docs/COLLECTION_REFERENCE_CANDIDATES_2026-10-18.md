# Exact current collection references and remaining ambiguity

The complete pinned 98348 XML scan succeeded in [run 39160460385](https://github.com/lisu188/hots-replay-recovery/actions/runs/39160460385). It checked all 5,575 projected XML files and 79,556,009 XML bytes against the earlier exact current projection. The report contains 238 exact references for 63 of the 207 unresolved legacy collection names. Its role counts are 166 visual/audio references, 58 other literal references, 8 catalog record IDs and 6 reward IDs. No named reward-alias field was observed. This covers the projected gamedata XML inventory, rather than arbitrary binary, server-side or constructed data.

The derived candidate report retains every contributing match index, declaration index, source path/digest, XML ordinal and unresolved flag. Independent root review reproduced the JSON and separately recalculated parent-child/reward joins and global identity counts. These checks do not resolve inheritance, catalog order, ownership or the old collection field's semantics.

## Visual families

Thirty-three old names occur under 32 skin owners and 1 mount owner. Those exact owners have no direct RequiredRewardArray or same-ID typed reward declaration. Following explicit child.parent literals across the entire projected inventory yields 121 distinct direct License candidates, all in the observed current 5418-ID set.

| Old-name families | Direct License candidates per family |
|---|---:|
|16|3|
|12|4|
|5|5|

Restricting children to the same file produces 33 apparent singletons. Including variants declared in other files removes that uniqueness in every family. All 121 child records retain unresolved-parent flags. Global (type, id) checks find exactly one declaration for each of the 121 child IDs and 121 typed reward IDs, with no cross-file duplicates in those groups. None of these facts chooses a variant or proves a legacy ownership conversion.

## Separate HyperlinkId chains

Five current loadout records have an exact old-name HyperlinkId and a direct RequiredRewardArray whose typed reward is declared in the same file:

| Legacy literal | Current record | Typed reward | Direct License |
|---|---|---|---:|
|IllidansNightmare|IllidanHorse|CRewardMount|18448|
|GoldenCyberWolf|CyberWolfGold|CRewardMount|18427|
|WonderBillie|BillieGoat|CRewardMount|18538|
|PiggyBank|MoneyPig|CRewardMount|18490|
|MechaDehaka|DehakaMecha|CRewardSkin|18008|

All five Licenses occur in the current set, with no duplicate global reward-License declaration. The five loadout IDs and five typed reward IDs each have exactly one global declaration. All five loadout records retain unresolved parents; BillieGoat's reward parent is unresolved too. HyperlinkId is a separate current field whose equality to an old collection name is not authenticated legacy-alias semantics. These remain source-reference candidates.

## Unit identity scope

The same complete XML scan found zero direct CUnit declarations for NovaHoloCloneCloaked, one each for NovaHoloClone and AbathurEvolvedMonstrosity, and eight for TownCannonTowerL2Standalone, including a Dragon Shire override. This narrows static presence questions. It supplies no numeric unit link or runtime replacement rule.

## Reproduction and state

Sources are observations/collection-alias-nodes-current-98348.json and observations/collection-license-current-98348.json, bound to their exact hashes by the research helper under research/collection-alias-98348/. Its fixed recorded repository path and task-work output directory are research setup assumptions. Import measure(repo_path) with the repository on PYTHONPATH to reproduce the semantic JSON without writing output. No parser or game data is fetched by this analysis. The report records the exact producer helper hash.

The existing 56 exact reward-name candidates remain unchanged, and all 207 previously unresolved names remain unresolved for conversion. No alias is registered, no availability/player/synchronization data is changed and no replay is produced. R8 remains the latest experimental replay. The full replay upgrade and deterministic playback remain unfinished, under the user's continuing no-client-launch instruction.
