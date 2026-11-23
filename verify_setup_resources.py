"""Compare native-layout and named setup serialization on the 24 pinned 98348 controls."""

import argparse
from collections import Counter
import json
from pathlib import Path

import first_sync_game
from setup_resource_crc import project, setup_crc, template


def check(cases):
    expected = Path(first_sync_game.__file__).resolve().parent / "observations" / "first-sync-game.json"
    pins = {r["replay_sha256"] for r in json.loads(expected.read_bytes())["references"]}
    if len(pins) != 24 or set(cases) != pins:
        raise ValueError("Expected the complete pinned 98348 cohort")
    counts = Counter()
    checksums = set()
    rows = []
    for digest, name in sorted(cases.items()):
        p, named, root, r = template(Path(name), digest, 98348)
        d = named["m_syncLobbyState"]["m_gameDescription"]
        data = project(p, named, root, d["m_cacheHandles"], d["m_mapFileSyncChecksum"], d["m_modFileSyncChecksum"])
        if hex(setup_crc(data)) != r["canonical_setup_crc"] or len(data) != r["bytes"]:
            raise ValueError("Rebuilding the three supplied fields changes the canonical setup")
        counts["controls"] += 1
        counts["bytes"] += r["bytes"]
        counts["canonical_byte_matches"] += r["canonical_bytes_equal_recorded"]
        checksums.add(r["canonical_setup_crc"])
        rows.append(dict(replay_sha256=digest, **r))
    return dict(**counts, distinct_serialization_crcs=len(checksums), records=rows, observed_runtime_crc=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("manifest", type=Path, help="Local JSON mapping pinned replay SHA-256 values to local files")
    args = cli.parse_args()
    print(json.dumps(check(json.loads(args.manifest.read_bytes())), indent=2))
