"""Witness the 98348 command link for Kael'thas' Arcane Barrier and the 41810 item commands it replaces.

In 41810 the Mana Addict reward is an inventory unit, KaelthasArcaneBarrierItem, and
TEN uses the second one (tag 217/5, player 4) through five SCmdEvent records with
ability link 365, command 3 and that item as the other unit. In 98348 the talent's
third rank grants the KaelthasArcaneBarrier button (Execute) once its 20-globe quest
completes. Across a manifest of genuine 98348 recordings this verifier requires a
candidate link to be issued only by Kael'thas players after their Mana Addict quest
completed, never by an incomplete, absent or other hero, with every activation burst
separated by the catalog cooldown. Command flags, sequence numbers and the target
simulation's own quest timing are not translated here.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import one, pinned, require
from initial_talent_tracker import HEROES, history, load_case
from predict_camp_captures import SOURCE

LINK = 385
SOURCE_LINK, SOURCE_COMMAND = 365, 3
ITEM = b"KaelthasArcaneBarrierItem"
LOOPS_PER_SECOND = 16
BURST = LOOPS_PER_SECOND
TEN_USES = [77929, 82528, 90313, 99691, 103345]


def catalog(kael):
    xml = ET.fromstring(pinned(kael, HEROES["HeroKaelthas"]))
    ranks = [n.get("value") for n in one(xml, "CTalent[@id='KaelthasManaAddict']/RankArray")]
    require(ranks[-1] == "KaelthasArcaneBarrierAbility", "Unexpected Mana Addict reward rank")
    button = one(xml, "CBehaviorAbility[@id='KaelthasArcaneBarrierAbility']/Buttons").attrib
    require(button.get("AbilCmd") == "KaelthasArcaneBarrier,Execute", "Unexpected reward command")
    cooldown = float(one(xml, "CAbilEffectInstant[@id='KaelthasArcaneBarrier']/Cost/Cooldown").get("TimeUse"))
    condition = one(xml, "CBehaviorTokenCounter[@id='KaelthasManaAddictQuestToken']/ConditionalEvents")
    require(condition.get("Compare") == "GE", "Unexpected quest comparison")
    return int(condition.get("CompareValue")), round(cooldown * LOOPS_PER_SECOND)


def bursts(loops):
    starts = []
    for loop in loops:
        if not starts or loop - last >= BURST:
            starts.append(loop)
        last = loop
    return starts


def stat_player(event):
    values = [x["m_value"] for x in event["m_intData"] if x["m_key"] == b"PlayerID"]
    require(len(values) == 1, "Stat event without one player")
    return values[0]


def recording(file, sha, quest, cooldown):
    protocol, raw, _, events = load_case(Path(file), sha, 98348)
    setup, heroes, _ = history(events)
    player_of = {user: player for user, (_, player) in setup.items()}
    hero_of = {player: hero for player, (_, hero) in heroes.items()}
    purchase, globes, uses = {}, defaultdict(list), defaultdict(list)
    for e in events:
        if e.get("m_eventName") == b"TalentChosen":
            name, = [s["m_value"] for s in e["m_stringData"] if s["m_key"] == b"PurchaseName"]
            if name == b"KaelthasManaAddict":
                purchase[stat_player(e)] = e["_gameloop"]
        elif e.get("m_eventName") == b"RegenGlobePickedUp":
            globes[stat_player(e)].append(e["_gameloop"])
    for g in protocol.decode_replay_game_events(raw):
        if g["_eventid"] == 27 and g.get("m_abil") and g["m_abil"]["m_abilLink"] == LINK:
            require(g["m_abil"]["m_abilCmdIndex"] == 0 and g["m_data"] == {"None": None} and g["m_otherUnit"] is None,
                    "Candidate link used with another command shape")
            uses[g["_userid"]["m_userId"]].append(g["_gameloop"])
    rows = []
    for player, hero in hero_of.items():
        loops = sorted(uses.get(next((u for u, p in player_of.items() if p == player), None), []))
        after = [t for t in globes[player] if player in purchase and t > purchase[player]]
        complete = after[quest - 1] if len(after) >= quest else None
        if loops:
            require(hero == "HeroKaelthas" and complete is not None and loops[0] > complete,
                    "Candidate link issued without a completed Mana Addict quest")
            starts = bursts(loops)
            require(all(b - a >= cooldown for a, b in zip(starts, starts[1:])), "Activation bursts violate the cooldown")
        if hero == "HeroKaelthas":
            rows.append(dict(player=player, purchase_loop=purchase.get(player), globes_after_purchase=len(after),
                             quest_complete_loop=complete, uses=len(loops), bursts=len(bursts(loops)),
                             first_use=loops[0] if loops else None))
    require(set(uses) <= set(player_of), "Candidate link issued by an unmapped user")
    return dict(sha256=sha, kaelthas=rows)


def source_uses(source, cooldown):
    protocol, raw, _, tracker = load_case(source, SOURCE, 41810)
    items = [e for e in tracker if e.get("m_unitTypeName") == ITEM]
    require([(e["m_unitTagIndex"], e["m_unitTagRecycle"], e["m_controlPlayerId"], e["_gameloop"]) for e in items] ==
            [(182, 1, 7, 355), (217, 5, 4, 1217)], "Unexpected source reward items")
    tags = {(e["m_unitTagIndex"] << 18) | e["m_unitTagRecycle"]: e for e in items}
    games = list(protocol.decode_replay_game_events(raw))
    referencing = [i for i, g in enumerate(games) if g["_eventid"] == 27 and g.get("m_otherUnit") in tags]
    require(referencing == TEN_USES, "Unexpected source item commands")
    rows = [games[i] for i in referencing]
    require(all(g["m_abil"]["m_abilLink"] == SOURCE_LINK and g["m_abil"]["m_abilCmdIndex"] == SOURCE_COMMAND and
                g["m_data"] == {"None": None} and g["m_otherUnit"] == (217 << 18 | 5) and g["_userid"]["m_userId"] == 3 and
                g["_gameloop"] > 1217 for g in rows), "Unexpected source item command shape")
    loops = [g["_gameloop"] for g in rows]
    require(all(b - a >= cooldown for a, b in zip(loops, loops[1:])), "Source uses violate the cooldown")
    return dict(ordinals=referencing, loops=loops, user=3, player=4, item_tag=[217, 5], item_birth_loop=1217,
                flags=sorted({g["m_cmdFlags"] for g in rows}), sequences=[g["m_sequence"] for g in rows])


def verify(source, kael, manifest):
    quest, cooldown = catalog(kael)
    cases = json.loads(manifest.read_bytes())
    observed = [recording(file, sha, quest, cooldown) for file, sha in cases]
    kael_rows = [r for o in observed for r in o["kaelthas"]]
    positives = [r for r in kael_rows if r["uses"]]
    require(len(positives) >= 2, "Too few native activations")
    require(any(r["purchase_loop"] is not None and r["quest_complete_loop"] is None for r in kael_rows),
            "No incomplete-quest negative control")
    ten = source_uses(source, cooldown)
    return dict(target_link=LINK, target_command=0, target_other_unit=None, source_link=SOURCE_LINK,
                source_command=SOURCE_COMMAND, quest_target_globes=quest, cooldown_loops=cooldown,
                recordings=len(cases), recordings_with_kaelthas=sum(1 for o in observed if o["kaelthas"]),
                kaelthas_players=len(kael_rows), activating_players=len(positives),
                activations=sum(r["uses"] for r in positives), activation_bursts=sum(r["bursts"] for r in positives),
                incomplete_quest_players=sum(1 for r in kael_rows if r["purchase_loop"] is not None and r["quest_complete_loop"] is None),
                no_purchase_players=sum(1 for r in kael_rows if r["purchase_loop"] is None), controls=observed, ten=ten,
                translated_flags=False, translated_sequences=False, target_quest_timing_verified=False,
                inserted_into_sparse_stream=False, verified_target_syncs=0)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("source", "kael", "manifest"):
        cli.add_argument(name, type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())), indent=2))
