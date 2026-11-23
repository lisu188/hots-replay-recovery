"""Apply the frozen stock Dragon Shire predictor to disjoint, hash-pinned 98348 recordings."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from check_blind_target_tags import test
from project_rank_targets import ANCHORS, ROSTER, MPQArchive, pinned, protocol96477, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("anchors", "roster", "selection", "control-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(pinned(args.anchors, ANCHORS))
    used = {r["replay_sha256"] for r in json.loads(pinned(args.roster, ROSTER))["references"]}
    selection = json.loads(args.selection.read_bytes())
    if isinstance(selection, dict):
        chosen = [
            dict(
                sha256=r["replay_sha256"],
                bytes=r["replay_bytes"],
                date=r["date"],
                public_url=r["public_url"],
            )
            for r in selection["cases"]
        ]
    else:
        chosen = selection
    digests = [r["sha256"] for r in chosen]
    require(
        chosen and len(set(digests)) == len(digests) and not (used & set(digests)),
        "Expected independent recordings disjoint from all training controls",
    )
    outcomes = []
    for row in chosen:
        digest = row["sha256"]
        require(len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest), "SHA-256 format")
        path = args.control_root / (digest + ".StormReplay")
        pinned(path, digest)
        require(path.stat().st_size == row["bytes"], "file size")
        with closing(MPQArchive(path)) as arc:
            head = protocol96477.decode_replay_header(arc.header["user_data_header"]["content"])
            require(
                head["m_dataBuildNum"] == 98348
                and head["m_ngdpRootKey"]["m_data"].hex() == "c3b3c8bc82e3a5a62e550fdde9a40c28",
                "data/root",
            )
            init = protocol96477.decode_replay_initdata(arc.read_file("replay.initData"))
            desc = init["m_syncLobbyState"]["m_gameDescription"]
            require(
                (desc["m_mapFileSyncChecksum"], desc["m_modFileSyncChecksum"]) == (886294905, 13528913),
                "Dragon Shire checksum",
            )
        # 111 was the sole positive flags value in every fold of the frozen earlier twelve.
        checked = test((path, digest, rows, {}, [111]))
        outcome = dict(
            replay_sha256=digest,
            replay_bytes=row["bytes"],
            date=row["date"],
            public_url=row["public_url"],
            commands=checked["all_target_commands"],
            ground_truth_live_anchor_targets=checked["live_anchor_targets"],
            game_bytes=checked["game_bytes"],
            game_sha256=checked["game_sha256"],
            reconstructed_sha256=checked["reconstructed_sha256"],
            game_byte_equal=checked["reconstructed_game_byte_equal"],
            xy_only=checked["modes"]["xy_only"],
            frozen=checked["modes"]["xy_and_held_out_flags"],
        )
        outcomes.append(outcome)
    report = dict(
        training_roster_sha256=ROSTER,
        common_anchors_sha256=ANCHORS,
        frozen_exact_m_targetUnitFlags=[111],
        cases=outcomes,
        exclusions="Original selection precedes command decode and uses public map label, date and key. "
        "No model update or fitting on these recordings.",
    )
    output = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if args.output.exists():
        require(args.output.read_bytes() == output, "Existing report differs")
    else:
        with args.output.open("xb") as out:
            out.write(output)
    print(
        [
            (r["commands"], r["frozen"]["predictions"], r["frozen"]["wrong_tags"], r["game_byte_equal"])
            for r in outcomes
        ]
    )


if __name__ == "__main__":
    main()
