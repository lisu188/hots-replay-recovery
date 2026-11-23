# Nova Covert Ops on the optional historical-rule map

The 2,203,389-byte Nova map built from PerfectAim has SHA-256 `8b0cdec389be8a7cc52b438e9798af5903158a59a426d9ab3e08f166e791fd8f`. Two builds compared byte for byte. In the independently combined Brightwing and Nova map the same Nova records resolve under SHA-256 `13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1`.

The map adds `NovaMasteryCovertOpsPinningShot` at the source's tier 1, column 4, selector 3. All 21 retail cells keep their talent, tier and column. The first three retain their indices. Later retail Nova selectors shift by one. TEN made no earlier Nova selection. The added talent has a distinct face and tooltip in enUS and plPL. The three other first-tier cells belong to the target build. Modern Covert Ops and the experimental historical choice are mutually exclusive first-tier choices under ordinary match rules.

The intended 2016 rule consumes 65 mana, begins with a 40% slow and adds two percentage points per second of cloak, up to 60%. A custom driver attached through Nova's stock cloaked periodic effect grants up to ten stacks. After decloaking, the model retains them for one second and cancels expiry on recloak. Launch records the level on the missile, and impact applies the corresponding 2.25-second slow. This experimental branch is limited to the selected talent on the real HeroNova. The ordinary target Holo Decoy branch remains in place. English and Polish tooltips describe the new talent. Other locales were not reconstructed.

Timing starts at the first eligible target cloak callback after purchase. Historical passive state before purchase, the exact boundary ordering of simultaneous expiry and recloak, decoy interactions, visuals, engine execution and the applicability of the documented October 2016 stuck-stack defect to TEN are unresolved. These limit historical fidelity. The offline interpreter distinguishes ten stack increments, cap, grace, cancellation, expiration, two ineligible conditions and eleven missile snapshots in flight. It uses an explicit ordering of cloak checks and expiry. A second reader, Heroes.XmlData 1.1.1 with Heroes.MpqTool, loaded both actual archives and resolved all 22 Nova cells, ten slow levels, cost and the launch/impact path.

The source first selected Nova's talent at game ordinal 844, loop 133. The map's selected link predicts tracker ordinal 245, loop 134. Both target-encoded frames match the respective physical original bytes with original time deltas. As standalone streams with absolute loops they occupy 8 and 110 bytes. One independent 41810 Nova selection and award matched the historical name, and two stock 98348 Nova first-tier selections and awards validated the corresponding retail alternative. This projection assumes the selection is accepted under the ordinary target tier and column path. All private fragment files remain separate from the original replay.

```text
python build_nova_intended_map.py PERFECT_AIM NOVA_XML SONYA_XML ABATHUR_XML OLD_HEROES_JSON NEW_MAP --stormlib LIBSTORM
python check_nova_rule.py NEW_MAP NOVA_XML
python project_nova_choice.py TEN NEW_MAP NOVA_XML GAMELIB PRIVATE_62_CASE_MANIFEST --output NEW_FRAGMENT_DIRECTORY
./read_nova_catalog.ps1 -Map NEW_MAP -NovaXml NOVA_XML -LibraryDirectory DLL_DIRECTORY -MpqToolDll MPQ_DLL -CascLibDll CASC_DLL
```

The historical evidence is in [Nova source and control observations](https://github.com/lisu188/hots-replay-recovery/blob/main/docs/NOVA_HISTORICAL_EFFECTS.md). The builder checks the PerfectAim archive and four source digests. The two proof tools also recognize the combined archive. `nova-intended-map.json` records the changed resources, including the appended localized strings. This branch supplies conditional input and tracker fragments. Complete replay or native playback compatibility remains unverified.
