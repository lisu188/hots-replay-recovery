"""Score and project point-update and command-manager sequences in contiguous single-user command intervals."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as named_encode
from first_sync_game import game
from implicit_point_issues import eligible, validate_manifest
from native_game_events import GameEvent, encode_game_events, iter_game_events
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from smartcam_tags import R8

FAMILY = {25, 27, 103, 104, 105}
RULES = (
    "first_later",
    "first_later_closed",
    "first_later_no_manager_closed",
    "chain",
    "chain_firstsame",
    "chain_closed",
    "manager0",
    "manager0_closed",
    "manager0_after_updates_closed",
    "manager0_firstsame_latest_same",
    "manager0_firstsame_latest_same_closed",
    "manager0_next_consecutive",
    "first_later_reverse_consecutive",
    "chain_reverse_consecutive",
    "single_recorded_issue_point",
    "single_recorded_issue_manager0",
)
SELECTED = ("first_later_no_manager_closed", "chain_firstsame", "manager0_firstsame_latest_same_closed")


def score_single_issue(open_issues, event, scores):
    # Candidate model only. It never uses a manager/update's own sequence to choose
    # an issue or decide whether to remove it. Multiple pending issues stay ambiguous.
    kind = event["_eventid"]
    if kind == 25:
        open_issues.clear()
    elif kind == 27:
        open_issues.append(event["m_sequence"])
        if len(open_issues) > 2:
            del open_issues[0]
    elif len(open_issues) == 1 and (kind == 104 or kind == 103 and event["m_state"] == 0):
        (predicted,) = open_issues
        truth = event["m_sequence"]
        rule = "single_recorded_issue_point" if kind == 104 else "single_recorded_issue_manager0"
        scores[rule]["absent" if truth is None else "match" if truth == predicted else "different"] += 1
        if kind == 103:
            open_issues.clear()


def intervals(p, raw, build, scores):
    """A reset or new issue terminates a user's open interval. Other users' records do not affect it."""
    active = {}
    open_issues = {}
    offset = previous = 0
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        end = offset + e["_bits"] // 8
        tick = e["_gameloop"]
        if e["_bits"] % 8 or end <= offset or end > len(raw) or tick < previous:
            raise ValueError("Invalid game frame bounds")
        kind = e["_eventid"]
        user = e["_userid"]["m_userId"]
        if kind in FAMILY:
            score_single_issue(open_issues.setdefault(user, []), e, scores)
        if kind in (25, 27):
            pending = active.pop(user, None)
            if pending:
                yield (*pending, e if kind == 27 else None)
            if kind == 27 and eligible(e) and e["m_cmdFlags"] == {41810: 0x100108, 98348: 0x80108}[build]:
                active[user] = (e, [])
        elif kind in FAMILY and user in active:
            active[user][1].append((ordinal, e, previous, raw[offset:end]))
        offset, previous = end, tick
    if offset != len(raw):
        raise ValueError("Incomplete game member")
    for issue, rows in active.values():
        yield issue, rows, None


def candidates(issue, rows, next_issue):
    # The next issue from this user may corroborate numbering, but manager and target
    # update sequences are hidden throughout admission and prediction.
    pred = issue["m_sequence"]
    consecutive = next_issue is not None and next_issue["m_sequence"] == pred + 1
    m = bool(rows and rows[-1][1]["_eventid"] == 103 and rows[-1][1]["m_state"] == 0)
    clean = all(r[1]["_eventid"] == 104 for r in (rows[:-1] if m else rows))
    closed = consecutive and clean
    issue_tick = issue["_gameloop"]
    first_same = bool(
        rows
        and rows[0][1]["_eventid"] == 104
        and rows[0][1]["_gameloop"] == issue_tick
        and rows[0][1]["m_target"] != issue["m_data"]["TargetPoint"]
    )
    for i, row in enumerate(rows):
        _, e, _, _ = row
        kind = e["_eventid"]
        flags = []
        if kind == 104:
            if i == 0 and e["_gameloop"] > issue_tick:
                flags.append("first_later")
                if closed:
                    flags.append("first_later_closed")
                    if not m:
                        flags.append("first_later_no_manager_closed")
                if consecutive:
                    flags.append("first_later_reverse_consecutive")
            elif i and e["_gameloop"] > issue_tick:
                flags.append("chain")
                if first_same:
                    flags.append("chain_firstsame")
                if closed:
                    flags.append("chain_closed")
                if consecutive:
                    flags.append("chain_reverse_consecutive")
        elif kind == 103 and e["m_state"] == 0:
            flags.append("manager0")
            if closed:
                flags.append("manager0_closed")
                if i:
                    flags.append("manager0_after_updates_closed")
            if consecutive and i == len(rows) - 1:
                flags.append("manager0_next_consecutive")
            if i and first_same and rows[i - 1][1]["_gameloop"] == e["_gameloop"]:
                flags.append("manager0_firstsame_latest_same")
                if closed:
                    flags.append("manager0_firstsame_latest_same_closed")
        if flags:
            yield row, pred, flags
        if kind != 104:
            break


def scan(path, digest, build, selected=()):
    p, game_bytes = game(path, digest, build)
    target = target_protocol()
    scores = {k: Counter() for k in RULES}
    emitted = {}
    for issue, rows, next_issue in intervals(p, game_bytes, build, scores):
        for row, pred, rules in candidates(issue, rows, next_issue):
            ordinal, e, prev, physical = row
            actual = e["m_sequence"]
            label = "absent" if actual is None else "match" if actual == pred else "different"
            for rule in rules:
                scores[rule][label] += 1
            if not any(rule in selected for rule in rules):
                continue
            if build == 41810 and actual is not None:
                # Explicit historical values are handled by the separate direct writer.
                continue
            if build == 98348 and actual != pred:
                raise ValueError("Physical target counterexample to selected rule")
            if ordinal in emitted:
                raise ValueError("Repeated original ordinal")
            emitted[ordinal] = ({**e, "m_sequence": pred}, prev, physical)
    ordered = sorted(emitted.items())
    rows, expect, physical_frames = {}, bytearray(), []
    historical_frames = []
    historical_elapsed = 0
    sparse = []
    last = 0
    for ordinal, (e, prev, physical) in ordered:
        kind = e["_eventid"]
        tid = target.game_event_types[kind][0]
        data = _anonymous({k: e[k] for k, _, _ in target.typeinfos[tid][1][0]}, target.typeinfos, tid)
        user = e["_userid"]["m_userId"]
        sparse.append(GameEvent(e["_gameloop"] - last, user, kind, data))
        expect.extend(physical)
        if build == 98348:
            physical_frames.append(GameEvent(e["_gameloop"] - prev, user, kind, data))
        else:
            historical_elapsed += e["_gameloop"] - prev
            historical_frames.append({**e, "m_sequence": None, "_gameloop": historical_elapsed})
        rows[ordinal] = e
        last = e["_gameloop"]
    physical_check = (
        encode_game_events(physical_frames) if build == 98348 else named_encode(historical_frames, p)
    )
    if physical_check != expect:
        raise ValueError("Reconstructed frame differs from original enclosing bytes")
    stream = encode_game_events(sparse)
    if named_encode(list(rows.values()), target) != stream or any(
        a.event != b for a, b in zip(iter_game_events(stream), sparse, strict=True)
    ):
        raise ValueError("Target codec failure")
    return (
        rows,
        stream,
        dict(
            build=build,
            replay_sha256=digest,
            rules=scores,
            emitted=len(rows),
            by_kind=Counter(str(e["_eventid"]) for e in rows.values()),
            sparse_bytes=len(stream),
            sparse_sha256=sha256(stream).hexdigest(),
            enclosing_bytes=len(expect),
            enclosing_sha256=sha256(expect).hexdigest(),
        ),
    )


def run_control(args):
    return scan(*args)[2]


def generate(source):
    """Return source-ordinal named events, sparse bytes and report for TEN's 382 omitted sequences."""
    events, raw, report = scan(source, SOURCE, 41810, SELECTED)
    if report["emitted"] != 382 or report["by_kind"] != {"104": 371, "103": 11}:
        raise ValueError("Unexpected TEN interval projection")
    return events, raw, report


