"""Return TEN ping projections and tier-qualified talent index candidates by physical input ordinal."""

from collections import Counter
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path

import first_sync_game
from convert_historical_pings import generate as project_map_pings
from hero_revive_wire import GATE_MAP
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from primary_hero_pings import generate as project_pings, locate_base


ACTIVE_TIERS = "c2cd58e105fb612fcac4ec557104da02f0f005440586549e62ab3ab45416023f"


def extra_rows(source, gate_map, original_map, ping_controls):
    """Each returned tuple contains the global ordinal, target event and evidence label."""
    if sha256(gate_map.read_bytes()).hexdigest() != GATE_MAP:
        raise ValueError("Expected GateOrder")
    target = target_protocol()
    old, raw = first_sync_game.game(source, SOURCE, 41810)
    pings, talents = [], []
    prior = 0
    for ordinal, event in enumerate(old.decode_replay_game_events(raw)):
        kind, loop = event["_eventid"], event["_gameloop"]
        if kind == 36:
            pings.append((ordinal, event))
        if kind == 110:
            talents.append((ordinal, prior, event))
        prior = loop

    map_data, map_report = project_map_pings(source,original_map,gate_map)
    all_data, ping_report = project_pings(source,original_map,gate_map,ping_controls)
    ping_events = [r for _,r in pings]
    base = locate_base(ping_events,map_data)
    all_pings = locate_base(ping_events,all_data)
    if (not base.items() <= all_pings.items() or len(base) != map_report["emitted"]
            or len(all_pings) != ping_report["emitted"] or ping_report["base_sha256"] != sha256(map_data).hexdigest()):
        raise ValueError("Grounded map and hero ping projections disagree")
    rows = [(pings[i][0], row, "ping_map_or_no_target" if i in base else "ping_opening_hero_lifetime")
            for i,row in zip(sorted(all_pings),target.decode_replay_game_events(all_data),strict=True)]

    studies = Path(first_sync_game.__file__).resolve().parent / "observations"
    projector = import_module("research.dragon-talents.project_target_frames")
    candidates, frames = projector.project_target_frames(source,studies/"target-talent-tree-98348.json",
                                                         studies/"supplemental-target-talent-witnesses-98348.json")
    active = (studies/"active-tier-awards-98348.json").read_bytes()
    if sha256(active).hexdigest() != ACTIVE_TIERS:
        raise ValueError("Unrecognized active-tier evidence")
    study = json.loads(active)["source"]
    if (study["replay_sha256"] != SOURCE or candidates["source_sha256"] != SOURCE
            or candidates["replay_application_eligible"] or study["scoped_awards"] != len(talents)):
        raise ValueError("Unexpected target-index or historical tier evidence")
    unresolved_prior = set()
    dispositions = Counter()
    for (ordinal,prior,original), wire, tier in zip(talents,candidates["selections"],study["selections"],strict=True):
        tick, user = original["_gameloop"], original["_userid"]["m_userId"]
        if ((ordinal,tick) != (wire["ordinal"],wire["loop"]) or
                any(wire[k]!=tier[k] for k in ("ordinal","loop","hero","purchase")) or
                original["m_index"] != wire["source_index"]):
            raise ValueError("Talent studies refer to different source inputs")
        frame = frames.get(ordinal)
        if frame is None or tier["status"] != "same_tier":
            unresolved_prior.add(user)
            dispositions["no_target_index_witness" if frame is None else "witnessed_index_tier_conflict"] += 1
            continue
        row, = target.decode_replay_game_events(frame)
        if ((row["_eventid"],row["_userid"],row["_gameloop"],row["m_index"],row["_bits"]) !=
                (110,original["_userid"],tick-prior,wire["direct_position"],len(frame)*8)):
            raise ValueError("Isolated target frame disagrees with its source envelope or target index")
        reason = ("talent_index_requires_earlier_unresolved_award" if user in unresolved_prior
                  else "talent_index_requires_target_award_state")
        rows.append((ordinal,{**row,"_gameloop":tick},reason))
        dispositions[reason] += 1
    if (len(pings),len(talents),len(base),len(all_pings),len(frames),dispositions["witnessed_index_tier_conflict"]) != (81,70,59,72,22,3):
        raise ValueError("Unexpected coverage for the pinned replays")
    return sorted(rows,key=lambda r:r[0]), dict(map_or_no_target_pings=59,confirmed_opening_hero_pings=13,
        historical_hero_timer_reference_sha256=ping_report["reference_digests"],ping_sparse_sha256=ping_report["sha256"],
        isolated_talent_witnesses=22,talent_dispositions=dict(dispositions),active_tier_sha256=ACTIVE_TIERS,
        target_awards_and_effects_verified=False,retained_r8_tracker_used=False)
