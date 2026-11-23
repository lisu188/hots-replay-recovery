"""Fill corroborated optional sequence fields in a new complete build-98285 R8 archive."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from command_interval_sequences import RULES, SELECTED, candidates, generate as interval_source, intervals
from encoders import encode_game_events
from first_point_commands import COMMANDS, first_issue
from first_sync_game import game as original_game
from immediate_point_updates import generate as immediate_source, match
from initial_point_sessions import analyze as sessions_source
from integrate_r8_camera_pings import GAME, SYNC, inventory
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from portable_sync_98348 import decode_sync, encode_sync
from predict_camp_captures import SOURCE
from runtime_catalog_probe import Storm

PARENT = "5ed50ccfcd947b92488cba095973dcd9d4de76a976a457417203608d379b3f01"
PARENT_GAME = "5bdad0febafc9cd6731a7f9956664eafcb8ca3ef24187481394e01beadee4613"
DONORS = {"05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75",
          "5a7b05f4a75bc229dbbd74e6cc09e3b411129fc731874cfaa9217432fb85e7dc"}


def digest(data):
    return sha256(data).hexdigest()


def identity(row):
    return row["_gameloop"], row["_userid"]["m_userId"], row["_eventid"], row["_event"]


def add(predictions, ordinal, sequence, rule):
    if type(sequence) is not int or not 1 <= sequence <= 2**32:
        raise ValueError("Invalid issue sequence")
    prior = predictions.setdefault(ordinal, (sequence, set()))
    if prior[0] != sequence:
        raise ValueError("Conflicting independent rule values")
    prior[1].add(rule)


def source_predictions(source):
    predictions = {}
    for rule, rows in (("interval",interval_source(source)[0]), ("immediate",immediate_source(source)[0]),
                       ("opening",dict(sessions_source(source,SOURCE,41810)[0]))):
        for i, e in rows.items():
            if e["_eventid"] in (103,104):
                add(predictions,i,e["m_sequence"],rule)
    if len(predictions) != 708:
        raise ValueError("Unexpected union of published original-ordinal projections")
    return predictions


def predictions_98285(p, raw):
    # The two modern builds use the same issue flag and event layout. The concrete
    # 98285 controls score these rules independently before any archive can be emitted.
    predicted = {}
    for issue, rows, next_issue in intervals(p, raw, 98348, {k: Counter() for k in RULES}):
        for (ordinal, _, _, _), sequence, rules in candidates(issue, rows, next_issue):
            if set(SELECTED).intersection(rules):
                add(predicted,ordinal,sequence,"interval")
    previous, session = {}, {}
    for i, e in enumerate(p.decode_replay_game_events(raw)):
        tick, user, kind, _ = identity(e)
        if kind in (101,102):
            session[user] = ("ended",0)
        if kind not in COMMANDS:
            continue
        if kind == 104:
            seq = match(previous.get(user), e, 98348)
            if seq is not None:
                add(predicted,i,seq,"immediate")
        previous[user] = e
        if tick >= 4000:
            continue
        phase, seq = session.get(user,("ready",0))
        if phase == "ended":
            continue
        if phase == "ready" and first_issue(e,98348) and e["m_sequence"] == seq+1:
            session[user] = ("open",seq+1)
        elif phase == "open" and (kind == 104 or kind == 103 and e["m_state"] == 0):
            add(predicted,i,seq,"opening")
            if kind == 103:
                session[user] = ("ready",seq)
        else:
            session[user] = ("ended",seq)
    return predicted


def modern_header(p, header):
    h = p.decode_replay_header(header)
    if (h["m_version"]["m_build"],h["m_version"]["m_baseBuild"],h["m_dataBuildNum"]) != (98285,)*3:
        raise ValueError("Unexpected physical build")


def iter_frames(protocol, raw):
    previous = offset = 0
    for e in protocol.decode_replay_game_events(raw):
        n, partial = divmod(e["_bits"],8)
        tick = e["_gameloop"]
        if partial or n <= 0 or tick < previous or offset+n > len(raw):
            raise ValueError("Invalid original frame")
        yield e, previous, raw[offset:offset+n]
        previous, offset = tick, offset+n
    if offset != len(raw):
        raise ValueError("Truncated event member")


def encode_physical(p, e, prior):
    return encode_game_events([{**e,"_gameloop":e["_gameloop"]-prior}],p)


def verify_control(path):
    h = digest(path.read_bytes())
    if h not in DONORS:
        raise ValueError("Unexpected physical 98285 control")
    p = target_protocol()
    with closing(MPQArchive(path)) as arc:
        modern_header(p,arc.header["user_data_header"]["content"])
        raw = read_member(arc,GAME)
    proposed = predictions_98285(p,raw)
    rules, ids = Counter(), Counter()
    size = 0
    for i, (e, prior, physical) in enumerate(iter_frames(p,raw)):
        if i not in proposed:
            continue
        seq, labels = proposed[i]
        if encode_physical(p,{**e,"m_sequence":seq},prior) != physical:
            raise ValueError("98285 control contradicts selected rule")
        rules.update(labels)
        ids[e["_eventid"]] += 1
        size += len(physical)
    if sum(ids.values()) != len(proposed):
        raise ValueError("Control scan incomplete")
    return dict(replay_sha256=h,frames=len(proposed),enclosing_bytes=size,rules=dict(rules),events=dict(ids))


def patch(source, old, original_raw, target, parent_raw):
    source_rows = source_predictions(source)
    draft_rows = predictions_98285(target,parent_raw)
    edited = bytearray()
    proof = []
    counts, by_kind = Counter(), Counter()
    prior_issues = Counter()
    total = 0
    for i, ((a, prior_a, _), (b, prior_b, physical)) in enumerate(zip(
        iter_frames(old,original_raw),iter_frames(target,parent_raw),strict=True
    )):
        if identity(a) != identity(b) or prior_a != prior_b:
            raise ValueError("Physical ordinal mapping differs between original and R8")
        total += 1
        tick, user, kind, _ = identity(b)
        if kind == 27:
            prior_issues[user,b["m_sequence"]] += 1
        if i not in source_rows:
            edited.extend(physical)
            continue
        seq, source_rules = source_rows[i]
        if i not in draft_rows or draft_rows[i][0] != seq or not source_rules <= draft_rows[i][1]:
            raise ValueError("R8's independent command history does not corroborate the original projection")
        if any(a.get(k) != b.get(k) for k in ("m_target","m_state","m_sequence")):
            raise ValueError("R8 differs from the original observation on the affected record")
        if prior_issues[user,seq] != 1:
            counts["unresolved_issuing_command"] += 1
            edited.extend(physical)
            continue
        if b["m_sequence"] is not None:
            if b["m_sequence"] != seq:
                raise ValueError("Would overwrite an inconsistent explicit value")
            counts["already_explicit"] += 1
            edited.extend(physical)
            continue
        after = encode_physical(target,{**b,"m_sequence":seq},prior_b)
        if len(after) != len(physical)+4 or encode_physical(target,b,prior_b) != physical:
            raise ValueError("Unrecognized optional-field encoding")
        edited.extend(after)
        proof.append([i,tick,user,kind,seq])
        counts["populated"] += 1
        by_kind[kind] += 1
    if total != 104257 or counts.total() != len(source_rows):
        raise ValueError("Incomplete full-length projected replay")
    data = bytes(edited)
    changed = {row[0]:row[-1] for row in proof}
    for i, ((a,prior_a,raw_a),(b,prior_b,raw_b)) in enumerate(zip(
        iter_frames(target,parent_raw),iter_frames(target,data),strict=True
    )):
        if i not in changed:
            if raw_a != raw_b:
                raise ValueError("Unrelated physical event bytes changed")
            continue
        if (prior_a != prior_b or a["m_sequence"] is not None or b["m_sequence"] != changed[i]
                or a["_bits"]+32 != b["_bits"]
                or {**a,"_bits":b["_bits"],"m_sequence":changed[i]} != b):
            raise ValueError("Decoded difference outside the optional sequence")
    return data, dict(full_game_events=total,original_ordinal_predictions=len(source_rows),
                      disposition=dict(counts),changed_events=dict(by_kind),
                      resulting_game_bytes=len(data),game_bytes_added=len(data)-len(parent_raw),
                      game_sha256=digest(data),
                      edits_ledger_sha256=digest(json.dumps(proof,separators=(",",":")).encode()))


def integrate(source, parent, controls, output, stormlib):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if digest(parent.read_bytes()) != PARENT or digest(source.read_bytes()) != SOURCE:
        raise ValueError("Unexpected protected parent or original")
    evidence = [verify_control(p) for p in controls]
    if {r["replay_sha256"] for r in evidence} != DONORS or len(evidence) != 2:
        raise ValueError("Both distinct physical 98285 controls required")
    if not all(any(r["rules"].get(rule,0) for r in evidence) for rule in ("opening","immediate","interval")):
        raise ValueError("Missing native support for an applied rule family")
    old, raw = original_game(source,SOURCE,41810)
    p,storm = target_protocol(),Storm(stormlib)
    header,before,v4 = inventory(parent,storm)
    modern_header(p,header)
    if digest(before[GAME]) != PARENT_GAME:
        raise ValueError("Protected game member differs")
    with closing(MPQArchive(source)) as arc:
        sync = read_member(arc,SYNC)
        if before["replay.tracker.events"] != read_member(arc,"replay.tracker.events"):
            raise ValueError("Original tracker differs")
    records = decode_sync(sync)
    if encode_sync(records) != sync or before[SYNC] != sync or len(records) != 308:
        raise ValueError("Source sync data mismatch")
    new,counts = patch(source, old, raw, p, before[GAME])
    with TemporaryDirectory(dir=output.parent) as temp:
        dest = Path(temp) / "candidate.StormReplay"
        dest.write_bytes(parent.read_bytes())
        storm.replace(dest,{GAME:new})
        h,after,updated = inventory(dest,storm)
        different = sorted(k for k in before if before[k] != after[k])
        if (header != h or before.keys() != after.keys() or different != ["(attributes)",GAME]
                or after[GAME] != new or v4["raw_chunk_size"] != updated["raw_chunk_size"]
                or sync != after[SYNC] or digest(parent.read_bytes()) != PARENT or digest(source.read_bytes()) != SOURCE):
            raise ValueError("Full archive verification failure")
        image_hash = digest(dest.read_bytes())
        os.link(dest,output)
    return dict(parent_sha256=PARENT,parent_game_sha256=PARENT_GAME,source_sha256=SOURCE,
                output_sha256=image_hash,output_bytes=output.stat().st_size,retained_build=98285,
                sync_records=len(records),sync_sha256=digest(sync),changed_members=different,
                unchanged_members=len(before)-len(different),independent_mpq_readers_agree=True,
                source_and_parent_unchanged=True,target_simulation_verified=False,
                physical_controls=sorted(evidence,key=lambda r:r["replay_sha256"]),**counts)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source","parent","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--control",action="append",required=True,type=Path)
    cli.add_argument("--stormlib",required=True)
    a=cli.parse_args()
    print(json.dumps(integrate(a.source,a.parent,a.control,a.output,a.stormlib),indent=2))
