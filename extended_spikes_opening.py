"""Reconstruct the continuous tracker opening through Anub'arak's first historical award."""

import argparse
from contextlib import closing
from hashlib import sha256
from itertools import islice
import json
from pathlib import Path

from build_extended_spikes_map import HERO, PARENT, TALENTS
from camp_owner_wire import read_tracker
from encoders import encode_tracker_events
from first_sync_game import game
from initial_talent_tracker import history, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from verify_extended_spikes_choice import CANDIDATE, effective


def check(value, why):
    if not value:
        raise ValueError(why)


def digest(raw):
    return sha256(raw).hexdigest()


def map_delta(parent, candidate):
    check(
        digest(parent.read_bytes()) == PARENT
        and digest(candidate.read_bytes()) == CANDIDATE,
        "Map mismatch",
    )
    with closing(MPQArchive(parent)) as a, closing(MPQArchive(candidate)) as b:
        names = set(read_member(a, "(listfile)").decode("ascii").splitlines())
        other = set(read_member(b, "(listfile)").decode("ascii").splitlines())
        check(
            len(names) == 70 and other == names | {HERO} and HERO not in names,
            "Map member inventory differs",
        )
        check(
            {k for k in names if read_member(a, k) != read_member(b, k)} == {TALENTS},
            "Unexpected map changes",
        )


def generate(source, parent, candidate, prefix, anub, game_library):
    map_delta(parent, candidate)
    talent, _ = effective(candidate, anub, game_library)
    src, commands = game(source, SOURCE, 41810)
    command = next(islice(src.decode_replay_game_events(commands), 491, None))
    check(
        (command["_eventid"], command["m_index"], command["_gameloop"])
        == (110, 0, 102),
        "Original selection changed",
    )
    data = prefix.read_bytes()
    check(
        digest(data)
        == "3c9ebfc479e391ea81746953ace5285f0253be514f0a7671d51dc1f5423bc4af",
        "Wrong pre-award opening",
    )
    target = target_protocol()
    rows = list(target.decode_replay_tracker_events(data))
    setup, heroes, levels = history(rows)
    _, player = setup[command["_userid"]["m_userId"]]
    check(
        player == 2
        and heroes[player][1] == "HeroAnubarak"
        and levels[player]
        and levels[player][-1][1] == 1,
        "Unbound opening award player or tier",
    )
    check(
        len(rows) == 266 and rows[-1]["_gameloop"] == 87,
        "Unexpected prior tracker boundary",
    )
    row = stat(command["_gameloop"] + 1, player, talent)
    addition = encode_tracker_events(
        [{**row, "_gameloop": row["_gameloop"] - rows[-1]["_gameloop"]}], target
    )
    old_protocol, old, _ = read_tracker(source, 41810)
    before = offset = 0
    seen = 0
    next_loop = next_kind = None
    for ordinal, e in enumerate(old_protocol.decode_replay_tracker_events(old)):
        n, partial = divmod(e.pop("_bits"), 8)
        check(n and not partial, "Unaligned source frame")
        if rows[-1]["_gameloop"] < e["_gameloop"] <= row["_gameloop"]:
            check(
                e == row
                and ordinal == 244
                and before == rows[-1]["_gameloop"]
                and old[offset : offset + n] == addition,
                "Physical award or contiguous insertion differs",
            )
            seen += 1
        if e["_gameloop"] > row["_gameloop"]:
            next_loop = e["_gameloop"]
            next_kind = e.get("m_eventName", b"").decode()
            break
        before, offset = e["_gameloop"], offset + n
    check(seen == 1 and next_loop == 134, "Unexpected next physical tracker record")
    wire = data + addition
    decoded = list(target.decode_replay_tracker_events(wire))
    check(
        len(decoded) == 267
        and sum(e["_bits"] for e in decoded) == len(wire) * 8
        and {k: v for k, v in decoded[-1].items() if k != "_bits"} == row
        and encode_tracker_events(decoded, target) == wire,
        "New target prefix readback differs",
    )
    return wire, dict(
        map_sha256=CANDIDATE,
        parent_map_sha256=PARENT,
        unchanged_map_content_members=69,
        parent_tracker_bytes=len(data),
        parent_tracker_sha256=digest(data),
        added_tracker_frames=1,
        source_command_ordinal=491,
        source_tracker_ordinal=244,
        translated_selector=0,
        award=talent,
        last_tracker_loop=row["_gameloop"],
        next_source_tracker_loop=next_loop,
        next_source_tracker_event=next_kind,
        frames=len(decoded),
        bytes=len(wire),
        sha256=digest(wire),
        verified_target_syncs=0,
        target_catalog_applied_at_runtime=False,
        historical_spell_geometry_verified=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "parent", "candidate", "prefix", "anub", "game_library"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("--private-output", type=Path)
    args = vars(cli.parse_args())
    output = args.pop("private_output")
    data, report = generate(**args)
    if output:
        with output.open("xb") as dest:
            dest.write(data)
    print(json.dumps(report, indent=2))