def compare_r8(path, events):
    if sha256(path.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected R8")
    p = target_protocol()
    with closing(MPQArchive(path)) as arc:
        header = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (
            header["m_version"]["m_build"],
            header["m_version"]["m_baseBuild"],
            header["m_dataBuildNum"],
        ) != (98285,) * 3:
            raise ValueError("Unexpected R8 build")
        raw = arc.read_file("replay.game.events")
    counts = Counter()
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        if ordinal not in events:
            continue
        expected = events[ordinal]
        payload = "m_target" if e["_eventid"] == 104 else "m_state"
        if any(expected[k] != e[k] for k in ("_eventid", "_gameloop", "_userid", payload)):
            raise ValueError("R8 changes interval event context")
        counts[
            (
                "absent"
                if e["m_sequence"] is None
                else (
                    "matching_explicit"
                    if e["m_sequence"] == expected["m_sequence"]
                    else "different_explicit"
                )
            )
        ] += 1
    if counts.total() != len(events):
        raise ValueError("R8 ordinal gap")
    return dict(build=98285, replay_sha256=R8, existing=counts)


def cohort(manifest, jobs, selected):
    pins = validate_manifest(manifest)
    with ProcessPoolExecutor(jobs) as pool:
        controls = list(pool.map(run_control, [(Path(manifest[h]), h, 98348, selected) for h in pins]))
    grouped = {}
    for name, chunk in (("discovery", controls[:8]), ("heldout", controls[8:])):
        grouped[name] = {
            rule: dict(sum((Counter(c["rules"][rule]) for c in chunk), Counter())) for rule in RULES
        }
    for name, test_counts in {"discovery": (2212, 5530, 730), "heldout": (4857, 15372, 1535)}.items():
        for rule, n in zip(SELECTED, test_counts, strict=True):
            if grouped[name][rule] != {"match": n}:
                raise ValueError("Selected rule fails the pinned independent comparison")
    return grouped, controls


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("--control-manifest", type=Path)
    cli.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    cli.add_argument("--retained-r8", type=Path)
    cli.add_argument("--private-output", type=Path)
    cli.add_argument("--private-ordinals", type=Path)
    a = cli.parse_args()
    events, raw, source_report = generate(a.source)
    report = dict(
        source=source_report, selected=SELECTED, target_build=98348, target_simulation_verified=False
    )
    if a.control_manifest:
        grouped, controls = cohort(json.loads(a.control_manifest.read_bytes()), a.jobs, SELECTED)
        report.update(
            validation=grouped,
            controls=controls,
            physical_target_frames=sum(x["emitted"] for x in controls),
            physical_target_bytes=sum(x["enclosing_bytes"] for x in controls),
        )
    if a.retained_r8:
        report["retained_r8"] = compare_r8(a.retained_r8, events)
    if a.private_output:
        with a.private_output.open("xb") as out:
            out.write(raw)
    if a.private_ordinals:
        with a.private_ordinals.open("xb") as out:
            out.write(json.dumps(list(events), separators=(",", ":")).encode())
    print(json.dumps(report, indent=2))
