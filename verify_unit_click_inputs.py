"""Check the public click receipt and the original R8 archive against the generated TEN subset."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from first_sync_game import game
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from repair_unit_tags import components, pack
from smartcam_tags import R8
from unit_click_inputs import SOURCE, clicks, generate, reference_keys, validate_cohort


def r8_comparison(source, r8, generated):
    if sha256(r8.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected partial R8 archive")
    old, source_game = game(source, SOURCE, 41810)
    current = target_protocol()
    with closing(MPQArchive(r8)) as archive:
        h = current.decode_replay_header(archive.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (98285,) * 3:
            raise ValueError("Unexpected R8 header")
        retained = archive.read_file("replay.game.events")
    counts = Counter()
    for (ordinal, _, prior, _), (other_ordinal, _, existing, _) in zip(
        clicks(old, source_game), clicks(current, retained), strict=True
    ):
        counts["clicks"] += 1
        if (prior["_gameloop"], prior["_userid"]) != (existing["_gameloop"], existing["_userid"]):
            raise ValueError("R8 changes click time, user or click order")
        counts["same_full_game_ordinal"] += ordinal == other_ordinal
        existing_tag = existing["m_unitTag"]
        counts["matches_repacked_historical_pair"] += (
            pack(*components(prior["m_unitTag"], 18), 22) == existing_tag
        )
        if ordinal in generated:
            if generated[ordinal]["m_unitTag"] != existing_tag:
                raise ValueError("R8 differs from the independent GateOrder prediction")
            counts["matches_independent_projection"] += 1
    if (
        counts["clicks"] != 2756
        or counts["same_full_game_ordinal"] != counts["clicks"]
        or counts["matches_repacked_historical_pair"] != counts["clicks"]
        or counts["matches_independent_projection"] != len(generated)
    ):
        raise ValueError("R8 click coverage differs from original ordinals or independent projection")
    return dict(sha256=R8, build=98285, **counts)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "gate_map", "mechanics", "curve", "receipt", "reference_list", "retained_r8"):
        cli.add_argument(arg, type=Path)
    args = cli.parse_args()
    events, raw, actual = generate(args.source, args.gate_map, args.mechanics, args.curve)
    saved = json.loads(args.receipt.read_bytes())
    if any(saved.get(k) != v for k, v in actual.items()):
        raise ValueError("Source projection differs from receipt")
    controls = saved["controls"]
    frames, physical_bytes = validate_cohort(controls, reference_keys(args.reference_list))
    if (frames, physical_bytes) != (saved["target_physical_frames"], saved["target_physical_bytes"]):
        raise ValueError("Aggregate control receipt differs")
    summary = dict(
        r8=r8_comparison(args.source, args.retained_r8, events),
        references=len(controls),
        target_clicks=frames,
        target_physical_bytes=physical_bytes,
        first_source_game_ordinal=min(events),
        last_source_game_ordinal=max(events),
        sparse_sha256=sha256(raw).hexdigest(),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
