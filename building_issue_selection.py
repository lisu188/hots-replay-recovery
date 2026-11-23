"""Measure earlier selection evidence for the 39 historical GateOrder building issues."""

import argparse
from collections import Counter
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from hero_camera_lifetimes import core_horizon, independent_histories, lobby_predictions, recorded_histories
from hero_revive_wire import source_curve
from implicit_building_issues import generate
from match_selections import CONTROL_RECEIPT, at, opening_members, pinned, plan, remove_items
from opening_birth_wire import target_protocol
from repair_unit_tags import components


def audit(source, gate_map, mechanics, catalog, curve, selection_controls):
    issues, _, _ = generate(source, gate_map, mechanics, catalog)
    pinned(selection_controls, CONTROL_RECEIPT)
    summary, stream, _ = plan(source, gate_map, mechanics, curve, json.loads(selection_controls.read_bytes()), 98348)
    known = {r["game_event_ordinal"]: e for r, e in zip(
        (r for r in summary["rows"] if r["admitted"]), target_protocol().decode_replay_game_events(stream), strict=True
    )}
    protocol, raw_tracker, end = read_tracker(source, 41810)
    users, raw_game, _ = opening_members(source, protocol, 41810)
    tracker = list(protocol.decode_replay_tracker_events(raw_tracker))
    cutoff = core_horizon(tracker, end)
    lives = independent_histories(lobby_predictions(source, 41810), tracker, source_curve(curve), cutoff)
    observed = recorded_histories(tracker)
    if any((slot, unit, events) != (*observed[k][:2], [r for r in observed[k][2] if r[0] <= cutoff])
           for k, (slot, unit, events) in lives.items()):
        raise ValueError("Primary-hero lifetime differs between tracker and independent timer")
    selections, counts = {}, Counter()
    uninterrupted = []
    for i, e in enumerate(protocol.decode_replay_game_events(raw_game)):
        user, tick = e["_userid"]["m_userId"], e["_gameloop"]
        if e["_eventid"] == 28:
            if i not in known:
                selections[user] = None
                continue
            d = known[i]["m_delta"]
            prev = selections.get(user, (0, []))
            if prev is None and d["m_removeMask"] != {"ZeroIndices": []}:
                raise ValueError("Accepted selection depends on unknown prior membership")
            retained = remove_items(prev[1] if prev else [], d["m_removeMask"])
            selections[user] = (tick, sorted(set(retained + d["m_addUnitTags"])))
        elif i in issues:
            selection = selections.get(user)
            if selection is None:
                counts["previous_selection_unresolved"] += 1
                continue
            since, tags = selection
            if len(tags) != 1 or components(tags[0], 22) not in lives:
                counts["previous_selection_other_than_primary_hero"] += 1
                continue
            slot, _, life = lives[components(tags[0], 22)]
            if slot != users.get(user):
                raise ValueError("Selected primary hero belongs to another user")
            when = at(life, tick)
            if when and when[0] < since <= tick and when[1]:
                counts["single_primary_hero_continuously_alive_since_accepted_selection"] += 1
                uninterrupted.append(i)
            else:
                counts["primary_hero_selection_with_intervening_lifetime_boundary"] += 1
    if counts.total() != len(issues):
        raise ValueError("Incomplete issue inventory")
    return dict(issues=len(issues), categories=dict(counts), uninterrupted_source_ordinals=uninterrupted,
                target_command_execution_verified=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "gate_map", "mechanics", "catalog", "curve", "selection_controls"):
        p.add_argument(arg, type=Path)
    print(json.dumps(audit(**vars(p.parse_args())), indent=2))
