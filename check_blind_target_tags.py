"""Leave-one-replay-out reconstruction of stock Dragon Shire command target tags."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

from catalog_diagnostics import UnitTimeline
from project_rank_targets import (
    ANCHORS,
    ROSTER,
    components,
    decode_events,
    encode_events,
    field,
    lifetime_ends,
    members,
    pack,
    pinned,
    protocol96477,
    require,
    startup,
)


def train(task):
    path, digest, _ = task
    game, tracker = members(path, digest, 98348)
    timeline = UnitTimeline(tracker)
    counts = Counter()
    flag_states = Counter()
    for event in protocol96477.decode_replay_game_events(game):
        target = field(event)
        if target is None:
            continue
        flag_states[target["m_targetUnitFlags"], target["m_tag"] not in (0, 0xFFFFFFFF)] += 1
        name, status = timeline.lookup(target["m_tag"], event["_gameloop"], 22)
        if status == "known_alive":
            counts[target["m_snapshotUnitLink"], name] += 1
    return digest, counts, flag_states


def training_links(training, held_out):
    names = defaultdict(set)
    files = Counter()
    for digest, counts, _ in training:
        if digest == held_out:
            continue
        files.update({link for link, _ in counts})
        for link, unit_type in counts:
            names[link].add(unit_type)
    # Disqualify a link on any conflicting type in training. Require two files per retained link.
    return {
        link: next(iter(types)) for link, types in names.items() if len(types) == 1 and files[link] >= 2
    }


def positive_flags(training, held_out):
    support = Counter()
    excluded = set()
    for digest, _, counts in training:
        if digest == held_out:
            continue
        for flags, positive in counts:
            if positive:
                support[flags] += 1
            else:
                excluded.add(flags)
    return sorted(flags for flags, files in support.items() if files >= 2 and flags not in excluded)


def live(identity, loop, ends):
    return 0 < loop < ends.get(identity, float("inf"))


def predict(point, link, loop, groups, startup_xy, ends, links=None):
    xy = point["x"], point["y"]
    candidates = groups.get(xy)
    if not candidates:
        return None, "outside_anchor_xy"
    if links is None:
        if len(startup_xy[xy]) != 1:
            return None, "multiple_startup_units_at_xy"
    else:
        if link not in links:
            return None, "unproven_link"
        wanted = links[link]
        candidates = [(name, key) for name, key in candidates if name == wanted]
        if not candidates:
            return None, "link_type_not_at_xy"
        if startup_xy[xy].count(wanted) != 1:
            return None, "ambiguous_startup_type_at_xy"
    if len(candidates) != 1:
        return None, "ambiguous_anchor"
    _, key = candidates[0]
    if not live(key, loop, ends):
        return None, "outside_initial_lifetime"
    return pack(*key, 22), None


def scope_result():
    return dict(
        predictions=0,
        correct_tags=0,
        wrong_tags=0,
        true_anchor_targets_missed=0,
        abstentions=Counter(),
        wrong_examples=[],
    )


def test(task):
    path, digest, rows, links, flags = task
    game, tracker = members(path, digest, 98348)
    identities = startup(tracker, rows, "target_index")
    anchor_set = set(identities)
    ends = lifetime_ends(tracker, identities)
    startup_xy = defaultdict(list)
    for e in tracker:
        if e["_gameloop"] == 0 and e["_event"].endswith(".SUnitBornEvent"):
            startup_xy[e["m_x"] * 4096, e["m_y"] * 4096].append(e["m_unitTypeName"].decode("ascii"))
    groups = defaultdict(list)
    for row, (_, observed_recycle) in zip(rows, identities):
        groups[row["x"] * 4096, row["y"] * 4096].append(
            (row["type"], (row["target_index"], observed_recycle))
        )
    modes = {
        name: scope_result()
        for name in (
            "xy_only",
            "xy_and_held_out_type",
            "xy_and_held_out_flags",
            "xy_and_held_out_flags_and_type",
        )
    }
    total = target_anchors = 0
    events = list(decode_events(game, protocol96477, "game"))
    for ordinal, e in enumerate(events):
        target = field(e)
        if target is None:
            continue
        total += 1
        loop = e["_gameloop"]
        point, link = target["m_snapshotPoint"], target["m_snapshotUnitLink"]
        xy_guess = predict(point, link, loop, groups, startup_xy, ends)
        typed_guess = predict(point, link, loop, groups, startup_xy, ends, links)
        # All guesses precede reading this command's held-out tag. The flags whitelist comes
        # solely from commands in other recordings and makes no claim about individual bits.
        allowed = target["m_targetUnitFlags"] in flags
        unknown_flags = None, "flag_value_not_confirmed_non_sentinel"
        guesses = (
            xy_guess,
            typed_guess,
            xy_guess if allowed else unknown_flags,
            typed_guess if allowed else unknown_flags,
        )
        original_tag = target["m_tag"]
        actual_key = components(original_tag, 22)
        actual = actual_key in anchor_set and live(actual_key, loop, ends)
        target_anchors += int(actual)
        for (mode, result), (guessed, reason) in zip(modes.items(), guesses):
            if guessed is None:
                result["abstentions"][reason] += 1
                result["true_anchor_targets_missed"] += int(actual)
                continue
            result["predictions"] += 1
            if original_tag == guessed:
                result["correct_tags"] += 1
            else:
                result["wrong_tags"] += 1
                result["true_anchor_targets_missed"] += int(actual)
                if len(result["wrong_examples"]) < 5:
                    result["wrong_examples"].append(
                        dict(
                            ordinal=ordinal,
                            loop=loop,
                            predicted_index=guessed >> 22,
                            recorded_index=actual_key[0],
                            recorded_recycle=actual_key[1],
                        )
                    )
            if mode == "xy_and_held_out_flags":
                target["m_tag"] = guessed
    reconstructed = encode_events(events, protocol96477, "game")
    for result in modes.values():
        require(
            result["predictions"] == result["correct_tags"] + result["wrong_tags"]
            and result["predictions"] + result["abstentions"].total() == total
            and result["true_anchor_targets_missed"] + result["correct_tags"] == target_anchors,
            "Classification accounting",
        )
    return dict(
        replay_sha256=digest,
        all_target_commands=total,
        live_anchor_targets=target_anchors,
        training_links=len(links),
        training_positive_flags=flags,
        modes=modes,
        game_bytes=len(game),
        game_sha256=sha256(game).hexdigest(),
        reconstructed_sha256=sha256(reconstructed).hexdigest(),
        reconstructed_game_byte_equal=game == reconstructed,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("anchors", "roster", "control-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--compact-output", type=Path)
    args = parser.parse_args()
    rows = json.loads(pinned(args.anchors, ANCHORS))
    refs = json.loads(pinned(args.roster, ROSTER))["references"]
    require(len(refs) == len({r["replay_sha256"] for r in refs}) == 12, "Invalid control sample")
    tasks = [(args.control_root / r["replay_file"], r["replay_sha256"], rows) for r in refs]
    with ProcessPoolExecutor(max_workers=3) as pool:
        trained = list(pool.map(train, tasks))
        cases = [
            (*task, training_links(trained, task[1]), positive_flags(trained, task[1]))
            for task in tasks
        ]
        outcomes = list(pool.map(test, cases))
    modes = {}
    for mode in outcomes[0]["modes"]:
        counters = Counter()
        reasons = Counter()
        for row in outcomes:
            data = row["modes"][mode]
            for k in ("predictions", "correct_tags", "wrong_tags", "true_anchor_targets_missed"):
                counters[k] += data[k]
            reasons.update(data["abstentions"])
        modes[mode] = dict(counters, abstentions=dict(sorted(reasons.items())))
    summary = dict(
        total_commands=sum(r["all_target_commands"] for r in outcomes),
        total_live_anchor_targets=sum(r["live_anchor_targets"] for r in outcomes),
        byte_equal_game_members=sum(r["reconstructed_game_byte_equal"] for r in outcomes),
        reconstructed_mode="xy_and_held_out_flags",
        modes=modes,
    )
    report = dict(
        anchor_table_sha256=ANCHORS,
        roster_sha256=ROSTER,
        controls=outcomes,
        summary=summary,
        criteria="Use exact X/Y, loop strictly inside first recorded lifetime, and observed initial recycle. "
        "The X/Y test excludes shared startup coordinates. Typed test requires unique initial "
        "type+position and only one tracker type for its link in at least two of the other eleven "
        "controls. The flags test accepts a full m_targetUnitFlags value only when non-sentinel "
        "tags were observed in at least two other controls and no sentinel tag occurred with "
        "that flags value in any other control. Every prediction precedes access to the test command tag.",
    )
    reports = [(args.output, report)]
    if args.compact_output:
        concise = [
            dict(
                replay_sha256=r["replay_sha256"],
                game_sha256=r["game_sha256"],
                commands=r["all_target_commands"],
                positive_flags=r["training_positive_flags"],
                correct_tags=r["modes"]["xy_and_held_out_flags"]["correct_tags"],
                wrong_tags=r["modes"]["xy_and_held_out_flags"]["wrong_tags"],
                xy_only_errors=r["modes"]["xy_only"]["wrong_tags"],
                reconstructed_game_byte_equal=r["reconstructed_game_byte_equal"],
            )
            for r in outcomes
        ]
        reports.append(
            (
                args.compact_output,
                dict(
                    anchor_table_sha256=ANCHORS, roster_sha256=ROSTER, controls=concise, summary=summary
                ),
            )
        )
    for path, value in reports:
        output = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        if path.exists():
            require(path.read_bytes() == output, "Existing output differs")
        else:
            with path.open("xb") as output_file:
                output_file.write(output)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
