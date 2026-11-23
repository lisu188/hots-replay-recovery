"""Count opening births for four named heroes in other build-98348 maps."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol

HEROES = (b"Abathur", b"Kaelthas", b"Nova", b"Tyrande")
DRAGON_SHIRE = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"


def audit(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Replay digest differs")
    p = load_protocol(96477)
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        v = h["m_version"]
        if (v["m_build"], v["m_baseBuild"], h["m_dataBuildNum"]) != (98348,) * 3:
            raise ValueError("Replay version differs")
        details = p.decode_replay_details(a.read_file("replay.details"))
        lobby = p.decode_replay_initdata(a.read_file("replay.initData"))[
            "m_syncLobbyState"
        ]
        handles = details["m_cacheHandles"]
        if (
            not handles
            or handles != lobby["m_gameDescription"]["m_cacheHandles"]
            or handles[-1][:4] != b"s2ma"
        ):
            raise ValueError("Replay map differs")
        map_sha = handles[-1][8:].hex()
        if map_sha == DRAGON_SHIRE:
            raise ValueError("Requires a non-Dragon-Shire control")
        slots = lobby["m_lobbyState"]["m_slots"]
        roster = {
            i: s["m_hero"] for i, s in enumerate(slots, 1) if s.get("m_hero") in HEROES
        }
        raw = a.read_file("replay.tracker.events")
    window = []
    bits = 0
    for e in p.decode_replay_tracker_events(raw):
        bits += e["_bits"]
        if e["_eventid"] in (1, 6) and 0 < e["_gameloop"] < 118:
            window.append(
                (
                    e["_gameloop"],
                    e["m_controlPlayerId"],
                    e["m_unitTypeName"],
                    e["_eventid"],
                )
            )
    if bits != len(raw) * 8:
        raise ValueError("Incomplete physical tracker")
    counts = {}
    for owner, hero in roster.items():
        exact = [
            tick
            for tick, o, kind, idx in window
            if tick < 110 and o == owner and kind == b"Hero" + hero and idx == 1
        ]
        score = counts.setdefault(hero.decode(), Counter())
        score["roster_entries"] += 1
        if len(exact) == 1:
            score["unique_births"] += 1
            tick = exact[0]
            score["additional_owned_births_in_eight_loops"] += (
                sum(
                    1
                    for t, o, kind, idx in window
                    if tick <= t < tick + 8 and o == owner
                )
                - 1
            )
    return dict(sha256=digest, map_handle=map_sha, heroes=counts)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "--case", nargs=2, action="append", required=True, metavar=("REPLAY", "SHA")
    )
    cases = [audit(Path(p), h) for p, h in cli.parse_args().case]
    if len({r["sha256"] for r in cases}) != len(cases):
        raise ValueError("Duplicate control")
    print(json.dumps(sorted(cases, key=lambda r: r["sha256"]), indent=2))
