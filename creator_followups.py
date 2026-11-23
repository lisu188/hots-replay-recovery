"""Check whether TEN's 68 new command creators support further physical target updates."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

import first_sync_game
from command_authored_xy import get_target
from first_sync_game import game
from audit_native_game_fidelity import _anonymous
from native_game_events import GameEvent, encode_game_events
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from repair_unit_tags import components
from snapshot_wire import terrain

ASSEMBLY = "566e8866089d44c526dd4ae6e68f015c7dd280167a028aac06a5a708eb14c2f7"
LEDGER = "5e5057f2d2709b47f85c4d872cc2dd2243968255395457606206703417f95e77"
PARTIAL = "2ee895d18bf0395de81bef5138fe471bcb427ba7dcd7184e273dc1262c77c413"
GATE = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"
FAMILY = {25, 27, 103, 104, 105}


def pin(path, expected):
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError("Input digest differs for " + path.name)
    return data


def collect(path, digest, build):
    p, raw = game(path, digest, build)
    with closing(MPQArchive(path)) as a:
        tracker = list(p.decode_replay_tracker_events(a.read_file("replay.tracker.events")))
    units = {(r["m_unitTagIndex"],r["m_unitTagRecycle"]): r["m_unitTypeName"].decode()
             for r in tracker if r["_eventid"] == 1}
    primary = {(r["m_unitTagIndex"],r["m_unitTagRecycle"]) for r in tracker
               if r["_eventid"] == 1 and r["_gameloop"] <= 82 and r["m_unitTypeName"].startswith(b"Hero")}
    families, issued, references, snapshots = defaultdict(list), Counter(), defaultdict(list), defaultdict(dict)
    state, previous, offset = {}, 0, 0
    history, repeats = Counter(), Counter()
    native_bytes = 0
    for i,e in enumerate(p.decode_replay_game_events(raw)):
        kind, tick, user = e["_eventid"], e["_gameloop"], e["_userid"]["m_userId"]
        size, rem = divmod(e["_bits"],8)
        if rem or size < 1 or offset+size > len(raw):
            raise ValueError("Invalid game frame extent")
        if kind in FAMILY:
            families[user].append((i,e))
        key = user, e.get("m_sequence")
        if kind == 27:
            issued[key] += 1
            state[key] = e["m_data"].get("TargetUnit") or next(iter(e["m_data"]))
        elif kind in (103,104,105) and key[1] is not None:
            references[key].append(i)
            if kind == 104:
                state[key] = "TargetPoint"
            if kind == 105 and build == 98348:
                prior, nxt = state.get(key), e["m_target"]
                if isinstance(prior,dict):
                    if prior["m_tag"] == nxt["m_tag"]:
                        same = prior["m_snapshotPoint"] == nxt["m_snapshotPoint"]
                        history["same_unit_same_xyz" if same else "same_unit_changed_xyz"] += 1
                        repeats[f"flags_{nxt['m_targetUnitFlags']}"] += 1
                        if components(nxt["m_tag"],22) in units:
                            repeats["tracked_generation"] += 1
                        if nxt["m_tag"] in (0,0xffffffff):
                            repeats["sentinel"] += 1
                    else:
                        history["different_unit"] += 1
                else:
                    history[str(prior)] += 1
                tid=p.game_event_types[105][0]
                fields=_anonymous({k:e[k] for k,_,_ in p.typeinfos[tid][1][0]},p.typeinfos,tid)
                frame=GameEvent(tick-previous,user,105,fields)
                if encode_game_events([frame]) != raw[offset:offset+size]:
                    raise ValueError("Native writer disagrees on the physical unit update")
                native_bytes += size
                state[key] = nxt
        if build == 41810 and (tar := get_target(e)):
            xyz = tuple(tar["m_snapshotPoint"][k] for k in "xyz")
            snapshots[tar["m_tag"],tick].setdefault(user,set()).add(xyz)
        previous, offset = tick, offset+size
    if offset != len(raw):
        raise ValueError("Incomplete game member")
    return families, issued, references, snapshots, units, primary, history, repeats, native_bytes


def intervals(rows):
    current, updates = None, []
    for index, event in rows:
        if event["_eventid"] in (25,27):
            if current is not None:
                yield current, updates, event
            current = (index,event) if event["_eventid"] == 27 else None
            updates = []
        elif current is not None:
            updates.append((index,event))
    if current is not None:
        yield current, updates, None


def status(sequence, e):
    got = e["m_sequence"]
    return "absent" if got is None else "same" if got == sequence else "different"


def current_case(args):
    path,digest = args
    families,issued,refs,_,_,heroes,history,repeats,physical = collect(path,digest,98348)
    results = defaultdict(Counter)
    for user, entries in families.items():
        for (i,e),updates,after in intervals(entries):
            target = get_target(e)
            seq = e["m_sequence"]
            if (target is None or e["m_cmdFlags"] != 0x80108 or any(e.get(k) is not None
                    for k in ("m_abil","m_otherUnit","m_unitGroup","m_vector"))
                    or components(target["m_tag"],22) not in heroes):
                continue
            for j,(_,r) in enumerate(updates):
                k = r["_eventid"]
                if k == 103 and r["m_state"] != 0:
                    break
                results[f"before_first_manager_{k}"][status(seq,r)] += 1
                if (k == 103 and j == 0 and len(updates)==1 and after and after.get("m_sequence")==seq+1):
                    results["sole_state0_bracketed"][status(seq,r)] += 1
                if k == 103:
                    break
            if len(updates) < 2 or issued[user,seq] != 1 or any(n<i for n in refs[user,seq]):
                continue
            first, second = updates[0][1],updates[1][1]
            if (first["_eventid"] == 104 and second["_eventid"] == 103 and second["m_state"] == 0
                    and first["_gameloop"] == second["_gameloop"] == e["_gameloop"]+1):
                results["next_loop_point_then_state0"][status(seq,first)+"_"+status(seq,second)] += 1
    return dict(history=history,repeat_targets=repeats,physical_unit_update_bytes=physical,lookup_rules=results)


def source_case(source,gate,assembly,partial):
    pin(gate,GATE)
    plane = terrain(gate)
    assemblies = {ASSEMBLY: LEDGER,
                  'd5722b8a4e8e794d6321abe49a7d4cdf825b793fc259e3b9c94fbf2d9c814cfd':
                  '8493263af8a2292db62fdec6e8f956534c60727c3f0e0caceea3a302c8355671'}
    stream = (assembly/'game-inputs.private.bin').read_bytes()
    stream_sha = sha256(stream).hexdigest()
    if stream_sha not in assemblies:
        raise ValueError('Unknown sparse assembly')
    ledger = json.loads(pin(assembly/"ordinals.private.json",assemblies[stream_sha]))
    proto = target_protocol()
    projected = {record[0]:(record[-1],e) for record,e in zip(ledger,
        proto.decode_replay_game_events(stream), strict=True)}
    creators = {i:("hero" if "moving_hero_target_requires_reproduced_trajectory" in labels else "cast")
                for i,(labels,_) in projected.items() if "moving_hero_target_requires_reproduced_trajectory" in labels
                or "tracker_corroborated_cast_conditional_flags" in labels}
    if Counter(creators.values()) != {"cast":51,"hero":17}:
        raise ValueError("Unexpected creator cohort")
    families,issued,refs,peers,units,_,_,_,_ = collect(source,SOURCE,41810)
    results, geometry, considered = Counter(), Counter(), {}
    for user,entries in families.items():
        for (i,e),updates,after in intervals(entries):
            if i not in creators:
                continue
            seq = e["m_sequence"]
            if projected[i][1]["m_sequence"] != seq:
                raise ValueError("Projected creator key mismatch")
            if creators[i] == "cast":
                for n,r in updates:
                    results[f"cast_following_{r['_eventid']}_{status(seq,r)}"] += 1
                continue
            tar = get_target(e)
            for j,(n,r) in enumerate(updates):
                if r["_eventid"] == 103 and r["m_state"] != 0:
                    break
                results[f"hero_before_first_manager_{r['_eventid']}_{status(seq,r)}"] += 1
                considered[n] = r
                if r["_eventid"] == 103:
                    break
                if r["_eventid"] != 105:
                    continue
                nxt = r["m_target"]
                if nxt["m_tag"] != tar["m_tag"]:
                    unit=units.get(components(nxt["m_tag"],18))
                    geometry["target_changed_to_"+str(unit)] += 1
                    continue
                if issued[user,seq] != 1 or any(o<i for o in refs[user,seq]):
                    geometry["reused_or_previously_referenced_creator"] += 1
                    continue
                xyz = tuple(nxt["m_snapshotPoint"][k] for k in "xyz")
                other = {v for who,points in peers[nxt["m_tag"],r["_gameloop"]].items()
                         if who!=user for v in points}
                if other != {xyz} or plane.sample(xyz[0],xyz[1]) != (xyz[2],0):
                    geometry["independent_position_missing_or_disagrees"] += 1
                    continue
                geometry["same_tag_same_payload" if tar==nxt else "same_tag_changed_payload"] += 1
    pin(partial,PARTIAL)
    with closing(MPQArchive(partial)) as ar:
        head = proto.decode_replay_header(ar.header["user_data_header"]["content"])
        if head["m_version"]["m_build"] != 98285:
            raise ValueError("Wrong protected R8")
        member = ar.read_file("replay.game.events")
    partial_matches=0
    for i,r in enumerate(proto.decode_replay_game_events(member)):
        if i in considered:
            old=considered[i]
            if (r["_eventid"],r["_gameloop"],r["_userid"],r["m_sequence"]) != (
                    old["_eventid"],old["_gameloop"],old["_userid"],old["m_sequence"]):
                raise ValueError("R8 near-creator position or sequence differs")
            partial_matches+=1
    if partial_matches!=len(considered):
        raise ValueError("Unobserved R8 candidate")
    return dict(creators=dict(Counter(creators.values())),intervals=results,unit_target_geometry=geometry,
                compared_earliest_followups=partial_matches, already_in_sparse_assembly=len(considered.keys() & projected.keys()),
                protected_r8_sha256=PARTIAL, sparse_assembly_sha256=stream_sha)


def aggregate(cases):
    history,repeats,bytes_seen=Counter(),Counter(),0
    rules=defaultdict(Counter)
    for result in cases:
        history.update(result["history"])
        repeats.update(result["repeat_targets"])
        bytes_seen+=result["physical_unit_update_bytes"]
        for rule, counts in result["lookup_rules"].items():
            rules[rule].update(counts)
    return dict(cases=len(cases),physical_unit_updates=history.total(),physical_bytes=bytes_seen,
                per_sequence_prior_target=history,repeat_targets=repeats,lookup_rules=rules)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","gate","assembly","partial","control_manifest"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--jobs",type=int,default=3)
    a=cli.parse_args()
    paths=json.loads(a.control_manifest.read_bytes())
    pins=sorted(r["replay_sha256"] for r in json.loads((Path(first_sync_game.__file__).parent/
        "observations/first-sync-game.json").read_bytes())["references"])
    if len(set(pins))!=24 or len(pins)!=24 or not set(pins).issubset(paths):
        raise ValueError("Expected all 24 physical target references")
    with ProcessPoolExecutor(a.jobs) as pool:
        results=list(pool.map(current_case,[(Path(paths[k]["path"] if isinstance(paths[k],dict) else paths[k]),k)
                                           for k in pins]))
    training, heldout = aggregate(results[:8]),aggregate(results[8:])
    if training["physical_unit_updates"]+heldout["physical_unit_updates"]!=4194:
        raise ValueError("Unexpected physical unit-update count")
    print(json.dumps(dict(source=source_case(a.source,a.gate,a.assembly,a.partial),first_eight=training,
                          remaining_sixteen=heldout,new_target_frames=0),indent=2))
