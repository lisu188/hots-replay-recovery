"""Test same-user, same-loop issue/update/manager brackets in replay game events."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol

RESET, ISSUE, MANAGER, POINT, UNIT = 25, 27, 103, 104, 105
KINDS = {RESET, ISSUE, MANAGER, POINT, UNIT}


def score_game(events):
    total = Counter()
    eligible = defaultdict(Counter)
    states = defaultdict(Counter)
    examples = {}

    # score_group receives events from exactly one user and game loop, with sequences
    # removed from all updates. Only score() receives the detached truth for comparison.
    def score_group(rows, truth, loop):
        next_manager = None
        right = {}
        for i in reversed(range(len(rows))):
            kind, seq, state = rows[i]
            if kind == MANAGER:
                next_manager = seq, state
            elif kind in (POINT, UNIT):
                right[i] = next_manager
        issue = None
        for i, (kind, seq, state) in enumerate(rows):
            if kind == ISSUE:
                issue = seq
            if kind not in (POINT, UNIT):
                continue
            real = truth[i]
            total["updates"] += 1
            total["actual_present" if real is not None else "actual_absent"] += 1
            total["point" if kind == POINT else "unit"] += 1
            if issue is None or right[i] is None:
                continue
            manager, state = right[i]
            if manager is None:
                continue
            adjacent = (
                i > 0
                and i + 1 < len(rows)
                and rows[i - 1][0] == ISSUE
                and rows[i + 1][0] == MANAGER
            )
            for label, applies, value in (
                ("adjacent_equal", adjacent and issue == manager, issue),
                ("nearest_equal", issue == manager, issue),
                ("nearest_disagree_left", issue != manager, issue),
                ("nearest_disagree_right", issue != manager, manager),
            ):
                if not applies:
                    continue
                record = eligible[label]
                record["eligible"] += 1
                result = (
                    "exact"
                    if real == value
                    else ("actual_absent" if real is None else "wrong_value")
                )
                record[result] += 1
                record["point" if kind == POINT else "unit"] += 1
                states[label][f"{state}.{result}"] += 1
                if result != "exact" and label not in examples:
                    examples[label] = dict(
                        loop=loop,
                        kind=kind,
                        prior_issue=issue,
                        following_manager=manager,
                        following_state=state,
                        observed_update=real,
                    )

    last = None
    groups = defaultdict(list)
    truth = defaultdict(dict)
    for e in events:
        kind = e["_eventid"]
        if kind not in KINDS:
            continue
        loop = e["_gameloop"]
        if last is not None and loop < last:
            raise ValueError("Game events out of chronological order")
        if last is not None and loop != last:
            for user, rows in groups.items():
                score_group(rows, truth[user], last)
            groups.clear()
            truth.clear()
        last = loop
        user = e["_userid"]["m_userId"]
        if kind in (POINT, UNIT):
            truth[user][len(groups[user])] = e.pop("m_sequence")
        groups[user].append((kind, e.get("m_sequence"), e.get("m_state")))
    for user, rows in groups.items():
        score_group(rows, truth[user], last)
    return dict(
        total=total,
        rules=eligible,
        manager_states=states,
        first_counterexample=examples,
    )


def inspect(path, expected, build):
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError("Input SHA-256 differs")
    p = load_protocol({41810: 41810, 98348: 96477}[build])
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (
            h["m_version"]["m_build"],
            h["m_version"]["m_baseBuild"],
            h["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Incorrect build")
        raw = a.read_file("replay.game.events")
    return dict(
        build=build,
        replay_sha256=digest,
        game_sha256=sha256(raw).hexdigest(),
        **score_game(p.decode_replay_game_events(raw)),
    )


def summarize(cases):
    aggregates = {}
    for build in sorted({r["build"] for r in cases}):
        cohort = [r for r in cases if r["build"] == build]
        totals = Counter()
        rules = defaultdict(Counter)
        states = defaultdict(Counter)
        example = None
        for r in cohort:
            totals.update(r["total"])
            for name, counts in r["rules"].items():
                rules[name].update(counts)
            for name, counts in r["manager_states"].items():
                states[name].update(counts)
            if example is None and "adjacent_equal" in r["first_counterexample"]:
                example = dict(
                    replay_sha256=r["replay_sha256"],
                    **r["first_counterexample"]["adjacent_equal"],
                )
        aggregates[build] = dict(
            replay_count=len(cohort),
            total=totals,
            rules=rules,
            manager_states=states,
            first_adjacent_counterexample=example,
        )
    return dict(
        format="hots-same-user-same-loop-sequence-brackets-v1", aggregate=aggregates
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="legacy-command-sequences.json, containing the pinned cohort",
    )
    ap.add_argument("replay", type=Path, nargs="+")
    args = ap.parse_args()
    m = json.loads(args.manifest.read_bytes())
    roster = [m["source"], *m["historical_controls"], *m["current_controls"]]
    by_sha = {sha256(path.read_bytes()).hexdigest(): path for path in args.replay}
    if (
        len({r["replay_sha256"] for r in roster}) != len(roster)
        or len(by_sha) != len(args.replay)
        or set(by_sha) != {r["replay_sha256"] for r in roster}
    ):
        ap.error("Replay files differ from the manifest or contain duplicates")
    cases = [
        inspect(by_sha[r["replay_sha256"]], r["replay_sha256"], r["build"])
        for r in roster
    ]
    print(json.dumps(summarize(cases), indent=2))
