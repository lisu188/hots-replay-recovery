"""Check Symbiote selections and project independently witnessed, targetless commands."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path
from xml.etree import ElementTree

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as encode_named
from first_sync_game import game
from first_sync_selections import opening_members
from match_selections import at, mask_key, remove_items, timeline
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from unit_slot_pool import UnitSlotPool


CONTROL = "afcf49a656068f343173fc79afff2d2ebf15066f531cb192382cdba9d1ea3272"
XML = "b2ecee56c24e3a6e62c904f066f858dd5fb9fa144c2e17af423320efaf9c69e1"
SYM = "AbathurSymbiote"
HERO = "HeroAbathur"


def catalog(xml):
    data = xml.read_bytes()
    if sha256(data).hexdigest() != XML:
        raise ValueError("Unexpected target unit catalog")
    root = ElementTree.fromstring(data)
    cancel = "AbathurAssumingDirectControlCancel"
    unit = root.find(f".//CUnit[@id='{SYM}']")
    ability = root.find(f".//CAbilEffectInstant[@id='{cancel}']")
    effect = root.find(f".//CEffectSet[@id='{cancel}Set']")
    if (unit.find(f"AbilArray[@Link='{cancel}']") is None
            or unit.find(f"CardLayouts/LayoutButtons[@AbilCmd='{cancel},Execute'][@Face='AbathurSymbioteCancel']") is None
            or ability.find("CmdButtonArray[@index='Execute'][@DefaultButtonFace='AbathurSymbioteCancel']") is None
            or ability.find(f"Effect[@value='{cancel}Set']") is None
            or effect.find("EffectArray[@value='SymbioteCancelSearch']") is None
            or root.find(".//CEffectEnumArea[@id='SymbioteCancelSearch']/AreaArray[@Effect='SymbioteRemoveHostBehavior']") is None):
        raise ValueError("Unrecognized instant cancel path")


def target_frame(event, previous, protocol):
    kind = event["_eventid"]
    tid, name = protocol.game_event_types[kind]
    payload = {k: v for k, v in event.items() if not k.startswith("_")}
    if name != event["_event"]:
        raise ValueError("Target event declaration differs")
    dt = event["_gameloop"] - previous
    native = GameEvent(dt, event["_userid"]["m_userId"], kind, _anonymous(payload, protocol.typeinfos, tid))
    data = encode_game_events([native])
    (decoded,) = iter_game_events(data)
    if decoded.event != native or data != encode_named([{**event, "_gameloop": dt}], protocol):
        raise ValueError("Target frame writers disagree")
    return data


def closed_prefix(tracker, first, recorded_tag, hero):
    births = [(e["_gameloop"], (e["m_unitTagIndex"], e["m_unitTagRecycle"]), e["m_unitTypeName"])
              for e in tracker if e["_eventid"] in (1, 6) and e["_gameloop"] < first]
    gates = [e["m_unitTagIndex"] for e in tracker if e["_eventid"] == 2 and e["_gameloop"] == 610]
    if len(gates) != 54 or len(set(gates)) != 54 or any(e["_eventid"] == 2 and e["_gameloop"] != 610
            for e in tracker if e["_gameloop"] < first):
        raise ValueError("Unexpected gate release observations")
    early = [tag for loop, tag, name in births if loop < 610]
    reused = [(tag, name) for loop, tag, name in births if loop >= 610]
    if early != [(i, 1) for i in range(183)]:
        raise ValueError("Earlier recorded allocations are not consecutive")
    types = Counter(n.decode() for _, n in reused)
    taken = [idx for (idx, gen), _ in reused if gen == 2]
    unused = sorted(set(gates) - set(taken))
    if (len(reused), len(set(taken)), len(taken), len(unused)) != (46, 46, 46, 8) or not all(i in gates for i in taken):
        raise ValueError("Unexpected consumed opening slots")
    outcomes = []
    # The native model takes retirements, not tracker deaths. Reproduce every earlier
    # observed birth under three possible retirement/allocation histories.
    recorded_slot, generation = recorded_tag
    if recorded_slot not in unused or generation != 2:
        raise ValueError("First Symbiote did not reuse a remaining blocker")
    recorded_first = [recorded_slot] + [i for i in unused if i != recorded_slot]
    for tail, hidden in [(recorded_first, 0), (recorded_first[::-1], 0), (recorded_first, len(unused))]:
        pool = UnitSlotPool()
        if [pool.allocate() for _ in early] != early:
            raise ValueError("Initial allocations differ")
        for idx in taken + tail:
            pool.retire((idx, 1))
        pool.drain()
        if [pool.allocate() for _ in reused] != [tag for tag, _ in reused]:
            raise ValueError("Earlier visible allocations differ")
        for _ in range(hidden):
            pool.allocate()
        outcomes.append(pool.allocate())
    if not (outcomes[0] == recorded_tag and outcomes[0] != outcomes[1] and max(outcomes[:2]) < hero < outcomes[2]):
        raise ValueError("Cannot demonstrate both possible positions of the dynamic tag")
    return dict(consecutive_early_births=len(early), gate_deaths=len(gates), subsequent_visible_births=types,
                remaining_gate_slots_without_omissions=len(unused), histories_checked=len(outcomes),
                hidden_allocations_in_opposite_order_example=len(unused),
                first_positional_removal_can_retain_different_unit=True)


def analyze(path, digest, build):
    protocol, raw_game = game(path, digest, build)
    users, _, raw_tracker = opening_members(path, protocol, build)
    tracker = list(protocol.decode_replay_tracker_events(raw_tracker))
    if sum(e["_bits"] for e in tracker) != len(raw_tracker) * 8:
        raise ValueError("Incomplete tracker stream")
    lives = timeline(tracker)
    (hero,) = [k for k, life in lives.items() if life[0][1] == HERO]
    owner = lives[hero][0][2]
    (user,) = [u for u, player in users.items() if player == owner]
    link, flags, bits = {41810: (165, 0x100100, 18), 98348: (190, 0x2080100, 22)}[build]
    selected, deaths = {}, {}
    before = []
    candidates = []
    offset = previous = 0
    removal_count = unconditional = resets = 0
    after_removals = Counter()
    for ordinal, e in enumerate(protocol.decode_replay_game_events(raw_game)):
        size, rest = divmod(e["_bits"], 8)
        tick = e["_gameloop"]
        if rest or not size or tick < previous:
            raise ValueError("Invalid event boundary")
        frame = raw_game[offset:offset+size]
        is_own = e["_userid"]["m_userId"] == user
        if is_own and e["_eventid"] == 28:
            delta = e["m_delta"]
            mask = delta["m_removeMask"]
            adds = [(tag >> bits, tag & ((1 << bits) - 1)) for tag in delta["m_addUnitTags"]]
            for tag in adds:
                states = lives.get(tag, [])
                state = at(states, tick)
                if state and state[1] == SYM and state[3] and state[2] == owner:
                    if (tag in selected or states[0][1] != SYM or states[-1][3]
                            or states[-1][0] in deaths or not states[0][0] < tick < states[-1][0]):
                        raise ValueError("Ambiguous selected Symbiote lifetime")
                    selected[tag] = tick
                    deaths[states[-1][0]] = tag
            if build == 41810:
                if e["m_controlGroupId"] != 10:
                    raise ValueError("Unexpected historical bank")
                retained = remove_items(before, mask)
                if not adds:
                    removal_count += 1
                    unconditional += all(set(remove_items(order, mask)) == set(retained) for order in permutations(before))
                    after_removals["hero_only" if retained == [hero] else "other"] += 1
                before = sorted(set(retained + adds))
            elif adds == [hero] and mask_key(mask) == ("ZeroIndices",) and delta["m_subgroupIndex"] == 0:
                if target_frame(e, previous, protocol) != frame:
                    raise ValueError("Target reset differs from physical bytes")
                resets += 1
        if is_own and e["_eventid"] == 27 and (e["m_abil"] or {}).get("m_abilLink") == link:
            candidates.append((ordinal, previous, e, frame))
        previous, offset = tick, offset + size
    if offset != len(raw_game):
        raise ValueError("Incomplete game stream")
    accepted = []
    distances, all_distances = Counter(), Counter()
    for ordinal, prior, e, frame in candidates:
        tick = e["_gameloop"]
        near = [d for d in (0, 1) if tick + d in deaths and selected[deaths[tick+d]] <= tick]
        all_distances["unmatched" if not near else str(near[0])] += 1
        if not near:
            continue
        if (len(near) != 1 or e["m_cmdFlags"] != flags
                or e["m_abil"] != {"m_abilLink": link, "m_abilCmdIndex": 0, "m_abilCmdData": None}
                or e["m_data"] != {"None": None} or e["m_otherUnit"] is not None or e["m_unitGroup"] is not None
                or e.get("m_vector") is not None or type(e["m_sequence"]) is not int):
            raise ValueError("Unexpected anchored command layout")
        if encode_named([{**e, "_gameloop": tick-prior}], protocol) != frame:
            raise ValueError("Original command frame differs")
        if build == 98348 and target_frame(e, prior, protocol) != frame:
            raise ValueError("Physical target command differs")
        distances[str(near[0])] += 1
        accepted.append((ordinal, prior, e))
    first = min(selected, key=selected.get)
    first_tick = lives[first][0][0]
    rec = dict(build=build, replay_sha256=digest, selected_lifetimes=len(selected),
               selection_delay=dict(sorted(Counter(t-lives[tag][0][0] for tag,t in selected.items()).items())),
               observed_command_link=link, flags=hex(flags), all_same_link_by_death_delay=all_distances,
               matched_command_counts_by_death_delay=distances)
    if build == 41810:
        rec.update(removal_only=removal_count, removal_poststates=after_removals,
                   positional_removals_correct_for_every_possible_numeric_order=unconditional,
                   first_symbiote=dict(birth=first_tick, selection=selected[first], death=lives[first][-1][0],
                                       source_index=first[0], source_generation=first[1],
                                       previous_slot_history=lives[first[0],first[1]-1]),
                   preceding_allocations=closed_prefix(tracker,first_tick,first,hero))
    else:
        rec["observed_full_replacements_selecting_primary_abathur"] = resets
    return rec, accepted


def generate(source, control, xml):
    catalog(xml)
    reference, _ = analyze(control, CONTROL, 98348)
    original, rows = analyze(source, SOURCE, 41810)
    if (original["selected_lifetimes"], reference["selected_lifetimes"],
            original["matched_command_counts_by_death_delay"], reference["matched_command_counts_by_death_delay"]
            ) != (69, 84, {"1": 49}, {"1": 62, "0": 4}):
        raise ValueError("Unexpected paired command reference")
    encoded, keys = bytearray(), []
    previous = 0
    protocol = target_protocol()
    modern = []
    for ordinal, prior, old in rows:
        e = {**old, "m_abil": {**old["m_abil"], "m_abilLink":reference["observed_command_link"]},
             "m_cmdFlags":int(reference["flags"], 16), "m_vector": None}
        modern.append(e)
        encoded.extend(target_frame(e, previous, protocol))
        previous = e["_gameloop"]
        keys.append(dict(ordinal=ordinal, loop=previous, enclosing_sha256=sha256(target_frame(e,prior,protocol)).hexdigest()))
    decoded = list(protocol.decode_replay_game_events(encoded))
    if (len(decoded) != len(modern) or sum(e["_bits"] for e in decoded) != len(encoded)*8
            or any({k:v for k,v in a.items() if k!="_bits"} != {k:v for k,v in b.items() if k!="_bits"}
                   for a,b in zip(decoded,modern,strict=True))):
        raise ValueError("Sparse target command stream differs")
    receipt = dict(original=original, reference=reference, target_catalog_sha256=XML,
                   frames=len(keys), bytes=len(encoded), sha256=sha256(encoded).hexdigest(),
                   first_loop=keys[0]["loop"], last_loop=keys[-1]["loop"],
                   command_selection_and_simulation_verified=False, numeric_catalog_index_statically_resolved=False)
    return bytes(encoded), receipt, keys


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "control", "abathur_xml"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--ledger", type=Path)
    args = cli.parse_args()
    data, report, keys = generate(args.source,args.control,args.abathur_xml)
    if args.output:
        with args.output.open("xb") as out:
            out.write(data)
    if args.ledger:
        with args.ledger.open("x",encoding="utf-8") as out:
            print(json.dumps(keys,indent=2), file=out)
    print(json.dumps(report,indent=2))
