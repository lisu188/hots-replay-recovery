"""Project a same-loop point update directly following an ordinary issue for the same player."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as named_encode
from first_sync_game import game
from implicit_point_issues import check_schema, eligible, validate_manifest
from contextlib import closing
from mpq_reader import MPQArchive
from smartcam_tags import R8
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE

UPDATE = 104
FAMILY = frozenset((25, 27, 103, 104, 105))
FIELDS = ("m_sequence", "m_target")


def match(previous, update, build):
    """Admission uses no target-update sequence value."""
    if (
        previous is None
        or update["_eventid"] != UPDATE
        or previous["_userid"] != update["_userid"]
        or previous["_gameloop"] != update["_gameloop"]
        or not eligible(previous)
        or previous["m_cmdFlags"] != {41810: 0x100108, 98348: 0x80108}[build]
        or previous["m_data"]["TargetPoint"] == update["m_target"]
    ):
        return None
    return previous["m_sequence"]


def native(event, delta, target, tid):
    value = _anonymous({k: event[k] for k in FIELDS}, target.typeinfos, tid)
    return GameEvent(delta, event["_userid"]["m_userId"], UPDATE, value)


def check_update(p):
    tid, name = p.game_event_types[UPDATE]
    if (
        name != "NNet.Game.SCmdUpdateTargetPointEvent"
        or tuple(k for k, _, _ in p.typeinfos[tid][1][0]) != FIELDS
    ):
        raise ValueError("Unexpected update payload")
    return tid


def scan(source, digest, build):
    p, raw = game(source, digest, build)
    check_schema(p, build)
    check_update(p)
    target = target_protocol()
    tid = check_update(target)
    pending = {}
    events = {}
    physical = bytearray()
    enclosing = []
    sparse = []
    source_check = []
    previous = offset = last_sparse = source_elapsed = 0
    counts = Counter()
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        kind = e["_eventid"]
        tick = e["_gameloop"]
        user = e["_userid"]["m_userId"]
        size, rem = divmod(e["_bits"], 8)
        if rem or not size or offset + size > len(raw) or tick < previous:
            raise ValueError("Invalid full game frame bounds")
        if kind in FAMILY:
            prior = pending.pop(user, None)
            if eligible(e):
                pending[user] = e
            elif kind == UPDATE and prior is not None and prior["_gameloop"] == tick:
                counts["all_immediate_same_loop_after_implicit_point_issue"] += 1
                seq = match(prior, e, build)
                if seq is not None:
                    # Only now examine the held-out optional update sequence.
                    actual = e["m_sequence"]
                    if actual is not None and actual != seq:
                        raise ValueError("Current or explicit source update contradicts issued sequence")
                    if build == 98348 and actual is None:
                        raise ValueError("Target update lacks an explicit sequence")
                    counts["absent" if actual is None else "matching_explicit"] += 1
                    physical.extend(raw[offset : offset + size])
                    converted = {**e, "m_sequence": seq}
                    events[ordinal] = converted
                    if build == 98348:
                        enclosing.append(native(converted, tick - previous, target, tid))
                    else:
                        source_elapsed += tick - previous
                        source_check.append({**e, "_gameloop": source_elapsed})
                    sparse.append(native(converted, tick - last_sparse, target, tid))
                    last_sparse = tick
        offset += size
        previous = tick
    if offset != len(raw):
        raise ValueError("Incomplete game stream traversal")
    encoded = encode_game_events(enclosing) if build == 98348 else named_encode(source_check, p)
    if encoded != physical:
        raise ValueError("Enclosing physical update frames differ")
    converted = encode_game_events(sparse)
    if converted != named_encode(list(events.values()), target) or any(
        frame.event != expect for frame, expect in zip(iter_game_events(converted), sparse, strict=True)
    ):
        raise ValueError("Sparse target update writer or reader mismatch")
    return (
        events,
        converted,
        dict(
            replay_sha256=digest,
            build=build,
            counts=dict(sorted(counts.items())),
            frames=len(events),
            enclosing_bytes=len(physical),
            enclosing_sha256=sha256(physical).hexdigest(),
            sparse_bytes=len(converted),
            sparse_sha256=sha256(converted).hexdigest(),
            ordinal_sha256=sha256(json.dumps(list(events), separators=(",", ":")).encode()).hexdigest(),
        ),
    )


def generate(source):
    """Return {source ordinal: target named update}, sparse bytes and receipt, only for TEN's absent values."""
    rows, data, report = scan(source, SOURCE, 41810)
    if report["counts"] != {"absent": 311, "all_immediate_same_loop_after_implicit_point_issue": 311}:
        raise ValueError("Unexpected TEN projection cohort")
    return rows, data, report


def control(case):
    path, digest = case
    return scan(path, digest, 98348)[2]


def compare_r8(path, generated):
    if sha256(path.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected original partial R8 archive")
    p = target_protocol()
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (98285,) * 3:
            raise ValueError("Unexpected R8 build")
        raw = arc.read_file("replay.game.events")
    counts = Counter()
    for i, e in enumerate(p.decode_replay_game_events(raw)):
        if i in generated:
            predicted = generated[i]
            fields = ("_eventid", "_gameloop", "_userid", "m_target")
            if any(e.get(k) != predicted[k] for k in fields):
                raise ValueError("R8 changes update order, time, user or coordinates")
            if e["m_sequence"] is None:
                counts["absent"] += 1
            elif e["m_sequence"] == predicted["m_sequence"]:
                counts["matching_explicit"] += 1
            else:
                counts["different_explicit"] += 1
    if counts.total() != len(generated):
        raise ValueError("R8 update ordinals missing")
    return dict(build=98285, sha256=R8, existing=dict(sorted(counts.items())))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("--control-manifest", type=Path)
    cli.add_argument("--retained-r8", type=Path)
    cli.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    cli.add_argument("--private-output", type=Path)
    cli.add_argument("--private-ordinals", type=Path)
    a = cli.parse_args()
    events, data, one = generate(a.source)
    report = dict(source=one, target_build=98348, target_simulation_verified=False)
    if a.retained_r8:
        report["retained_r8"] = compare_r8(a.retained_r8, events)
    if a.control_manifest:
        manifest = json.loads(a.control_manifest.read_bytes())
        pins = validate_manifest(manifest)
        with ProcessPoolExecutor(a.jobs) as pool:
            controls = list(pool.map(control, [(Path(manifest[h]), h) for h in pins]))
        total = sum(r["frames"] for r in controls)
        if total != 13081 or any(
            r["frames"] != r["counts"].get("matching_explicit", 0)
            or r["frames"] != r["counts"].get("all_immediate_same_loop_after_implicit_point_issue", 0)
            for r in controls
        ):
            raise ValueError("Unexpected observed same-loop comparison cohort")
        report.update(
            controls=controls,
            target_physical_frames=total,
            target_physical_bytes=sum(r["enclosing_bytes"] for r in controls),
        )
    if a.private_output:
        with a.private_output.open("xb") as out:
            out.write(data)
    if a.private_ordinals:
        with a.private_ordinals.open("xb") as out:
            out.write(json.dumps(list(events), separators=(",", ":")).encode())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
