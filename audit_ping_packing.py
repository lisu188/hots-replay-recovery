"""Offline aggregate for event 36. CLI accepts path, digest, build triples."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol


def require(test, message):
    if not test:
        raise ValueError(message)


def measure(args):
    path, digest, build = args
    build = int(build)
    p = load_protocol({41810: 41810, 98348: 96477}[build])
    require(sha256(Path(path).read_bytes()).hexdigest() == digest, "Replay digest mismatch")
    with closing(MPQArchive(path)) as arc:
        header = p.decode_replay_header(arc.header["user_data_header"]["content"])
        require(
            header["m_version"]["m_baseBuild"]
            == header["m_version"]["m_build"]
            == header["m_dataBuildNum"]
            == build,
            "Physical build mismatch",
        )
        details = p.decode_replay_details(arc.read_file("replay.details"))
        init = p.decode_replay_initdata(arc.read_file("replay.initData"))
        handles = details["m_cacheHandles"]
        require(
            handles and handles == init["m_syncLobbyState"]["m_gameDescription"]["m_cacheHandles"],
            "Cache handle mismatch",
        )
        require(
            handles[-1][:4] == b"s2ma"
            and handles[-1][8:].hex()
            == {
                41810: "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
                98348: "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
            }[build],
            "Dragon Shire map mismatch",
        )
        game = arc.read_file("replay.game.events")
        msg = arc.read_file("replay.message.events")
        tracker = arc.read_file("replay.tracker.events")
    life = defaultdict(list)
    bits = 0
    for e in p.decode_replay_tracker_events(tracker):
        bits += e["_bits"]
        if e["_eventid"] in (1, 2, 6, 12):
            key = e["m_unitTagIndex"], e["m_unitTagRecycle"]
            life[key].append((e["_gameloop"], e["_eventid"] != 2))
    require(bits == 8 * len(tracker), "Incomplete tracker")
    births = {key for key, rows in life.items() if any(alive for _, alive in rows)}
    bits = 0
    messages = defaultdict(list)
    for e in p.decode_replay_message_events(msg):
        bits += e["_bits"]
        if e["_event"].endswith(".SPingMessage"):
            messages[e["_userid"]["m_userId"]].append(
                (e["_gameloop"], e["m_point"]["x"], e["m_point"]["y"])
            )
    require(bits == 8 * len(msg), "Incomplete message stream")
    counts = Counter()
    options = Counter()
    by_alt = defaultdict(Counter)
    factors = [1, 16, 256, 4096]
    msg_counts = Counter()
    msg_ticks = defaultdict(list)
    for who, rows in messages.items():
        for when, x, y in rows:
            msg_ticks[who, when].append((x, y))
    shift = {41810: 18, 98348: 22}[build]
    xs, ys = [], []
    bits = 0
    for e in p.decode_replay_game_events(game):
        bits += e["_bits"]
        if e["_eventid"] != 36:
            continue
        require(e["_event"] == "NNet.Game.STriggerPingEvent", "Unexpected event binding")
        tag, tick = e["m_unit"], e["_gameloop"]
        x, y = e["m_point"]["x"], e["m_point"]["y"]
        who = e["_userid"]["m_userId"]
        xs.append(x)
        ys.append(y)
        counts["pings"] += 1
        counts["both_coords_nonzero"] += bool(x and y)
        for k in factors:
            counts[f"both_coords_divisible_{k}"] += x % k == y % k == 0
        flag = e["m_pingedMinimap"]
        category = "zero" if tag == 0 else ("allones" if tag == 2**32 - 1 else "tag")
        counts[category] += 1
        options[f"{category}/{e['m_option']}/{int(flag)}"] += 1
        same_time = msg_ticks.get((who, tick), [])
        msg_counts["same_user_same_loop_candidates"] += bool(same_time)
        msg_counts["same_user_same_loop_point_exact"] += (x, y) in same_time
        msg_counts["same_user_point_any_loop"] += any(
            (a, b) == (x, y) for _, a, b in messages.get(who, [])
        )
        if category != "tag":
            continue
        for s in range(1, 32):
            key = tag >> s, tag & ((1 << s) - 1)
            if key not in births:
                continue
            by_alt[s]["any_lifetime"] += 1
            if s == shift:
                rows = life[key]
                j = bisect_left(rows, (tick, False))
                if j < len(rows) and rows[j][0] == tick:
                    counts["birth_death_on_ping_tick"] += 1
                elif j and rows[j - 1][1]:
                    counts["visibly_live"] += 1
                else:
                    counts["not_visibly_live"] += 1
    require(bits == 8 * len(game), "Incomplete game member")
    return dict(
        sha256=digest,
        build=build,
        counts=counts,
        options=options,
        shift_matches={s: c["any_lifetime"] for s, c in by_alt.items()},
        point_ranges=([min(xs), max(xs), min(ys), max(ys)] if xs else []),
        message_crosscheck=msg_counts,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case", nargs="+")
    args = ap.parse_args()
    if len(args.case) % 3:
        ap.error("Supply PATH SHA256 BUILD triples")
    with ProcessPoolExecutor(max_workers=4) as ps:
        out = list(ps.map(measure, zip(*[iter(args.case)] * 3)))
    print(json.dumps(out, indent=2))
