"""Project TEN's ordinary point-targeted SCmdEvent issues on the GateOrder Dragon Shire map."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as named_encode
import first_sync_game
from first_sync_game import game
from hero_revive_wire import GATE_MAP
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from repair_command_flags import delete_zero_bit
from smartcam_tags import R8

ID = 27
NAME = "NNet.Game.SCmdEvent"
LEGACY_FLAGS = {0x100108: 0x80108, 0x110108: 0x88108, 0x10A: 0x10A}
SOURCE_COUNTS = {0x100108: 1175, 0x110108: 66, 0x10A: 7}
SOURCE_FIELDS = ("m_cmdFlags", "m_abil", "m_data", "m_sequence", "m_otherUnit", "m_unitGroup")
TARGET_FIELDS = SOURCE_FIELDS[:3] + ("m_vector",) + SOURCE_FIELDS[3:]
CONTROL_SET = "ecf4ad00b6c16fb075971d6ab03a15cbe6040d03f8e7d0eefd110e0334b55545"


def check_schema(p, build):
    tid, name = p.game_event_types[ID]
    root, args = p.typeinfos[tid]
    fields = {k: t for k, t, _ in args[0]}
    if (
        name != NAME
        or root != "_struct"
        or tuple(fields) != (SOURCE_FIELDS if build == 41810 else TARGET_FIELDS)
    ):
        raise ValueError("Unexpected issue root")
    for k in ("m_abil", "m_otherUnit", "m_unitGroup") + (("m_vector",) if build == 98348 else ()):
        if p.typeinfos[fields[k]][0] != "_optional":
            raise ValueError("Issue optional shape changed")
    if p.typeinfos[fields["m_cmdFlags"]] != ("_int", [(0, 25 if build == 41810 else 26)]) or p.typeinfos[
        fields["m_sequence"]
    ] != ("_int", [(1, 32)]):
        raise ValueError("Flag or mandatory sequence encoding changed")
    kind, choices = p.typeinfos[fields["m_data"]]
    pos, point = choices[1][1]
    if (
        kind != "_choice"
        or pos != "TargetPoint"
        or [(key, p.typeinfos[t]) for key, t, _ in p.typeinfos[point][1][0]]
        != [("x", ("_int", [(0, 20)])), ("y", ("_int", [(0, 20)])), ("z", ("_int", [(-(1 << 31), 32)]))]
    ):
        raise ValueError("Unexpected TargetPoint coordinate encoding")
    return tid


def eligible(e):
    return (
        e["_eventid"] == ID
        and e["m_abil"] is None
        and set(e["m_data"]) == {"TargetPoint"}
        and e.get("m_vector") is None
        and e["m_otherUnit"] is None
        and e["m_unitGroup"] is None
    )


def project(event):
    if not eligible(event) or event["m_cmdFlags"] not in LEGACY_FLAGS:
        raise ValueError("Unsupported point issue")
    return {**event, "m_cmdFlags": LEGACY_FLAGS[event["m_cmdFlags"]], "m_vector": None}


def native(e, delta, p, tid):
    payload = {k: e[k] for k in TARGET_FIELDS}
    return GameEvent(delta, e["_userid"]["m_userId"], ID, _anonymous(payload, p.typeinfos, tid))


def scan(path, digest, build):
    source, game_bytes = game(path, digest, build)
    check_schema(source, build)
    target = target_protocol()
    tid = check_schema(target, 98348)
    flags, shapes, selected_flags = Counter(), Counter(), Counter()
    vectors = Counter()
    physical = bytearray()
    native_physical = []
    legacy_physical = []
    selected = {}
    previous = offset = 0
    issues_by_user = Counter()
    sequence_echo = defaultdict(set)
    for ordinal, event in enumerate(source.decode_replay_game_events(game_bytes)):
        tick = event["_gameloop"]
        user = event["_userid"]["m_userId"]
        size, rem = divmod(event["_bits"], 8)
        if rem or not size or offset + size > len(game_bytes) or tick < previous:
            raise ValueError("Enclosing frame extent")
        kind = event["_eventid"]
        if kind in (103, 104, 105) and event["m_sequence"] is not None:
            sequence_echo[user].add(event["m_sequence"])
        if kind == ID:
            if event["_event"] != NAME:
                raise ValueError("Command ID/name discrepancy")
            flag = event["m_cmdFlags"]
            flags[flag] += 1
            (choice,) = event["m_data"]
            if build == 41810:
                shape = "/".join(
                    [
                        hex(flag),
                        "implicit" if event["m_abil"] is None else "explicit",
                        choice,
                        "other" if event["m_otherUnit"] is not None else "-",
                        "group" if event["m_unitGroup"] is not None else "-",
                    ]
                )
                shapes[shape] += 1
            issues_by_user[user] += 1
            # The historical schema has no vector member. Measure the modern presence
            # independently, without conditioning candidate selection on that field.
            if (build == 98348 and event["m_abil"] is None and choice == "TargetPoint"
                    and event["m_otherUnit"] is None and event["m_unitGroup"] is None):
                vectors["present" if event["m_vector"] is not None else "absent"] += 1
            if eligible(event):
                physical.extend(game_bytes[offset : offset + size])
                selected_flags[flag] += 1
                if build == 98348:
                    native_physical.append(native(event, tick - previous, target, tid))
                else:
                    legacy_physical.append({**event, "_gameloop": tick - previous})
                selected[ordinal] = event
        offset += size
        previous = tick
    if offset != len(game_bytes):
        raise ValueError("Incomplete physical member traversal")
    if build == 98348:
        exact = encode_game_events(native_physical)
    else:
        # The named writer measures against prior selected time; reconstruct the
        # cumulative total of physical enclosing deltas to check every original frame.
        cursor = 0
        for e in legacy_physical:
            cursor += e["_gameloop"]
            e["_gameloop"] = cursor
        exact = named_encode(legacy_physical, source)
    if exact != physical:
        raise ValueError("Reconstructed issue frames differ from original physical bytes")
    repeated = Counter((e["_userid"]["m_userId"], e["m_sequence"]) for e in selected.values())
    summary = dict(
        replay_sha256=digest,
        build=build,
        issues=sum(flags.values()),
        implicit_points=len(selected),
        ordinary_flag_counts={hex(k): v for k, v in sorted(selected_flags.items())},
        physical_bytes=len(physical),
        physical_sha256=sha256(physical).hexdigest(),
        other_command_records_echo_user_sequence=sum(
            n for (u, s), n in repeated.items() if s in sequence_echo[u]
        ),
        repeated_user_sequences=sum(n - 1 for n in repeated.values()),
        issuing_users=len(issues_by_user),
    )
    if build == 41810:
        summary["all_issue_shapes"] = dict(sorted(shapes.items()))
    else:
        summary["vector_on_otherwise_eligible_point_issues"] = dict(sorted(vectors.items()))
    return selected, summary


def control(case):
    path, digest = case
    return scan(path, digest, 98348)[1]


def generate(source, gate_map):
    """Return {zero-based full source game ordinal: target named issue}, target sparse bytes and evidence."""
    if sha256(gate_map.read_bytes()).hexdigest() != GATE_MAP:
        raise ValueError("Expected the historical GateOrder Dragon Shire package")
    with closing(MPQArchive(gate_map)) as archive:
        width, height = unpack_from("<II", read_member(archive, "MapInfo"), 16)
        terrain = sha256(read_member(archive, "t3SyncHeightMap")).hexdigest()
    if (width, height) != (
        248,
        208,
    ) or terrain != "1e40648f6489f131dfac23717ae530fa32ca6858975e401c9f480df28b166c5f":
        raise ValueError("Unexpected historical map geometry")
    rows, report = scan(source, SOURCE, 41810)
    if report["issues"] != 4558 or Counter(e["m_cmdFlags"] for e in rows.values()) != SOURCE_COUNTS:
        raise ValueError("Unexpected historical issue cohort")
    generated = {}
    frames = []
    target = target_protocol()
    tid = check_schema(target, 98348)
    previous = 0
    for ordinal, e in rows.items():
        point = e["m_data"]["TargetPoint"]
        if not (0 <= point["x"] <= width * 4096 and 0 <= point["y"] <= height * 4096):
            raise ValueError("Point outside historical map bounds")
        row = project(e)
        generated[ordinal] = row
        frames.append(native(row, e["_gameloop"] - previous, target, tid))
        previous = e["_gameloop"]
    raw = encode_game_events(frames)
    if named_encode(list(generated.values()), target) != raw or any(
        a.event != b for a, b in zip(iter_game_events(raw), frames, strict=True)
    ):
        raise ValueError("Sparse named target writer and native codec disagree")
    return (
        generated,
        raw,
        dict(
            source=report,
            target_build=98348,
            layout_sha256=GATE_MAP,
            terrain_sha256=terrain,
            frames=len(generated),
            bytes=len(raw),
            sha256=sha256(raw).hexdigest(),
            ordinal_sha256=sha256(json.dumps(list(generated), separators=(",", ":")).encode()).hexdigest(),
            flag_semantics_verified=False,
            simulation_verified=False,
        ),
    )


def mapped_candidates(legacy, target):
    # Use one zero-bit deletion position for all observed original point flags;
    # the 0x100108 mapping is independently witnessed on first player issues.
    candidates = {}
    for pos in range(25):
        if any(f & (1 << pos) for f in legacy):
            continue
        mapped = tuple(delete_zero_bit(f, pos) for f in legacy)
        if mapped[legacy.index(0x100108)] == 0x80108 and all(f in target for f in mapped):
            candidates[pos] = mapped
    return candidates


def validate_manifest(manifest):
    original = json.loads(
        (Path(first_sync_game.__file__).parent / "observations/first-sync-game.json").read_bytes()
    )
    pins = sorted(r["replay_sha256"] for r in original["references"])
    if (
        len(pins) != 24
        or sha256(" ".join(pins).encode()).hexdigest() != CONTROL_SET
        or sorted(manifest) != pins
    ):
        raise ValueError("Expected pinned 24 recordings")
    return pins


def reference_cohort(manifest, jobs):
    pins = validate_manifest(manifest)
    with ProcessPoolExecutor(jobs) as pool:
        controls = list(pool.map(control, [(Path(manifest[d]), d) for d in pins]))
    target_flags = Counter()
    for row in controls:
        target_flags.update({int(k, 16): v for k, v in row["ordinary_flag_counts"].items()})
        if row["vector_on_otherwise_eligible_point_issues"] != {"absent":row["implicit_points"]}:
            raise ValueError("A target issue with the observed source shape can carry a vector")
    ordered = sorted(LEGACY_FLAGS)
    candidates = mapped_candidates(ordered, target_flags)
    unique = set(candidates.values())
    if unique != {tuple(LEGACY_FLAGS[k] for k in ordered)}:
        raise ValueError(f"Flag model is ambiguous across physical target forms: {unique}")
    if (sum(c["implicit_points"] for c in controls), sum(c["physical_bytes"] for c in controls)) != (
        519318,
        10386360,
    ):
        raise ValueError("Unexpected pinned cohort frame or byte totals")
    return dict(
        controls=controls,
        control_ordinary_flags={hex(k): v for k, v in sorted(target_flags.items())},
        control_physical_frames=sum(c["implicit_points"] for c in controls),
        control_physical_bytes=sum(c["physical_bytes"] for c in controls),
        compatible_zero_bit_positions=sorted(candidates),
        projected_mapping={hex(k): hex(LEGACY_FLAGS[k]) for k in ordered},
    )


def compare_r8(path, generated):
    if sha256(path.read_bytes()).hexdigest() != R8:
        raise ValueError("Expected the original partial R8")
    target = target_protocol()
    with closing(MPQArchive(path)) as archive:
        h = target.decode_replay_header(archive.header["user_data_header"]["content"])
        if (h["m_version"]["m_baseBuild"], h["m_version"]["m_build"], h["m_dataBuildNum"]) != (98285,) * 3:
            raise ValueError("Unexpected R8 version")
        raw = archive.read_file("replay.game.events")
    matched = 0
    for i, e in enumerate(target.decode_replay_game_events(raw)):
        if i in generated:
            keys = ("_gameloop", "_userid", "_eventid", *TARGET_FIELDS)
            if tuple(e.get(k) for k in keys) != tuple(generated[i][k] for k in keys):
                raise ValueError("R8 disagrees with predicted issue ordinal or data")
            matched += 1
    if matched != len(generated):
        raise ValueError("R8 ordinals missing")
    return dict(sha256=R8, build=98285, equal_projected_issues=matched)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("gate_map", type=Path)
    cli.add_argument("--control-manifest", type=Path)
    cli.add_argument("--jobs", type=int, choices=range(1, 5), default=2)
    cli.add_argument("--retained-r8", type=Path)
    cli.add_argument("--private-output", type=Path)
    cli.add_argument("--private-ordinals", type=Path)
    a = cli.parse_args()
    events, raw, report = generate(a.source, a.gate_map)
    if a.control_manifest:
        report.update(reference_cohort(json.loads(a.control_manifest.read_bytes()), a.jobs))
    if a.retained_r8:
        report["retained_r8"] = compare_r8(a.retained_r8, events)
    if a.private_output:
        with a.private_output.open("xb") as out:
            out.write(raw)
    if a.private_ordinals:
        with a.private_ordinals.open("xb") as out:
            out.write(json.dumps(list(events), separators=(",", ":")).encode())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
