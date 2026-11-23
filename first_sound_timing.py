"""Verify recipient-specific opening offsets against the pinned five legacy and 24 modern replays."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import json

from first_sync_game import game
from mpq_reader import MPQArchive
from opening_sound_roles import COMMON, STOCK, leave_one_out, role_order
from predict_camp_captures import SOURCE

COHORT = "92d7296d30269683992887bcc9a202ae20800ef8c0715ac8c239bd0704cb8773"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def verify_manifest(cases):
    pairs = sorted((build, digest) for _, digest, build in cases)
    raw = json.dumps(pairs, separators=(",", ":")).encode("ascii")
    require(sha256(raw).hexdigest() == COHORT, "Expected the exact 29 build/digest pairs")
    return cases


def score(path, digest, build):
    protocol, raw = game(path, digest, build)
    with closing(MPQArchive(path)) as archive:
        tracker = list(protocol.decode_replay_tracker_events(archive.read_file("replay.tracker.events")))
        init = protocol.decode_replay_initdata(archive.read_file("replay.initData"))
        slots = init["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
    map_digest = details["m_cacheHandles"][-1][8:].hex()
    packs = {s["m_userId"]: s.get("m_announcerPack") for s in slots if s["m_control"] == 2}
    setup = {r["m_userId"]: r["m_playerId"] for r in tracker
             if r["_gameloop"] == 0 and r["_eventid"] == 9 and r["m_userId"] is not None}
    require(len(set(setup.values())) == len(setup), "Duplicate setup players")
    gate, = [r["_gameloop"] for r in tracker if r.get("m_eventName") == b"GatesOpen"]
    reports = defaultdict(list)
    first = None
    previous = 0
    for ordinal, event in enumerate(protocol.decode_replay_game_events(raw)):
        tick = event["_gameloop"]
        if tick > gate + 1024:
            break
        if event["_eventid"] == 46:
            uid = event["_userid"]["m_userId"]
            row = (ordinal, tick, tick-previous, event["m_sound"])
            reports[setup[uid]].append(row)
            if first is None:
                first = (uid, *row)
        previous = tick
    words = {p: [e[3] for e in rows[:10]] for p, rows in reports.items()}
    closed = len(words) == 10 and all(len(values) == 10 for values in words.values())
    hits, roles = leave_one_out(words, role_order(build)) if closed else (0, None)
    result = dict(sha256=digest, build=build, map_sha256=map_digest, gate_loop=gate, threshold_loop=gate-34*16,
                  first_loop=first[2] if first else None, first_minus_gate_threshold=first[2]-gate+34*16 if first else None,
                  closed=hits==10)
    if hits != 10:
        return result
    require(set(setup.values()) == set(range(1,11)) and len(setup) == 10, "Unexpected closed-group setup")
    lags, recipients = [], []
    for uid, player in sorted(setup.items()):
        rows = reports[player]
        initial = rows[:10]
        own = next((r for r in rows[10:] if r[3] == roles[player]), None)
        require(all(r[3] != roles[player] for r in initial), "Included own role in first batch")
        lag = own[1] - initial[-1][1] if own else None
        if lag is not None:
            lags.append(lag)
        pack = packs.get(uid)
        record = dict(player=player, first_loop=initial[0][1], initial_last_loop=initial[-1][1],
                      own_first_loop=own[1] if own else None, lag=lag,
                      map_default_or_explicit_lady=pack in (b"NoAnnouncerPack", b"LadyofThorns"))
        if digest == SOURCE:
            record.update(own_word=roles[player], initial_ordinals=[r[0] for r in initial], first_raw_delta=initial[0][2])
        recipients.append(record)
    result.update(own_found=len(lags), own_strictly_later=sum(lag>0 for lag in lags), observed_lags=lags)
    if map_digest == STOCK:
        result["default_or_lady_lags"] = [r["lag"] for r in recipients if r["map_default_or_explicit_lady"]]
    if digest == SOURCE:
        result.update(ten_player_batches=recipients, common_original_word=roles[COMMON], first_source_frame=first)
    return result


def report(cases):
    rows = [score(Path(path), digest, build) for path, digest, build in verify_manifest(cases)]
    rows.sort(key=lambda r:(r["build"],r["sha256"]))
    totals = {}
    for build in (41810,98348):
        at = [r for r in rows if r["build"] == build]
        closed = [r for r in at if r["closed"]]
        lags = [v for r in closed for v in r["observed_lags"]]
        by_default = [v for r in closed for v in r.get("default_or_lady_lags", []) if v is not None]
        totals[build] = dict(cases=len(at), closed=len(closed), own_found=len(lags), eligible=len(closed)*10,
                             later_than_full_initial_batch=sum(v>0 for v in lags), observed_lag_range=[min(lags),max(lags)],
                             absent_through_gate_plus_1024=sum(r["first_loop"] is None for r in at),
                             first_minus_threshold=dict(sorted(Counter(r["first_minus_gate_threshold"] for r in at
                                                                       if r["first_loop"] is not None).items())),
                             stock_map_NoAnnouncerPack_or_LadyofThorns_lags=dict(sorted(Counter(by_default).items())))
    return dict(cohort_digest=COHORT, totals=totals, cases=rows)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    doc = json.loads(parser.parse_args().manifest.read_bytes())
    print(json.dumps(report(doc), indent=2))
