"""Reproduce the TEN camera fragment and the 15 original-build 98348 Dragon Shire comparisons."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

import first_sync_game
from full_camera_inputs import SOURCE, audit, frame_rows
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from smartcam_tags import R8


def control(case):
    path, digest, stock_map = case
    _, report, _, pairs = audit(path,digest,98348,stock_map)
    return report,pairs


def compare_r8(source, candidate):
    if sha256(candidate.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected original partial R8 archive")
    old, raw_source = first_sync_game.game(source, SOURCE, 41810)
    target = target_protocol()
    with closing(MPQArchive(candidate)) as archive:
        header = target.decode_replay_header(archive.header["user_data_header"]["content"])
        if (header["m_version"]["m_build"],header["m_version"]["m_baseBuild"],header["m_dataBuildNum"]) != (98285,)*3:
            raise ValueError("Unexpected partial R8 build")
        raw_r8 = archive.read_file("replay.game.events")
    count = 0
    for a,b in zip(frame_rows(old,raw_source),frame_rows(target,raw_r8),strict=True):
        if a != b:
            raise ValueError("R8 camera ordinal, preceding loop, fields or physical bytes differ")
        count += 1
    return dict(replay_sha256=R8, build=98285, identical_physical_enclosing_frames=count)


def verify(source, gate_map, stock_map, paths, jobs):
    pins_path = Path(first_sync_game.__file__).resolve().parent / "observations" / "unit-generation-evidence.json"
    pins = sorted(row["sha256"] for row in json.loads(pins_path.read_bytes())["cases"] if row["build"]==98348)
    if len(set(pins)) != 15 or len(pins) != 15 or not set(pins).issubset(paths):
        raise ValueError("Missing one of the 15 pinned Dragon Shire controls")
    cases = [(Path(paths[h]), h, stock_map) for h in pins]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        controls = list(pool.map(control,cases))
    _,old,_,oldpairs = audit(source,SOURCE,41810,gate_map)
    modern = [r for r, _ in controls]
    shapes = sum((Counter(r["shapes"]) for r in modern),Counter())
    missing = sorted(old["shapes"].keys()-shapes.keys())
    amount = sum(r["frames"] for r in modern)
    physical_bytes = sum(r["enclosing_bytes"] for r in modern)
    if (amount, physical_bytes, missing) != (406717,3252218,[]):
        raise ValueError("Reference event, byte or optional-field coverage changed")
    return dict(source=old,controls=modern,control_camera_events=amount,control_physical_bytes=physical_bytes,
                control_startpoint_hits=sum(r["exact_startpoint_hits"] for r in modern),
                control_shapes=dict(sorted(shapes.items())),source_shapes_without_target_witness=missing,
                historical_distance_pitch_pairs=len(oldpairs),
                historical_pairs_exactly_observed_modern=len(oldpairs & set().union(*(p for _,p in controls))),
                rendered_camera_or_follow_semantics_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source","gate_map","stock_map","control_manifest"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--jobs",type=int,default=2,choices=range(1,5))
    cli.add_argument("--retained-r8",type=Path)
    args = cli.parse_args()
    result = verify(args.source,args.gate_map,args.stock_map,json.loads(args.control_manifest.read_bytes()),args.jobs)
    if args.retained_r8:
        result["original_partial_r8"] = compare_r8(args.source,args.retained_r8)
    print(json.dumps(result,indent=2))
