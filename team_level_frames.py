"""Project post-start level notifications from a recorded team-level clock and lobby roster."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from clocked_objective_stats import check, item, stat, teams
from dragon_reset_wire import COHORT
from encoders import encode_tracker_events
from first_sync_tracker import stock_scripts
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


def clock(rows, player):
    result = {}
    for e in rows:
        data = {v["m_key"]: v["m_value"] for v in e["m_intData"]}
        if data[b"PlayerID"] == player and data[b"Level"] > 1:
            level = data[b"Level"]
            check(level not in result, "Ambiguous team-level anchor")
            result[level] = e["_gameloop"]
    check(
        list(result) == list(range(2, 2 + len(result))),
        "Level progression skipped or reordered",
    )
    return result


def project(path, protocol, raw):
    decoded = list(protocol.decode_replay_tracker_events(raw))
    roster = teams(path, protocol, decoded)
    levels = [e for e in decoded if e.get("m_eventName") == b"LevelUp"]
    predictions = {}
    for team in (1, 2):
        players = sorted(p for p, t in roster.items() if t == team)
        clocks = [clock(levels, p) for p in (players[0], players[-1])]
        if clocks[0] != clocks[1]:
            return [], "team clocks disagree"
        for lvl, tick in clocks[0].items():
            if (tick, team) in predictions:
                return [], "multiple team levels on one tick"
            predictions[tick, team] = [
                stat(
                    tick, b"LevelUp", [item(b"PlayerID", p), item(b"Level", lvl)], None
                )
                for p in players
            ]
    # Ordering between both teams on the same tick needs a separate producer.
    if len({tick for tick, _ in predictions}) != len(predictions):
        return [], "both teams leveled at the same time"
    rows = [e for k in sorted(predictions) for e in predictions[k]]
    physical = [
        e
        for e in levels
        if next(v["m_value"] for v in e["m_intData"] if v["m_key"] == b"Level") > 1
    ]
    if rows != [{k: v for k, v in e.items() if k != "_bits"} for e in physical]:
        return [], "order, time, or payload differs from the five-player projection"
    target = target_protocol()
    offset = prior = selected = 0
    for e in decoded:
        n, remain = divmod(e["_bits"], 8)
        check(n and not remain, "Invalid physical frame size")
        if selected < len(physical) and e is physical[selected]:
            predicted = {
                **rows[selected],
                "_gameloop": rows[selected]["_gameloop"] - prior,
            }
            check(
                encode_tracker_events([predicted], target) == raw[offset : offset + n],
                "Physical level frame differs",
            )
            selected += 1
        prior = e["_gameloop"]
        offset += n
    check(offset == len(raw) and selected == len(rows), "Incomplete tracker readback")
    return rows, None


def verify(legacy, current, evidence, scripts):
    stock_scripts(scripts)
    cohort = json.loads(evidence.read_bytes())
    check(
        sha256(
            json.dumps(cohort, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == COHORT,
        "Unexpected control group",
    )
    report = []
    for build, field, manifest in (
        (41810, "old_replays", legacy),
        (98348, "target_controls", current),
    ):
        paths = json.loads(manifest.read_bytes())
        for case in cohort[field]:
            digest = case["sha256"]
            path = Path(paths[digest])
            check(
                sha256(path.read_bytes()).hexdigest() == digest, "Unexpected recording"
            )
            protocol, raw, _ = read_tracker(path, build)
            rows, reason = project(path, protocol, raw)
            if digest == SOURCE:
                check(
                    len(rows) == 210 and not reason,
                    "Original team projection incomplete",
                )
            report.append(
                dict(
                    build=build,
                    replay_sha256=digest,
                    frames=len(rows),
                    withheld_reason=reason,
                )
            )
    counts = Counter()
    for case in report:
        counts[case["build"]] += case["frames"]
    return dict(
        cases=report,
        source_clock="first lobby-mapped teammate, checked against the last teammate and every physical row",
        verified_target_xp_clock=False,
        frames_by_build=dict(counts),
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("legacy", "current", "evidence", "scripts"):
        cli.add_argument(name, type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())), indent=2))
