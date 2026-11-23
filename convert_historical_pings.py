"""Emit target-format ping inputs on the preserved Dragon Shire layout."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

import native_game_events as native
from camp_owner_wire import TARGET_SCHEMA_SHA
from dragonshire_packages import historical_package_digest
from map_startup_identity import match_startup, parse_objects
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
import os
from plan_authored_targets import join_layouts
from predict_camp_captures import MAP, SOURCE
from project_rank_targets import lifetime_ends
from protocol_loader import load_protocol
from repair_unit_tags import components, pack
from tempfile import TemporaryDirectory

PING = 36
FIELDS = ("m_point", "m_unit", "m_pingedMinimap", "m_option")
R8 = "4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19"


def pinned(path, expected):
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Unexpected input digest")


def placements(path, digest):
    pinned(path, digest)
    with closing(MPQArchive(path)) as arc:
        return parse_objects(read_member(arc, "Objects"))


def target_protocol():
    p = load_protocol(96477)
    tid, name = p.game_event_types[PING]
    if (
        p.recovery_schema_sha256 != TARGET_SCHEMA_SHA
        or name != "NNet.Game.STriggerPingEvent"
        or tuple(x[0] for x in p.typeinfos[tid][1][0]) != FIELDS
    ):
        raise ValueError("Unexpected named ping schema")
    return p


def native_frame(e, tag, delta):
    point = e["m_point"]
    payload = ((point["x"], point["y"]), tag, e["m_pingedMinimap"], e["m_option"])
    return native.GameEvent(delta, e["_userid"]["m_userId"], PING, payload)


def target_for(tag, loop, anchors, ends):
    if tag == 0:
        return 0, "no_explicit_unit"
    key = components(tag, 18)
    if key not in anchors:
        return None, "unresolved_instance"
    if not 0 < loop < ends.get(key, float("inf")):
        return None, "outside_initial_lifetime"
    return pack(anchors[key], 1, 22), "original_layout_placement"


def generate(source, original_map, historical_map):
    pinned(source, SOURCE)
    original = placements(original_map, MAP)
    historical_digest = historical_package_digest(historical_map)
    dest = placements(historical_map, historical_digest)
    if original != dest:
        raise ValueError("Historical package changes authored placements")
    cross = join_layouts(original, dest)
    sp = load_protocol(41810)
    tp = target_protocol()
    with closing(MPQArchive(source)) as arc:
        tracker = list(sp.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
        game = arc.read_file("replay.game.events")
    verified, report = match_startup(original, tracker)
    if report["verified"] != len(original):
        raise ValueError("Incomplete source placement verification")
    anchors = {(a.index, a.recycle): cross[a.index] for a in verified if a.index in cross}
    ends = lifetime_ends(tracker, anchors)
    frames = []
    expected = []
    counts = Counter()
    last = 0
    for e in sp.decode_replay_game_events(game):
        if e["_eventid"] != PING:
            continue
        loop = e["_gameloop"]
        tag, reason = target_for(e["m_unit"], loop, anchors, ends)
        counts[reason] += 1
        if tag is None:
            continue
        frames.append(native_frame(e, tag, loop - last))
        expected.append(
            (
                loop,
                e["_userid"]["m_userId"],
                e["m_point"],
                tag,
                e["m_pingedMinimap"],
                e["m_option"],
            )
        )
        last = loop
    raw = native.encode_game_events(frames)
    decoded = list(tp.decode_replay_game_events(raw))
    actual = [(e["_gameloop"], e["_userid"]["m_userId"], *(e[k] for k in FIELDS)) for e in decoded]
    if actual != expected or sum(e["_bits"] for e in decoded) != 8 * len(raw):
        raise ValueError("Target named reader disagrees with the native ping writer")
    return raw, dict(
        bytes=len(raw),
        sha256=sha256(raw).hexdigest(),
        counts=dict(counts),
        total_source=sum(counts.values()),
        emitted=len(decoded),
        source_sha256=SOURCE,
        original_map_sha256=MAP,
        target_layout_sha256=historical_digest,
        native_profile_sha256=native.SCHEMA_SHA256,
    )


def verify_control(path, digest):
    pinned(path, digest)
    p = target_protocol()
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        v = h["m_version"]
        if (v["m_build"], v["m_baseBuild"], h["m_dataBuildNum"]) != (98348,) * 3:
            raise ValueError("Expected a genuine 98348 recording")
        raw = arc.read_file("replay.game.events")
    start = prior = count = total_bytes = 0
    for e in p.decode_replay_game_events(raw):
        bits = e["_bits"]
        if bits % 8:
            raise ValueError("Unaligned game frame")
        stop = start + bits // 8
        loop = e["_gameloop"]
        if e["_eventid"] == PING:
            frame = native_frame(e, e["m_unit"], loop - prior)
            encoded = native.encode_game_events([frame])
            if raw[start:stop] != encoded:
                raise ValueError("Encoded ping differs from its physical frame")
            total_bytes += len(encoded)
            count += 1
        start, prior = stop, loop
    if start != len(raw):
        raise ValueError("Incomplete member traversal")
    return dict(
        replay_sha256=digest,
        full_member_bytes_scanned=start,
        physical_ping_frames=count,
        physical_ping_bytes=total_bytes,
    )


def compare_r8(source, r8):
    rows = []
    for path, digest, schema in ((source, SOURCE, 41810), (r8, R8, 96477)):
        pinned(path, digest)
        p = load_protocol(schema)
        with closing(MPQArchive(path)) as arc:
            rows.append(
                [
                    (e["_gameloop"], e["_userid"]["m_userId"], *(e[k] for k in FIELDS))
                    for e in p.decode_replay_game_events(arc.read_file("replay.game.events"))
                    if e["_eventid"] == PING
                ]
            )
            if digest == R8:
                pairs = {
                    (e["m_unitTagIndex"], e["m_unitTagRecycle"])
                    for e in p.decode_replay_tracker_events(arc.read_file("replay.tracker.events"))
                    if "m_unitTagIndex" in e and "m_unitTagRecycle" in e
                }
    if rows[0] != rows[1]:
        raise ValueError("Source and preserved R8 ping records differ")
    units = [row[3] for row in rows[0] if row[3]]
    if not all(components(tag, 18) in pairs for tag in units):
        raise ValueError("Historical ping tag missing from retained tracker")
    return dict(
        source=SOURCE,
        r8=R8,
        unchanged_ping_records=len(rows[0]),
        explicit_unit_records=len(units),
        changed_identities_at_shift22=sum(components(t, 18) != components(t, 22) for t in units),
        incidental_tracker_matches_at_shift22=sum(components(t, 22) in pairs for t in units),
    )


def generate_for_retained_tracker(source, r8):
    """Encode all pings relative to the partial R8 tracker's recorded unit generations."""
    from smartcam_tags import match_tracker_identities

    pinned(source, SOURCE)
    pinned(r8, R8)
    old = load_protocol(41810)
    target = target_protocol()
    with closing(MPQArchive(source)) as arc:
        game = arc.read_file("replay.game.events")
        source_tracker = arc.read_file("replay.tracker.events")
    with closing(MPQArchive(r8)) as arc:
        retained_tracker = arc.read_file("replay.tracker.events")
    if retained_tracker != source_tracker:
        raise ValueError("Unexpected change in the R8 tracker")
    events = [e for e in old.decode_replay_game_events(game) if e["_eventid"] == PING]
    keys = {components(e["m_unit"], 18) for e in events if e["m_unit"]}
    matches = match_tracker_identities(
        keys,
        list(old.decode_replay_tracker_events(source_tracker)),
        list(target.decode_replay_tracker_events(retained_tracker)),
    )
    frames = []
    reverse = {pack(*value, 22): pack(*key, 18) for key, value in matches.items()}
    reverse[0] = 0
    last = 0
    for e in events:
        value = e["m_unit"]
        tag = pack(*matches[components(value, 18)], 22) if value else 0
        frames.append(native_frame(e, tag, e["_gameloop"] - last))
        last = e["_gameloop"]
    raw = native.encode_game_events(frames)
    observed = list(target.decode_replay_game_events(raw))
    for expected, actual in zip(events, observed, strict=True):
        if (
            actual["_eventid"] != PING
            or reverse[actual["m_unit"]] != expected["m_unit"]
            or any(
                expected[k] != actual[k]
                for k in ("_gameloop", "_userid", "m_point", "m_option", "m_pingedMinimap")
            )
        ):
            raise ValueError("Inverse ping comparison failed")
    if sum(e["_bits"] for e in observed) != 8 * len(raw):
        raise ValueError("Trailing bytes in ping stream")
    return raw, dict(
        source_sha256=SOURCE,
        tracker_sha256=sha256(retained_tracker).hexdigest(),
        recorded_reference_sha256=R8,
        events=len(events),
        unique_unit_identities=len(matches),
        nonzero_unit_fields=sum(bool(e["m_unit"]) for e in events),
        sha256=sha256(raw).hexdigest(),
        bytes=len(raw),
        full_inverse_equal=True,
        destination_simulation_allocation_verified=False,
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    subs = cli.add_subparsers(dest="action", required=True)
    maker = subs.add_parser("generate")
    for key in ("source", "original-map", "historical-map", "output"):
        maker.add_argument("--" + key, type=Path, required=True)
    check = subs.add_parser("verify-control")
    check.add_argument("replay", type=Path)
    check.add_argument("--sha256", required=True)
    regression = subs.add_parser("compare-r8")
    regression.add_argument("original", type=Path)
    regression.add_argument("r8", type=Path)
    retained = subs.add_parser("retained-tracker")
    retained.add_argument("original", type=Path)
    retained.add_argument("r8", type=Path)
    retained.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    if args.action in ("generate", "retained-tracker"):
        if args.action == "generate":
            raw, result = generate(args.source, args.original_map, args.historical_map)
        else:
            raw, result = generate_for_retained_tracker(args.original, args.r8)
        with TemporaryDirectory(dir=args.output.parent) as tmp:
            staged = Path(tmp) / "pings.bin"
            staged.write_bytes(raw)
            if os.name == "nt":
                os.rename(staged, args.output)  # On Windows an existing destination is rejected.
            else:
                os.link(staged, args.output)
    elif args.action == "compare-r8":
        result = compare_r8(args.original, args.r8)
    else:
        result = verify_control(args.replay, args.sha256)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
