"""Measure what TEN recorded about Nova's first talent and her subsequent unit-target commands."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import hypot
from pathlib import Path

from encoders import encode_game_events
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from symbolic_command_starts import members


def measure(source):
    protocol, raw, _ = members(source, SOURCE, 41810)
    with closing(MPQArchive(source)) as file:
        tracker = file.read_file("replay.tracker.events")
        details_raw = file.read_file("replay.details")
        details = protocol.decode_replay_details(details_raw)
        utc = datetime(1601,1,1,tzinfo=timezone.utc) + timedelta(microseconds=details["m_timeUTC"]//10)
    named_stats = Counter()
    names = Counter()
    purchase_players = {}
    setup = {}
    hero_tags = set()
    birth_types = {}
    active = {}
    positions = defaultdict(list)
    for event in protocol.decode_replay_tracker_events(tracker):
        t = event["_gameloop"]
        k = event["_event"].split(".")[-1]
        names[k] += 1
        if k == "SPlayerSetupEvent":
            setup[event["m_playerId"]] = event["m_userId"]
        if k == "SUnitBornEvent":
            index = event["m_unitTagIndex"]
            tag = protocol.unit_tag(index, event["m_unitTagRecycle"])
            active[index] = tag
            birth_types[tag] = event["m_unitTypeName"].decode()
            if event["m_unitTypeName"].startswith(b"Hero"):
                hero_tags.add(tag)
        if k == "SUnitDiedEvent":
            active.pop(event["m_unitTagIndex"], None)
        if k == "SUnitRevivedEvent":
            index = event["m_unitTagIndex"]
            active[index] = protocol.unit_tag(index, event["m_unitTagRecycle"])
        if k == "SUnitPositionsEvent":
            index = event["m_firstUnitIndex"]
            a = event["m_items"]
            if len(a) % 3:
                raise ValueError("Tracker unit-position framing")
            for i in range(0, len(a), 3):
                index += a[i]
                if index in active:
                    positions[active[index]].append(t)
        if k == "SStatGameEvent":
            label = event["m_eventName"].decode()
            named_stats[label] += 1
            if label == "TalentChosen":
                strings = {r["m_key"]: r["m_value"] for r in event["m_stringData"]}
                integers = {r["m_key"]: r["m_value"] for r in event["m_intData"]}
                for item in (b"NovaMasteryCovertOpsPinningShot", b"NovaHeroicAbilityTripleTap"):
                    if item in strings.values():
                        purchase_players[item] = (t, integers[b"PlayerID"])
    first, player = purchase_players[b"NovaMasteryCovertOpsPinningShot"]
    heroic, heroic_player = purchase_players[b"NovaHeroicAbilityTripleTap"]
    if player != heroic_player:
        raise ValueError("Different purchasing players")
    rows = []
    snapshots = defaultdict(list)
    by_observer = defaultdict(lambda: defaultdict(set))
    owner_links = defaultdict(set)
    physical = offset = previous = 0
    purchase_wire = {}
    for n, event in enumerate(protocol.decode_replay_game_events(raw)):
        t = event["_gameloop"]
        k = event["_eventid"]
        u = event["_userid"]["m_userId"]
        size, rem = divmod(event["_bits"], 8)
        if rem or not size:
            raise ValueError("Unexpected game row boundary")
        if n in (844, 40579) and k == 110:
            purchase_wire[n] = (u, t)
        if k in (27, 105):
            target = event["m_target"] if k == 105 else event["m_data"].get("TargetUnit")
            if target:
                snapshots[target["m_tag"]].append(t)
                point = target["m_snapshotPoint"]
                by_observer[target["m_tag"], u][t].add((point["x"], point["y"]))
            if k == 27 and event["m_abil"]:
                link = event["m_abil"]["m_abilLink"]
                owner_links[link].add(u)
                if u == setup[player] and t >= first:
                    bytes_in_file = raw[offset:offset + size]
                    rebuilt = encode_game_events([{**event, "_gameloop": t - previous}], protocol)
                    if rebuilt != bytes_in_file:
                        raise ValueError("Nova source issue re-encoding mismatch")
                    physical += size
                    form = next(iter(event["m_data"]))
                    rows.append((t, link, form, target["m_tag"] if target else None))
        previous = t
        offset += size
    if offset != len(raw) or purchase_wire != {844: (setup[player], first-1), 40579: (setup[player], heroic-1)}:
        raise ValueError("TEN purchase gamer association")
    links = {}
    for link in sorted({x[1] for x in rows}):
        subset = [x for x in rows if x[1] == link]
        units = [x for x in subset if x[3] is not None]
        def sample(counts, row):
            t, _, _, tag = row
            return len({loop for loop in counts[tag] if t < loop <= t + 36})
        links[link] = dict(users_with_link=len(owner_links[link]),
            targets=dict(Counter(x[2] for x in subset)),
            before_heroic=dict(Counter(x[2] for x in subset if x[0] < heroic)),
            unit_target_hero_births=sum(x[3] in hero_tags for x in units),
            units_with_two_subsequent_physical_snapshot_loops_within_36=sum(sample(snapshots,x) >= 2 for x in units),
            units_with_two_subsequent_tracker_position_loops_within_36=sum(sample(positions,x) >= 2 for x in units),
            unit_issue_loops=[x[0] for x in units] if len(units) <= 90 else None)
    displacement = []
    for issue, link, _, tag in rows:
        if link != 378:
            continue
        sides = {}
        for name, start, end in (("before", issue-36, issue-1), ("after", issue+1, issue+36)):
            chords = []
            for (actor, viewer), ticks in by_observer.items():
                if actor != tag:
                    continue
                seen = sorted(t for t in ticks if start <= t <= end)
                for a, b in zip(seen, seen[1:]):
                    if len(ticks[a]) != 1 or len(ticks[b]) != 1:
                        continue
                    (x1, y1), = ticks[a]
                    (x2, y2), = ticks[b]
                    # Report integer differences and observer-local span; no velocity assumed.
                    chords.append((a-issue, b-a, x2-x1, y2-y1))
            moving = [round(hypot(dx, dy) / dt * 16 / 4096, 3) for _, dt, dx, dy in chords if dx or dy]
            sides[name] = dict(comparable_pairs=len(chords), stationary=sum(dx==dy==0 for _,dt,dx,dy in chords),
                nonzero_chord_rate_range=[min(moving),max(moving)] if moving else None,
                distinct_loop_spans=sorted({dt for _,dt,dx,dy in chords}))
            if issue == 8412:
                sides[name]["distinct_physical_chords"] = sorted(set(chords))
        displacement.append(dict(issue_loop=issue, target_hero_born=tag in hero_tags,
            tracker_birth_type=birth_types.get(tag), **sides))
    # Use the very same tagged life and deduplicate repetitions by different observers.
    focal_tag, = {tag for t,link,_,tag in rows if t == 8412 and link == 378}
    windows = [t for t,link,_,tag in rows if tag == focal_tag and link == 378]
    pairs = set()
    for (tag, _), ticks in by_observer.items():
        if tag != focal_tag:
            continue
        for t in ticks:
            if t + 1 not in ticks or len(ticks[t]) != 1 or len(ticks[t+1]) != 1:
                continue
            (a,b), = ticks[t]
            (c,d), = ticks[t+1]
            pairs.add((t,c-a,d-b))
    bands = defaultdict(Counter)
    for t,x,y in pairs:
        v = hypot(x,y) / 256
        key = "post_378" if any(start < t and t+1 <= start+36 for start in windows) else "elsewhere"
        bands[key]["distinct_one_loop_chords"] += 1
        bands[key]["stationary"] += x == y == 0
        bands[key]["within_0_02_of_4_4"] += abs(v-4.4) <= 0.02
        bands[key]["within_0_02_of_1_76"] += abs(v-1.76) <= 0.02
    return dict(source_sha256=SOURCE, game_member_sha256=sha256(raw).hexdigest(),
        details_member_sha256=sha256(details_raw).hexdigest(), recorded_utc_date=utc.date().isoformat(),
        tracker_member_sha256=sha256(tracker).hexdigest(), purchase_selection_loop=133,
        purchase_tracker_loop=first, heroic_purchase_selection_loop=heroic-1, heroic_purchase_tracker_loop=heroic,
        complete_nova_explicit_issue_bytes=physical, named_stat_counts=named_stats, tracker_event_kinds=names,
        explicit_ability_links=links, link378_observed_snapshot_chords=displacement,
        tyrande_same_tag_one_loop_chords=bands)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    print(json.dumps(measure(cli.parse_args().source), indent=2))
