"""Emit individually qualified TEN selection frames before the first recorded sync."""

import argparse
from collections import defaultdict
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from camp_owner_wire import read_tracker
from encoders import encode_game_events as named_encode
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import model, target_protocol
from predict_camp_captures import SOURCE


PROFILE_PIN = "8ad237b10067acf552384df4f5e2b6112d56d7113024a1575ede4dfdc186524e"
WANTED = {(52,807), (59,64), (60,739), (60,827)}
SELECTION = "NNet.Game.SSelectionDeltaEvent"


def opening_members(path, protocol, build):
    with closing(MPQArchive(path)) as arc:
        header = protocol.decode_replay_header(arc.header["user_data_header"]["content"])
        version = header["m_version"]
        if (version["m_build"],version["m_baseBuild"],header["m_dataBuildNum"]) != (build,)*3:
            raise ValueError("Unexpected replay build")
        slots = protocol.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
        humans = [(s["m_userId"],i) for i,s in enumerate(slots,1)
                  if s.get("m_userId") is not None and s["m_control"] == 2
                  and not s["m_observe"] and s.get("m_hero")]
        if len(humans) != len(dict(humans)):
            raise ValueError("Ambiguous player slots")
        return dict(humans), arc.read_file("replay.game.events"), arc.read_file("replay.tracker.events")


def selections(protocol, raw, limit):
    offset = previous = 0
    for event in protocol.decode_replay_game_events(raw):
        loop = event["_gameloop"]
        if loop > limit:
            return
        size, rest = divmod(event["_bits"],8)
        if rest or size < 1 or offset+size > len(raw) or loop < previous:
            raise ValueError("Invalid game event boundary")
        if event["_event"] == SELECTION and event["_eventid"] == 28:
            yield event, previous, raw[offset:offset+size]
        offset += size
        previous = loop


def single(event):
    delta = event["m_delta"]
    groups = delta["m_addSubgroups"]
    tags = delta["m_addUnitTags"]
    if (event["m_controlGroupId"] == 10 and delta["m_subgroupIndex"] == 0
            and delta["m_removeMask"] == {"None":None} and len(groups) == len(tags) == 1
            and groups[0]["m_count"] == 1):
        return tags[0], groups[0]
    return None


def encode_frame(event, previous, target):
    payload = {k:v for k,v in event.items() if not k.startswith("_")}
    tid, kind = target.game_event_types[28]
    if kind != SELECTION:
        raise ValueError("Wrong event declaration")
    dt = event["_gameloop"] - previous
    frame = GameEvent(dt, event["_userid"]["m_userId"], 28,
                      _anonymous(payload, target.typeinfos, tid))
    encoded = encode_game_events([frame])
    (decoded,) = iter_game_events(encoded)
    alternate = named_encode([{**event, "_gameloop":dt}],target)
    if decoded.event != frame or encoded != alternate:
        raise ValueError("Selection frame codec disagreement")
    return encoded


def target_witnesses(path, digest, names):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unrecognized reference")
    target = target_protocol()
    humans, game, tracker = opening_members(path,target,98348)
    primary = {}
    invalidated = {}
    for row in target.decode_replay_tracker_events(tracker):
        loop, kind = row["_gameloop"], row["_eventid"]
        if loop > 256:
            break
        if kind in (1,2,3):
            key = (row["m_unitTagIndex"] << 22) | row["m_unitTagRecycle"]
            if kind == 1 and row["m_unitTypeName"] in names:
                if key in primary:
                    raise ValueError("Duplicate unit birth")
                primary[key] = (loop,row["m_controlPlayerId"],row["m_unitTypeName"])
            elif kind in (2,3) and key in primary:
                invalidated.setdefault(key,loop)
    sightings = set()
    for event, prior, physical in selections(target,game,256):
        add = single(event)
        if add is None or add[0] not in primary:
            continue
        tag, group = add
        born, owner, unit = primary[tag]
        tick = event["_gameloop"]
        if not born < tick < invalidated.get(tag,257) or humans.get(event["_userid"]["m_userId"]) != owner:
            continue
        if encode_frame(event,prior,target) != physical:
            raise ValueError("Reference frame fails physical comparison")
        sightings.add((unit.decode("ascii"), group["m_unitLink"], group["m_subgroupPriority"],
                       group["m_intraSubgroupPriority"], group["m_count"]))
    return sightings


def admitting_references(unit, expected, priorities, evidence):
    """Conflicting observed catalog links disqualify a type across all priorities."""
    variants = {link for (name,link,*_),hits in evidence.items() if name == unit and hits}
    if variants != {expected}:
        return set()
    return evidence.get((unit,expected,*priorities),set())


