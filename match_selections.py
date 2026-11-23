"""Audit and convert TEN selection deltas with physical catalog, tag and removal witnesses."""

from bisect import bisect_right
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from itertools import repeat
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from encoders import encode_game_events as named_encode
from first_sync_selections import encode_frame, opening_members, SELECTION
from hero_camera_lifetimes import core_horizon, independent_histories, lobby_predictions
from hero_revive_wire import source_curve
from native_game_events import iter_game_events
from opening_birth_wire import model, target_protocol
from predict_camp_captures import SOURCE

WANTED = {
    "AbathurSymbiote",
    "AbathurEvolvedMonstrosity",
    "VehicleDragon",
    "HeroKaelthas",
    "HeroGreymane",
    "HeroFaerieDragon",
    "HeroAnubarak",
    "HeroTyrande",
    "HeroAbathur",
    "HeroNova",
    "HeroBarbarian",
}
CONTROL_RECEIPT = "e03bd87bdba8ed46fd5af9eb4cb490be59234f0a2bb61aefdd3daa75c087c935"


def pinned(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Replay hash mismatch")


def stream(protocol, game):
    prior = offset = 0
    selections = []
    group_updates = 0
    for ordinal, e in enumerate(protocol.decode_replay_game_events(game)):
        size, rest = divmod(e["_bits"], 8)
        tick = e["_gameloop"]
        if rest or size <= 0 or offset + size > len(game) or tick < prior:
            raise ValueError("Invalid game frame")
        if e["_event"] == SELECTION:
            if e["_eventid"] != 28:
                raise ValueError("Unexpected selection event ID")
            selections.append((ordinal, e, prior, game[offset : offset + size]))
        elif e["_event"].endswith(".SControlGroupUpdateEvent"):
            group_updates += 1
        offset += size
        prior = tick
    if offset != len(game):
        raise ValueError("Incomplete game member")
    return selections, group_updates


def timeline(tracker):
    changes = defaultdict(list)
    for e in tracker:
        kind = e["_eventid"]
        if kind not in (1, 2, 3, 4, 6, 12):
            continue
        key = e["m_unitTagIndex"], e["m_unitTagRecycle"]
        seq = changes[key]
        if kind in (1, 6):
            if seq:
                raise ValueError("Repeated generation birth")
            unit, owner, alive = e["m_unitTypeName"].decode("ascii"), e["m_controlPlayerId"], True
        elif not seq:
            continue
        else:
            _, unit, owner, alive = seq[-1]
            if kind == 2:
                alive = False
            elif kind == 12:
                alive = True
            elif kind == 3:
                owner = e["m_controlPlayerId"]
            else:
                unit = e["m_unitTypeName"].decode("ascii")
        seq.append((e["_gameloop"], unit, owner, alive))
    return changes


def at(seq, tick):
    i = bisect_right(seq, tick, key=lambda a: a[0])
    return seq[i - 1] if i else None


def groups(delta):
    tags = delta["m_addUnitTags"]
    rows = [g for g in delta["m_addSubgroups"] for _ in repeat(None, g["m_count"])]
    if len(tags) != len(rows) or any(g["m_count"] < 1 for g in delta["m_addSubgroups"]):
        raise ValueError("Subgroup count differs from added tags")
    return zip(rows, tags)


def mask_key(mask):
    ((kind, value),) = mask.items()
    if kind == "None" and value is None:
        return (kind,)
    if kind == "Mask" and isinstance(value, tuple) and len(value) == 2:
        return (kind, *value)
    if kind in ("ZeroIndices", "OneIndices") and isinstance(value, list):
        return (kind, *value)
    raise ValueError("Invalid removal variant")


def native_observations(path, digest, build):
    pinned(path, digest)
    p = target_protocol()
    humans, game, raw = opening_members(path, p, build)
    changes = timeline(p.decode_replay_tracker_events(raw))
    events, group_updates = stream(p, game)
    found, masks = Counter(), Counter()
    native_frames = native_bytes = 0
    for _, e, prior, frame in events:
        d = e["m_delta"]
        if encode_frame(e, prior, p) != frame:
            raise ValueError("Native physical selection frame differs")
        native_frames += 1
        native_bytes += len(frame)
        masks[mask_key(d["m_removeMask"])] += 1
        for g, tag in groups(d):
            state = at(changes.get((tag >> 22, tag & 0x3FFFFF), []), e["_gameloop"])
            if not state or state[0] >= e["_gameloop"] or not state[3]:
                continue
            _, unit, owner, _ = state
            if unit not in WANTED or owner != humans.get(e["_userid"]["m_userId"]):
                continue
            found[
                unit,
                g["m_unitLink"],
                g["m_subgroupPriority"],
                g["m_intraSubgroupPriority"],
                g["m_count"],
            ] += 1
    return dict(
        build=build,
        sha256=digest,
        frames=native_frames,
        bytes=native_bytes,
        control_group_updates=group_updates,
        observed=[[*k, v] for k, v in sorted(found.items())],
        masks=[[*k, v] for k, v in sorted(masks.items())],
    )


def remove_items(items, mask):
    """The selected 98348 path indexes the low bits of the ascending item array."""
    key = mask_key(mask)
    if key == ("None",):
        return list(items)
    if key == ("ZeroIndices",):
        return []
    if key[0] == "Mask" and len(key) == 3:
        _, width, bits = key
        if 1 <= width <= 3 and 0 <= bits < 1 << width:
            return [tag for index, tag in enumerate(items) if index >= width or not bits & 1 << index]
    raise ValueError("Removal mask outside the verified TEN shapes")


def catalog(controls, build):
    links = defaultdict(set)
    refs = defaultdict(set)
    for c in controls:
        if c["build"] != build:
            continue
        for unit, link, priority, intra, count, observed in c["observed"]:
            if observed < 1:
                raise ValueError("Empty physical witness")
            links[unit].add(link)
            refs[unit, priority, intra, count].add(c["sha256"])
    return links, refs


def plan(source, package, mechanics, curve, controls, build):
    """98348 predicts opening tags; the 98285 lane uses the unchanged historical tracker by design."""
    if build not in (98285, 98348):
        raise ValueError("Unsupported selection build")
    pinned(source, SOURCE)
    p, raw_tracker, end = read_tracker(source, 41810)
    humans, game, _ = opening_members(source, p, 41810)
    tracker = list(p.decode_replay_tracker_events(raw_tracker))
    physical = timeline(tracker)
    placed, heroes, map_sha = model(source, 41810, p, package, mechanics)
    initial = {(r["m_unitTagIndex"], r["m_unitTagRecycle"]): r for r in placed + heroes}
    hero_life = independent_histories(
        lobby_predictions(source, 41810), tracker, source_curve(curve), core_horizon(tracker, end)
    )
    first_activation = next(
        e["_gameloop"] for e in tracker if e.get("m_eventName") == b"DragonKnightActivated"
    )
    observed_heroes = {(r["m_unitTagIndex"], r["m_unitTagRecycle"]) for r in heroes}
    if set(hero_life) != observed_heroes:
        raise ValueError("Opening and historical timer models disagree")
    links, refs = catalog(controls, build)
    selections, control_updates = stream(p, game)
    if control_updates or len(selections) != 158:
        raise ValueError("Unexpected control-group writes or selection count")
    source_state, target_state = defaultdict(list), defaultdict(list)
    remap = {}
    ledger, events, patches = [], [], {}
    for index, (ordinal, e, prior, physical_frame) in enumerate(selections):
        tick, user = e["_gameloop"], e["_userid"]["m_userId"]
        if named_encode([{**e, "_gameloop": tick - prior}], p) != physical_frame:
            raise ValueError("Historical physical frame mismatch")
        d = e["m_delta"]
        if e["m_controlGroupId"] != 10 or d["m_subgroupIndex"] not in (0, 1):
            raise ValueError("Unexpected TEN group or index")
        dst = deepcopy(e)
        out = dst["m_delta"]
        additions = []
        bindings = []
        for source_group, tag in groups(d):
            pair = tag >> 18, tag & 0x3FFFF
            state = at(physical.get(pair, []), tick)
            if not state or state[0] >= tick or not state[3] or state[2] != humans.get(user):
                raise ValueError("Cannot identify a prior living selected unit for this player")
            unit = state[1]
            key = (
                unit,
                source_group["m_subgroupPriority"],
                source_group["m_intraSubgroupPriority"],
                source_group["m_count"],
            )
            available = sorted(refs.get(key, ()))
            whole_unit_links = links.get(unit, set())
            link = next(iter(whole_unit_links)) if len(whole_unit_links) == 1 and available else None
            dst_tag = None
            if build == 98285:
                dst_tag = (pair[0] << 22) | pair[1]
            elif pair in initial:
                predicted = initial[pair]
                start = physical[pair][0]
                if (
                    predicted["m_unitTypeName"].decode(),
                    predicted["m_controlPlayerId"],
                    predicted["_gameloop"],
                ) != (start[1], start[2], start[0]):
                    raise ValueError("Opening allocation differs from original birth")
                if unit != start[1]:
                    raise ValueError("Opening identity changed type")
                if pair in hero_life:
                    life = at(hero_life[pair][2], tick)
                    if not life or life[0] >= tick or not life[1]:
                        raise ValueError("Independent primary-hero life differs")
                elif (
                    unit != "VehicleDragon"
                    or state[0] != first_activation
                    or tick != first_activation + 1
                ):
                    raise ValueError("Uncorroborated selected map-unit transition")
                dst_tag = (predicted["m_unitTagIndex"] << 22) | predicted["m_unitTagRecycle"]
            if dst_tag is not None:
                remap[tag] = dst_tag
            additions.append(
                dict(
                    unit=unit,
                    source_link=source_group["m_unitLink"],
                    target_link=link,
                    tag_resolved=dst_tag is not None,
                    link_witnesses=available,
                )
            )
            bindings.append((dst_tag, link))
        if len(d["m_addSubgroups"]) != len(bindings):
            raise ValueError("TEN groups are no longer all singletons")
        for g, (_, link) in zip(out["m_addSubgroups"], bindings):
            if link is not None:
                g["m_unitLink"] = link
        group_ok = all(t is not None and l is not None for t, l in bindings)
        if all(t is not None for t, _ in bindings):
            out["m_addUnitTags"] = [t for t, _ in bindings]
        src_retained = remove_items(source_state[user], d["m_removeMask"])
        old_target = target_state[user]
        reset = mask_key(d["m_removeMask"]) == ("ZeroIndices",)
        retained = (
            []
            if reset
            else (None if old_target is None else remove_items(old_target, d["m_removeMask"]))
        )
        membership_ok = (
            retained is not None
            and all(t in remap for t in src_retained)
            and retained == [remap[t] for t in src_retained]
        )
        accepted = group_ok and membership_ok
        source_state[user] = sorted(set(src_retained + d["m_addUnitTags"]))
        target_state[user] = sorted(set(retained + out["m_addUnitTags"])) if accepted else None
        if accepted and [remap[t] for t in source_state[user]] != target_state[user]:
            raise ValueError("Selection sort order changed after migration")
        reasons = []
        if any(not a["tag_resolved"] for a in additions):
            reasons.append("target-allocation-unknown")
        if any(a["target_link"] is None for a in additions):
            reasons.append("matching-selection-link-unwitnessed")
        if not membership_ok:
            reasons.append("prior-selection-state-unknown")
        row = dict(
            selection_ordinal=index,
            game_event_ordinal=ordinal,
            loop=tick,
            prior_game_loop=prior,
            mask=list(mask_key(d["m_removeMask"])),
            additions=additions,
            admitted=accepted,
            reasons=reasons,
        )
        if accepted:
            standalone = encode_frame(dst, events[-1]["_gameloop"] if events else 0, target_protocol())
            enclosed = encode_frame(dst, prior, target_protocol())
            row.update(
                sparse_ordinal=len(events),
                sparse_frame_sha256=sha256(standalone).hexdigest(),
                enclosing_frame_sha256=sha256(enclosed).hexdigest(),
            )
            events.append(dst)
        if build == 98285 and any(l is not None for _, l in bindings):
            # Link 302 has independent single-unit evidence for every mixed TEN row.
            # The adjacent Monstrosity field stays unresolved on this partial copy.
            if not group_ok and [
                (a["unit"], a["source_link"], a["target_link"]) for a in additions
            ] != [("AbathurEvolvedMonstrosity", 36, None), ("AbathurSymbiote", 302, 438)]:
                raise ValueError("Unqualified mixed selection subgroup")
            patches[ordinal] = dst
        ledger.append(row)
    sparse = named_encode(events, target_protocol()) if events else b""
    decoded = list(target_protocol().decode_replay_game_events(sparse))
    if (
        len(decoded) != len(events)
        or any(
            {k: v for k, v in e.items() if k != "_bits"} != {k: v for k, v in f.items() if k != "_bits"}
            for e, f in zip(events, decoded)
        )
        or sum(e["_bits"] for e in decoded) != len(sparse) * 8
        or sum(1 for _ in iter_game_events(sparse)) != len(events)
    ):
        raise ValueError("Sparse stream decoder disagreement")
    return (
        dict(
            build=build,
            map_sha256=map_sha,
            source=SOURCE,
            selections=len(ledger),
            admitted=len(events),
            sparse_bytes=len(sparse),
            sparse_sha256=sha256(sparse).hexdigest(),
            rows=ledger,
        ),
        sparse,
        patches,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "map", "mechanics", "curve", "controls"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("--private-output", type=Path)
    args = cli.parse_args()
    pinned(args.controls, CONTROL_RECEIPT)
    summary, sparse, _ = plan(
        args.source, args.map, args.mechanics, args.curve, json.loads(args.controls.read_bytes()), 98348
    )
    if args.private_output:
        with args.private_output.open("xb") as target:
            target.write(sparse)
    print(json.dumps(summary, indent=2))
