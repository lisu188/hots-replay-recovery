"""Test the cross-layout authored transfer's exact fixed-point coordinates on 98348 controls."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path

from map_startup_identity import BIRTH, match_startup
from plan_authored_targets import join_layouts, layout, write_once
from project_rank_targets import (
    components,
    decode_events,
    encode_events,
    field,
    lifetime_ends,
    members,
    pack,
    protocol96477,
    require,
)


def fixed(row):
    return row.x * 4096, row.y * 4096


def examine(path, digest, target_rows, players, common):
    game, tracker = members(path, digest, 98348)
    checked, startup = match_startup(target_rows, tracker)
    require(startup["verified"] == len(target_rows), "Incomplete observed target layout")
    checked_births = {a.event_offset for a in checked}
    # A non-authored startup unit has only tracker integer tile coordinates; abstain on its entire tile.
    unknown_tiles = {
        (e["m_x"], e["m_y"])
        for n, e in enumerate(tracker)
        if n not in checked_births and e["_gameloop"] == 0 and e["_event"] == BIRTH
    }
    candidates = defaultdict(set)
    for rank, row in enumerate(target_rows):
        x, y = fixed(row)
        # All four floor/ceil candidates from every placement can veto a prospective fixed point.
        for fx in {floor(x), ceil(x)}:
            for fy in {floor(y), ceil(y)}:
                candidates[fx, fy].add(rank)
    keys = {(r, 1) for r in common}
    ends = lifetime_ends(tracker, keys)
    owner_ends = {}
    for e in tracker:
        if e["_event"].endswith(".SUnitOwnerChangeEvent"):
            owner_ends.setdefault((e["m_unitTagIndex"], e["m_unitTagRecycle"]), e["_gameloop"])
    events = list(decode_events(game, protocol96477, "game"))
    stats = Counter()
    for event in events:
        target = field(event)
        if target is None:
            continue
        stats["all_command_targets"] += 1
        loop = event["_gameloop"]
        xy = target["m_snapshotPoint"]["x"], target["m_snapshotPoint"]["y"]
        ranks = candidates.get(xy, ())
        guess = None
        if (
            target["m_targetUnitFlags"] == 111
            and len(ranks) == 1
            and (xy[0] // 4096, xy[1] // 4096) not in unknown_tiles
        ):
            rank = next(iter(ranks))
            key = rank, 1
            row = target_rows[rank]
            if key in keys and fixed(row) == xy and 0 < loop < ends.get(key, float("inf")):
                guess = pack(rank, 1, 22)
        # The command's input tag and owner fields are held out from the predictor.
        recorded = target["m_tag"]
        original_key = components(recorded, 22)
        if original_key in keys and 0 < loop < ends.get(original_key, float("inf")):
            stats["recorded_live_common_objects"] += 1
        if guess is None:
            continue
        group = "integer" if row.x == int(row.x) and row.y == int(row.y) else "fractional"
        stats[group + "_predictions"] += 1
        stats[group + ("_correct" if guess == recorded else "_wrong")] += 1
        target["m_tag"] = guess
        if loop < owner_ends.get(key, float("inf")):
            player = players[row.object_id]
            original_pair = target["m_snapshotControlPlayerId"], target["m_snapshotUpkeepPlayerId"]
            stats["owner_pairs_predicted"] += 1
            stats[
                "owner_pairs_correct" if original_pair == (player, player) else "owner_pairs_wrong"
            ] += 1
            target["m_snapshotControlPlayerId"] = target["m_snapshotUpkeepPlayerId"] = player
    predicted_wire = encode_events(events, protocol96477, "game")
    return dict(
        replay_sha256=digest,
        counts=dict(sorted(stats.items())),
        original_game_sha256=sha256(game).hexdigest(),
        reconstructed_game_sha256=sha256(predicted_wire).hexdigest(),
        game_byte_equal=game == predicted_wire,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-map", "target-map", "control-root", "selection", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    old, _, _ = layout(args.source_map, 41810)
    cur, players, _ = layout(args.target_map, 98348)
    common = set(join_layouts(old, cur).values())
    controls = json.loads(args.selection.read_bytes())["cases"]
    results = [
        examine(
            args.control_root / (r["replay_sha256"] + ".StormReplay"),
            r["replay_sha256"],
            cur,
            players,
            common,
        )
        for r in controls
    ]
    report = dict(
        exact_cross_layout_objects=len(common),
        controls=results,
        scope="Follow-up on the two already used external recordings. Frozen full flags value 111. "
        "Rank, initial recycle and both owner values come from authored placement/rule. "
        "Target command-time owner prediction stops at the first observed owner transition.",
    )
    write_once(args.output, report)
    print(json.dumps(results))


if __name__ == "__main__":
    main()
