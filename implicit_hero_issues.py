"""Project only primary-hero issues corroborated by another reporter on the same game loop."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from command_authored_xy import get_target
from command_snapshot_owners import OWNER_FIELDS, OwnerHistory
from encoders import encode_game_events as named_encode
from first_point_commands import FLAGS
from first_sync_game import game
from hero_camera_lifetimes import core_horizon, independent_histories, lobby_predictions, recorded_histories, timers
from hero_revive_wire import GATE_MAP, STOCK, source_curve
from implicit_point_issues import check_schema, native
from match_selections import CONTROL_RECEIPT, at, groups
from mpq_reader import MPQArchive
from native_game_events import encode_game_events, iter_game_events
from opening_birth_wire import FIELDS, model, target_protocol
from predict_camp_captures import SOURCE
from project_rank_targets import MAP
from repair_unit_tags import components, pack
from snapshot_wire import terrain

HEROES = frozenset("Hero" + n for n in
        ("Abathur","Anubarak","Barbarian","FaerieDragon","Greymane","Kaelthas","Nova","Tyrande"))
TRAIN = "8371d65c0c680ad8aaf9fa283f489f76c8dd6660595a566d438cbf62a003f73e"
CROSS = {
    "afcf49a656068f343173fc79afff2d2ebf15066f531cb192382cdba9d1ea3272": "889da151b127b6b5091a26c0395b7787a74cd3f4dea69521512cf027129a009e",
    "1230eee79fd3b50a3ee471c587bc77dd14aef67d57bf22cd8df52e877329323a": "fddf3267c510a29b4ad55ada48096860054969095cf025a54f91b15fc310714e",
    "a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4": "ab9867fa3ecc52c8330553a120af5853f6673b6e42a9e393ee82dd6629fb7e93",
}


def read_json(path, digest):
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if sha256(raw).hexdigest() != digest:
        raise ValueError("Unexpected catalog observations")
    return json.loads(raw)


def catalog(controls, broader, excluded):
    # Leave the entire scored recording out of the independent selection witnesses.
    # Broader historical observations may veto but never supply a positive assignment.
    ids, reverse = defaultdict(lambda: defaultdict(set)), defaultdict(set)
    for r in read_json(controls, CONTROL_RECEIPT):
        if r["build"] != 98348 or r["sha256"] == excluded:
            continue
        for unit, link, _, _, _, count in r["observed"]:
            if count < 1:
                raise ValueError("Invalid physical selection witness")
            reverse[link].add(unit)
            ids[unit][link].add(r["sha256"])
    report = read_json(broader, TRAIN)
    veto = set(map(int, report["excluded_reverse_aliases"]))
    extra = report["all_unambiguous_current_candidates"]
    out = {}
    for unit, candidates in ids.items():
        if unit not in HEROES or len(candidates) != 1:
            continue
        (link, files), = candidates.items()
        if len(files) >= 2 and reverse[link] == {unit} and link not in veto and extra.get(unit, link) == link:
            out[unit] = link
    return out


def geometry(replay, build, p, package, mechanics, tracker, table):
    _, heroes, digest = model(replay, build, p, package, mechanics)
    if digest != (GATE_MAP if build == 41810 else STOCK):
        raise ValueError("Unexpected historical or native map")
    cutoff = core_horizon(tracker, tracker[-1]["_gameloop"])
    predicted = independent_histories(lobby_predictions(replay,build),tracker,table,cutoff)
    physical = recorded_histories(tracker)
    births = {(e["m_unitTagIndex"], e["m_unitTagRecycle"]): e for e in tracker if e["_eventid"] == 1
              and e["_gameloop"] <= 82}
    result = {}
    for birth in heroes:
        key = birth["m_unitTagIndex"], birth["m_unitTagRecycle"]
        unit = birth["m_unitTypeName"].decode()
        real = births.get(key)
        if unit not in HEROES or not real or any(birth[k] != real[k] for k in ("_gameloop", *FIELDS)):
            continue
        if key in predicted and key in physical and predicted[key][:2] == physical[key][:2]:
            result[key] = (unit, (birth["m_controlPlayerId"], birth["m_upkeepPlayerId"]),
                           predicted[key][2], physical[key][2])
    return result, cutoff


def crossmap_geometry(replay, protocol, tracker, table):
    # A control on another map can check the snapshot projection. Its locally observed
    # slot numbers cannot establish a Dragon Shire allocation.
    cutoff = core_horizon(tracker, tracker[-1]["_gameloop"])
    observed = recorded_histories(tracker)
    with closing(MPQArchive(replay)) as arc:
        slots = protocol.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    starts, predictions = {}, []
    for key, (slot, unit, life) in observed.items():
        if slot not in range(1,11) or unit.decode() not in HEROES or unit != b"Hero"+slots[slot-1]["m_hero"]:
            continue
        (birth,) = [e for e in tracker if e["_eventid"] == 1 and e["_gameloop"] == life[0][0]
                    and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) == key]
        if (birth["m_controlPlayerId"], birth["m_upkeepPlayerId"]) != (slot,slot):
            continue
        predictions.append((life[0][0],*key,slot,slot,unit))
    independent = independent_histories(predictions,tracker,table,cutoff)
    for key, (slot, unit, life) in independent.items():
        starts[key] = (unit.decode(), (slot,slot), life, observed[key][2])
    return starts, cutoff


def scan(replay, digest, build, package, mechanics, table, controls, broader):
    p, raw = game(replay, digest, build)
    target = target_protocol()
    check_schema(p, build)
    tid = check_schema(target,98348)
    with closing(MPQArchive(replay)) as arc:
        map_sha = p.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"][-1][8:].hex()
        if map_sha != CROSS.get(digest, MAP[build]):
            raise ValueError("Replay map differs")
        tracker = list(p.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
    if digest in CROSS:
        if build != 98348 or sha256(package.read_bytes()).hexdigest() != map_sha:
            raise ValueError("Unexpected cross-map control or map package")
        starts, cutoff = crossmap_geometry(replay,p,tracker,table)
    else:
        starts, cutoff = geometry(replay, build, p, package, mechanics, tracker, table)
    target_links = catalog(controls, broader, digest)
    owners = OwnerHistory(tracker)
    plane = terrain(package)
    shift = 18 if build == 41810 else 22
    snapshots = defaultdict(lambda: defaultdict(set))
    selections, reverse = defaultdict(set), defaultdict(set)
    candidates = []
    offset = previous = 0
    for i, e in enumerate(p.decode_replay_game_events(raw)):
        tick, user = e["_gameloop"], e["_userid"]["m_userId"]
        n, partial = divmod(e["_bits"], 8)
        prior, start = previous, offset
        offset, previous = offset+n, tick
        if partial or n < 1 or offset > len(raw) or tick < prior:
            raise ValueError("Invalid event frame extent")
        if e["_eventid"] == 28:
            for group, tag in groups(e["m_delta"]):
                key = components(tag, shift)
                if key in starts:
                    unit = starts[key][0]
                    link = group["m_unitLink"]
                    selections[unit].add(link)
                    reverse[link].add(unit)
        u = get_target(e)
        if not u or tick > cutoff:
            continue
        key = components(u["m_tag"], shift)
        if key not in starts:
            continue
        point = tuple(u["m_snapshotPoint"][kk] for kk in "xyz")
        snapshots[key,tick][user].add(point)
        if (e["_eventid"] == 27 and e["m_abil"] is None and e["m_otherUnit"] is None
                and e["m_unitGroup"] is None and e["m_cmdFlags"] == FLAGS[build]):
            candidates.append((i, e, key, prior, raw[start:offset]))
    if offset != len(raw):
        raise ValueError("Incomplete original member")
    projected, physical, sparse = {}, bytearray(), []
    by_unit, admissions = Counter(), Counter()
    last = 0
    for i, e, key, prior, original in candidates:
        tick, user = e["_gameloop"], e["_userid"]["m_userId"]
        unit, pair, independent, recorded = starts[key]
        if unit not in target_links:
            continue
        life = at(independent, tick)
        if life is None or life != at(recorded, tick) or life[0] >= tick or not life[1]:
            continue
        u = e["m_data"]["TargetUnit"]
        owner, reason = owners.lookup(u["m_tag"],tick,shift)
        if owner != pair or reason not in ("alive", "revived"):
            continue
        admissions["live_ordinary_issue"] += 1
        # The current user's command and all other events from this reporter are held out.
        # Peers need agree with each other before consulting the intended issue's snapshot.
        peers = {point for other, obs in snapshots[key,tick].items() if other != user for point in obs}
        if len(peers) != 1:
            continue
        (x, y, peer_z), = peers
        if not (0 <= x < (plane.width-1)*4096 and 0 <= y < (plane.height-1)*4096):
            continue
        height, remainder = plane.sample(x, y)
        if remainder or height != peer_z:
            continue
        admissions["unanimous_other_reporters_on_exact_terrain"] += 1
        point = dict(x=x,y=y,z=height)
        if point != u["m_snapshotPoint"]:
            admissions["issue_disagrees_with_other_reporter_position"] += 1
            continue
        current_link = target_links[unit]
        if build == 41810:
            # Verify the source link against a separate event family in the historical recording.
            old_links = selections[unit]
            if len(old_links) != 1:
                continue
            old_link, = old_links
            if reverse[old_link] != {unit}:
                continue
        else:
            old_link = current_link
        snapshot = dict(m_targetUnitFlags=111, m_timer=0, m_tag=pack(*key,22), m_snapshotUnitLink=current_link,
                        **dict(zip(OWNER_FIELDS, pair)), m_snapshotPoint=point)
        if u != {**snapshot,"m_tag":pack(*key,shift),"m_snapshotUnitLink":old_link} or e.get("m_vector") is not None:
            admissions["other_fields_disagree"] += 1
            continue
        row = {**e,"m_cmdFlags":FLAGS[98348],"m_vector":None,"m_data":{"TargetUnit":snapshot}}
        if named_encode([{**e,"_gameloop":tick-prior}],p) != original:
            raise ValueError("Historical enclosing frame differs")
        if build == 98348 and encode_game_events([native(row, tick-prior, target, tid)]) != original:
            raise ValueError("Complete target enclosing frame differs")
        projected[i] = row
        physical.extend(original)
        sparse.append(native(row, tick-last, target, tid))
        last = tick
        by_unit[unit] += 1
    output = encode_game_events(sparse)
    if named_encode(list(projected.values()),target) != output or any(
        r.event != f for r, f in zip(iter_game_events(output),sparse,strict=True)
    ):
        raise ValueError("Sparse codecs disagree")
    receipt = dict(build=build,replay_sha256=digest,ordinary_primary_candidates=len(candidates),
                   measured=dict(sorted(admissions.items())),qualified=len(projected),by_unit=dict(sorted(by_unit.items())),
                   enclosing_bytes=len(physical),enclosing_sha256=sha256(physical).hexdigest(),
                   bytes=len(output),sha256=sha256(output).hexdigest(),
                   ordinal_sha256=sha256(json.dumps(list(projected),separators=(",",":")).encode()).hexdigest())
    return projected, output, receipt


def generate(source, gate_map, mechanics, curve, controls, broader):
    return scan(source,SOURCE,41810,gate_map,mechanics,source_curve(curve),controls,broader)


def control(args):
    return scan(*args)[2]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("source","gate_map","mechanics","curve","controls","broader"):
        p.add_argument(arg,type=Path)
    for arg in ("native-manifest","stock-map","heroes-lib","game-lib","private-output","cache-directory"):
        p.add_argument("--"+arg,type=Path)
    a = p.parse_args()
    _, raw, source_result = generate(a.source,a.gate_map,a.mechanics,a.curve,a.controls,a.broader)
    report = dict(source=source_result,target_hero_trajectory_verified=False,
                  target_effective_catalog_verified=False,command_execution_verified=False)
    if a.native_manifest:
        if not all([a.stock_map,a.heroes_lib,a.game_lib]):
            p.error("Native checks require the stock map and both Galaxy libraries")
        paths = json.loads(a.native_manifest.read_bytes())
        cases = []
        lib = timers(a.heroes_lib,a.game_lib)
        for h,pth in paths.items():
            with closing(MPQArchive(Path(pth))) as arc:
                deps = target_protocol().decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"]
            if deps[-1][8:].hex() == STOCK:
                cases.append((Path(pth),h,98348,a.stock_map,a.mechanics,lib,a.controls,a.broader))
        keys = {r["sha256"] for r in read_json(a.controls,CONTROL_RECEIPT) if r["build"] == 98348}
        if keys != set(paths) or len(cases) != 15:
            raise ValueError("Incomplete stock Dragon controls")
        if a.cache_directory:
            for h, map_sha in CROSS.items():
                map_path = a.cache_directory / map_sha[:2] / map_sha[2:4] / (map_sha+".s2ma")
                cases.append((Path(paths[h]),h,98348,map_path,a.mechanics,lib,a.controls,a.broader))
        with ProcessPoolExecutor(3) as pool:
            refs = list(pool.map(control,cases))
        report["controls"] = sorted(refs,key=lambda r:r["replay_sha256"])
        if len(refs) != len({r["replay_sha256"] for r in refs}):
            raise ValueError("Duplicate physical control")
        support = {
            name: dict(frames=sum(r["by_unit"].get(name,0) for r in refs),
                       recordings=sum(name in r["by_unit"] for r in refs))
            for name in source_result["by_unit"]
        }
        if a.cache_directory and not all(s["frames"] for s in support.values()):
            raise ValueError("Missing held-out type-specific physical control")
        report["qualified_source_type_witnesses"] = support
        report["enclosing_native_frames_equal"] = sum(r["qualified"] for r in refs)
        report["enclosing_native_bytes_equal"] = sum(r["enclosing_bytes"] for r in refs)
        report["native_position_counterexamples"] = sum(
            r["measured"].get("issue_disagrees_with_other_reporter_position",0) for r in refs
        )
    if a.private_output:
        with a.private_output.open("xb") as f:
            f.write(raw)
    print(json.dumps(report,indent=2))
