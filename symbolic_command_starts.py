"""Count physically referenced command sequences with no recorded issue and compare known state-2 creators."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol

BUILD_SCHEMA = {b: b for b in (39445, 39951, 41150, 41810, 42178, 42273)} | {
    b: 96477 for b in (97605, 98285, 98304, 98348)
}
CANONICAL = {
    39445: "0898b2e8608c58b24a4a8f71585af7a028a0265d4d61a8074c124de97a577148",
    39951: "0898b2e8608c58b24a4a8f71585af7a028a0265d4d61a8074c124de97a577148",
    41150: "be0c0a8785c9a3f657157f80d16514e00b8ac978a6f9d148362fcdb3c151e752",
    41810: "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd",
    42178: "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd",
    42273: "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd",
    96477: "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84",
}
FAMILY = {25, 27, 103, 104, 105}
COHORT = "be1b28e7b8bd865bca9500fb1539713904a90e829437e187939360ab8621563d"


def members(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Replay digest mismatch")
    schema = BUILD_SCHEMA[build]
    p = load_protocol(schema)
    if sha256(Path(p.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != CANONICAL[schema]:
        raise ValueError("Unexpected upstream game grammar")
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        version = h["m_version"]
        if (version["m_build"], version["m_baseBuild"]) != (build, build):
            raise ValueError("Recording build/base mismatch")
        data_build = h["m_dataBuildNum"]
        if data_build != {39951: 40322, 41150: 41393}.get(build, build):
            raise ValueError("Unknown data build")
        raw = arc.read_file("replay.game.events")
    return p, raw, data_build


def shape(e):
    return "/".join(
        (
            hex(e["m_cmdFlags"]),
            "implicit" if e["m_abil"] is None else "explicit",
            next(iter(e["m_data"])),
            "other" if e.get("m_otherUnit") is not None else "-",
            "group" if e.get("m_unitGroup") is not None else "-",
            "vector" if e.get("m_vector") is not None else "-",
        )
    )


def relation(issue, target_update):
    kind = target_update["_eventid"]
    if kind not in (104, 105):
        raise ValueError("Expected point or unit update")
    value = issue["m_data"].get("TargetPoint" if kind == 104 else "TargetUnit")
    if value is None:
        return "different_target_kind"
    if kind == 104:
        return "identical_point" if value == target_update["m_target"] else "changed_point"
    return "same_unit_tag" if value["m_tag"] == target_update["m_target"]["m_tag"] else "changed_unit_tag"


def audit(path, digest, build):
    p, raw, data_build = members(path, digest, build)
    first_use = {}
    last_family = {}
    issues = defaultdict(list)
    pairs = []
    recorded_types = Counter()
    all_states = Counter()
    bit19_issues = Counter()
    bit19_first_updates = Counter()
    first_update_keys = set()
    case_frames = {}
    prior = offset = 0
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        k = e["_eventid"]
        t = e["_gameloop"]
        u = e["_userid"]["m_userId"]
        end = offset + e["_bits"] // 8
        if e["_bits"] % 8 or end <= offset or end > len(raw) or t < prior:
            raise ValueError("Physical game event boundaries")
        if k in FAMILY:
            seq = e.get("m_sequence")
            key = (u, seq)
            if k == 27:
                issues[key].append((ordinal, e))
                if build >= 97605 and e["m_cmdFlags"] & (1 << 19):
                    bit19_issues[shape(e)] += 1
            elif k in (103, 104, 105) and seq is not None:
                first_use.setdefault(key, (ordinal, k, t))
                if k in (104, 105) and key not in first_update_keys:
                    first_update_keys.add(key)
                    earlier = issues.get(key, ())
                    if build >= 97605 and len(earlier) == 1 and earlier[0][1]["m_cmdFlags"] & (1 << 19):
                        src = earlier[0][1]
                        relationship = relation(src, e)
                        bit19_first_updates[str(k) + "/" + relationship + "/" + shape(src)] += 1
            if k == 103:
                all_states[str(e["m_state"])] += 1
                old = last_family.get(u)
                if old and old[1]["_eventid"] in (104, 105) and old[1]["_gameloop"] == t:
                    n, a, prev, physical = old
                    s = a.get("m_sequence")
                    state = e["m_state"]
                    recorded_types[
                        f"{a['_eventid']}/{state}/"
                        + (
                            "no_update_sequence_field"
                            if "m_sequence" not in a
                            else (
                                "both_absent"
                                if s is None and seq is None
                                else "paired_numeric" if s is not None and s == seq else "different"
                            )
                        )
                    ] += 1
                    if state == 2 and seq is not None and s == seq:
                        case_frames[n] = (a, prev, physical)
                        case_frames[ordinal] = (e, prior, raw[offset:end])
                        pairs.append((key, n, ordinal, a))
            last_family[u] = (ordinal, e, prior, raw[offset:end])
        prior = t
        offset = end
    if offset != len(raw):
        raise ValueError("Incomplete game member")
    # Same-user adjacent need not be adjacent globally. Replay original enclosing delta for each frame.
    elapsed = 0
    check = []
    physical = bytearray()
    for _, (e, prev, frame) in sorted(case_frames.items()):
        elapsed += e["_gameloop"] - prev
        check.append({**e, "_gameloop": elapsed})
        physical.extend(frame)
    if encode_game_events(check, p) != physical:
        raise ValueError("Physical state-2/update pairs differ from named wire")
    counts = Counter()
    known = Counter()
    coincident = Counter()
    symbolic = {}
    future_shapes = Counter()
    future_delays = Counter()
    future_point = Counter()
    for key, n, manager, a in pairs:
        k = a["_eventid"]
        kind = "point" if k == 104 else "unit"
        all_issues = issues.get(key, ())
        before = [e for i, e in all_issues if i < n]
        if not before and not all_issues:
            status = "never_issued"
        elif not before:
            status = "issued_later"
        elif len(before) == 1:
            status = "one_prior_issue"
        else:
            status = "multiple_prior_issues"
        counts[kind + "/" + status] += 1
        if status == "issued_later":
            future = all_issues[0][1]
            future_shapes[kind + "/" + shape(future)] += 1
            future_delays[str(future["_gameloop"] - a["_gameloop"])] += 1
            relationship = relation(future, a)
            future_point[kind + "/" + relationship] += 1
        if status == "one_prior_issue":
            creator = before[0]
            known[kind + "/" + shape(creator)] += 1
            coincident[kind + "/" + relation(creator, a)] += 1
        if status == "never_issued" and first_use[key][0] == n:
            if key in symbolic:
                raise ValueError("Duplicate first-use candidate")
            symbolic[key] = (n, manager, a)
    entries = [
        [n, manager, e["_gameloop"], u, s, e["_eventid"], e["m_target"]]
        for (u, s), (n, manager, e) in symbolic.items()
    ]
    entries.sort(key=lambda r: r[0])
    missing = {k for k in first_use if k not in issues}
    unexplained = Counter(str(first_use[k][1]) for k in missing if k not in symbolic)
    report = dict(
        build=build,
        data_build=data_build,
        replay_sha256=digest,
        game_sha256=sha256(raw).hexdigest(),
        game_bytes=len(raw),
        schema_build=BUILD_SCHEMA[build],
        schema_lf_sha256=CANONICAL[BUILD_SCHEMA[build]],
        issued_sequence_keys=len(issues),
        update_sequence_in_grammar=[
            "m_sequence" in {f[0] for f in p.typeinfos[p.game_event_types[k][0]][1][0]} for k in (104, 105)
        ],
        explicit_lookup_keys=len(first_use),
        never_issued_lookup_keys=len(missing),
        paired_state2_contexts=dict(sorted(counts.items())),
        symbolic_first_use=dict(Counter("point" if r[-2] == 104 else "unit" for r in entries)),
        other_never_issued_first_event_ids=dict(unexplained),
        one_prior_creator_shapes=dict(sorted(known.items())),
        all_manager_states=dict(sorted(all_states.items())),
        modern_issue_shapes_with_bit19=dict(sorted(bit19_issues.items())),
        modern_first_target_updates_of_unique_prior_bit19_issues=dict(sorted(bit19_first_updates.items())),
        later_issue_shapes=dict(sorted(future_shapes.items())),
        later_issue_loop_delays=dict(sorted(future_delays.items())),
        later_issue_target_comparison=dict(sorted(future_point.items())),
        update_agrees_with_issue_target=dict(coincident),
        all_same_loop_update_manager_pairs=dict(sorted(recorded_types.items())),
        physical_state2_frames=len(check),
        physical_state2_bytes=len(physical),
        physical_state2_sha256=sha256(physical).hexdigest(),
        generated_issues=0,
    )
    return entries, report


def one(case):
    return audit(*case)[1]


def references(refs):
    keys = " ".join(h + "/" + str(refs[h]["build"]) for h in sorted(refs))
    if len(refs) != 62 or sha256(keys.encode()).hexdigest() != COHORT:
        raise ValueError("Expected the 62 independent pinned recordings")
    return [(Path(v["path"]), d, v["build"]) for d, v in sorted(refs.items())]


def summarize(rows):
    if len({r["game_sha256"] for r in rows}) != 63:
        raise ValueError("Expected independent physical game members for all 63 replays")
    by_build = {}
    for build in sorted(set(r["build"] for r in rows)):
        selection = [r for r in rows if r["build"] == build]

        def total(key):
            return dict(sorted(sum((Counter(r[key]) for r in selection), Counter()).items()))

        by_build[str(build)] = dict(
            recordings=len(selection),
            symbolic_first_use=total("symbolic_first_use"),
            all_manager_states=total("all_manager_states"),
            never_issued_lookup_keys=sum(r["never_issued_lookup_keys"] for r in selection),
            physical_state2_frames=sum(r["physical_state2_frames"] for r in selection),
        )
    return by_build


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("--manifest", type=Path, help="JSON mapping replay SHA to {build, path}")
    cli.add_argument("--private-ledger", type=Path)
    cli.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    args = cli.parse_args()
    ledger, report = audit(args.source, SOURCE, 41810)
    result = {"source": report}
    if args.manifest:
        refs = json.loads(args.manifest.read_bytes())
        cases = references(refs)
        with ProcessPoolExecutor(args.jobs) as pool:
            result["controls"] = list(pool.map(one, cases))
        result["by_build_including_source"] = summarize([report, *result["controls"]])
    if args.private_ledger:
        with args.private_ledger.open("x", encoding="utf8") as out:
            json.dump(ledger, out, separators=(",", ":"))
    print(json.dumps(result, indent=2))