def generate(source, map_path, mechanics, profile, references):
    if sha256(source.read_bytes()).hexdigest() != SOURCE or sha256(profile.read_bytes()).hexdigest() != PROFILE_PIN:
        raise ValueError("Unexpected source or catalog profile")
    old, tracker, _ = read_tracker(source,41810)
    target = target_protocol()
    _, heroes, _ = model(source,41810,old,map_path,mechanics)
    humans, game, _ = opening_members(source,old,41810)
    observed = {}
    for e in old.decode_replay_tracker_events(tracker):
        if e["_gameloop"] > 64:
            break
        if e["_eventid"] in (1,2,3):
            key = e["m_unitTagIndex"],e["m_unitTagRecycle"]
            if e["_eventid"] == 1:
                observed[key] = e
            else:
                observed.pop(key,None)
    bindings = {(e["m_unitTagIndex"],e["m_unitTagRecycle"]):e for e in heroes}
    profile_rows = json.loads(profile.read_bytes())["startup_fields"]
    catalog = {(r["source_catalog_link"],r["tracker_unit_type"]):r["current_98348_observed_candidate"]
               for r in profile_rows}
    names = {unit.encode("ascii") for _,unit in catalog}
    evidence = defaultdict(set)
    for digest, path in references.items():
        for hit in target_witnesses(path,digest,names):
            evidence[hit].add(digest)
    rows, frames = [], []
    admitted_previous = 0
    for event, prior, physical in selections(old,game,63):
        tick = event["_gameloop"]
        tag, group = single(event) or (None,None)
        if group is None or (tick,group["m_unitLink"]) not in WANTED:
            raise ValueError("Unexpected first-sync selection shape")
        source_check = named_encode([{**event,"_gameloop":tick-prior}],old)
        if source_check != physical:
            raise ValueError("Source frame does not reencode exactly")
        pair = tag >> 18, tag & ((1<<18)-1)
        pred, actual = bindings[pair], observed[pair]
        if (pred["_gameloop"] >= tick or pred["m_controlPlayerId"] != humans[event["_userid"]["m_userId"]]
                or any(pred[k] != actual[k] for k in ("_gameloop","m_unitTypeName","m_controlPlayerId","m_upkeepPlayerId"))):
            raise ValueError("Source selected hero disagrees with the opening model")
        unit = pred["m_unitTypeName"].decode("ascii")
        source_link = group["m_unitLink"]
        expected = catalog.get((source_link,unit))
        priorities = (group["m_subgroupPriority"],group["m_intraSubgroupPriority"],group["m_count"])
        agree = admitting_references(unit,expected,priorities,evidence)
        row = dict(loop=tick, unit=unit, source_link=source_link, target_link=expected,
                   matching_reference_count=len(agree), matching_references=sorted(agree),
                   priority=list(priorities), admitted=bool(agree),
                   source_physical_previous=prior)
        if row["admitted"]:
            converted = deepcopy(event)
            d = converted["m_delta"]
            d["m_addSubgroups"][0]["m_unitLink"] = expected
            d["m_addUnitTags"] = [(pred["m_unitTagIndex"] << 22) | pred["m_unitTagRecycle"]]
            framed = encode_frame(converted,prior,target)
            sparse = encode_frame(converted,admitted_previous,target)
            frames.append(sparse)
            admitted_previous = tick
            row.update(frame_bytes=len(framed), physical_delta_sha256=sha256(framed).hexdigest(),
                       sparse_frame_sha256=sha256(sparse).hexdigest(), target_tag=d["m_addUnitTags"][0])
        rows.append(row)
    if len(rows)!=4 or {(r["loop"],r["source_link"]) for r in rows} != WANTED:
        raise ValueError("Incomplete source selection interval")
    data = b"".join(frames)
    report = dict(build=98348, source_sha256=SOURCE, catalog_profile_sha256=PROFILE_PIN,
                  references_checked=len(references), references=sorted(references), evidence_loop_limit=256,
                  selections=rows, frames=len(frames), sparse_bytes=len(data), sparse_sha256=sha256(data).hexdigest())
    return report, data


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("source","map","mechanics","profile","references","out"):
        p.add_argument(key,type=Path)
    args=p.parse_args()
    refs={k:Path(v) for k,v in json.loads(args.references.read_bytes()).items()}
    report,data=generate(args.source,args.map,args.mechanics,args.profile,refs)
    with args.out.open("xb") as stream:
        stream.write(data)
    print(json.dumps(report,indent=2))
