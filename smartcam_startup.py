"""Project camera endpoints belonging to map-authored units during their first source lifetime."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from map_startup_identity import match_startup, parse_objects
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from plan_authored_targets import join_layouts
from project_rank_targets import lifetime_ends
from smartcam_tags import decode, read_case, components, pack, MAP, SOURCE, TARGET_MAP

PROFILE = {
    MAP: 41810,
    "662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800": 41810,
    TARGET_MAP: 98348,
    "2de7e30ecf97cb975f483e8dc33ec05035d5b42d1e45a9a011dfecb4984b1632": 98348,
}


def layout(path):
    digest = sha256(path.read_bytes()).hexdigest()
    if digest not in PROFILE:
        raise ValueError("Unknown Dragon Shire package")
    with closing(MPQArchive(path)) as arc:
        return digest, parse_objects(read_member(arc, "Objects"))


def project(replay, original_map, target_map):
    digest, original = layout(original_map)
    if digest != MAP:
        raise ValueError("Expected original 41810 map")
    target_sha, target = layout(target_map)
    smart, t, _, h, _ = read_case(replay, SOURCE, 41810)
    rows = decode(smart, h)
    source_anchors, evidence = match_startup(original, t)
    if evidence["verified"] != len(original):
        raise ValueError("Incomplete source-map identity check")
    ids = {(r.index, r.recycle) for r in source_anchors}
    ends = lifetime_ends(t, ids)
    shared = join_layouts(original, target)
    accepted = []
    reasons = Counter()
    for n, (_, tick, *tags) in enumerate(rows):
        for side, word in enumerate(tags):
            key = components(word, 18)
            if key not in ids:
                reasons["outside_authored_startup"] += 1
                continue
            if not 0 < tick < ends.get(key, float("inf")):
                reasons["outside_source_first_lifetime"] += 1
                continue
            if key[0] not in shared:
                reasons["no_unique_map_correspondence"] += 1
                continue
            source_object = original[key[0]]
            target_index = shared[key[0]]
            accepted.append(
                dict(
                    ordinal=n,
                    field=side,
                    member_byte_offset=n * 13 + 5 + 4 * side,
                    loop=tick,
                    object_id=source_object.object_id,
                    unit_type=source_object.unit_type,
                    target_packed_value=pack(target_index, 1, 22),
                )
            )
    if len(accepted) + sum(reasons.values()) != 2 * len(rows):
        raise ValueError("Field accounting")
    return dict(
        source_sha256=SOURCE,
        source_map_sha256=digest,
        target_map_sha256=target_sha,
        fields=2 * len(rows),
        projected_initial_fields=len(accepted),
        withheld=dict(reasons),
        projections=accepted,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--original-map", type=Path, required=True)
    p.add_argument("--target-map", type=Path, required=True)
    a = p.parse_args()
    print(
        json.dumps(
            project(a.source, a.original_map, a.target_map), indent=2, sort_keys=True
        )
    )
